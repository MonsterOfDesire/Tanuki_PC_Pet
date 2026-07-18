import random as random_module


def get_mood_band(mood_score):
    if mood_score < 20:
        return "severe"
    if mood_score < 50:
        return "low"
    return "normal"


def get_mood_rules(mood_score, is_adult=False):
    if mood_score < 20:
        if is_adult:
            return (
                ["scold", "sad", "angry", "exhausted"],
                ["awkward", "think", "hurry", "effort", "sleep"],
                ["happy", "smile", "confidence", "cool", "cry", "hard-cry", "scared"],
            )
        return (
            ["scold", "hard-cry", "cry", "exhausted", "scared"],
            ["sad", "angry", "awkward", "think", "hurry", "effort", "sleep"],
            ["happy", "smile", "confidence", "cool"],
        )
    if mood_score < 50:
        return (
            ["angry", "sad", "think", "awkward", "hurry", "effort", "sleep"],
            ["cry", "hard-cry", "scold", "exhausted", "scared"],
            ["happy", "smile", "confidence", "cool"],
        )
    return (
        ["happy", "smile", "confidence", "cool", "glance"],
        ["awkward", "think"],
        ["cry", "hard-cry", "sad", "angry", "scold"],
    )


def get_record_weight(record):
    if not record:
        return 1.0
    meta = record.get("manifest") or {}
    return max(0.0, float(meta.get("weight", 1.0) or 0.0))


def context_matches(context, contexts):
    if isinstance(context, (list, tuple, set, frozenset)):
        return any(item in contexts for item in context if item)
    return context in contexts


def has_reserved_context_only(contexts):
    return bool(contexts) and all(
        str(item).startswith("future_") or str(item) == "disabled"
        for item in contexts
    )


def is_record_eligible(record, mood_score=None, context=None):
    if not record:
        return False
    meta = record.get("manifest") or {}
    bands = meta.get("band") or []
    if mood_score is not None and bands:
        if get_mood_band(mood_score) not in bands:
            return False
    contexts = meta.get("contexts") or []
    if has_reserved_context_only(contexts) and not context_matches(context, contexts):
        return False
    if context and contexts and not context_matches(context, contexts):
        return False
    return True


def choose_weighted_result(results, rng=None):
    if not results:
        return None
    if rng is None:
        rng = random_module
    weights = [max(0.0, result[3]) for result in results]
    if any(weight > 0 for weight in weights):
        chosen = rng.choices(results, weights=weights, k=1)[0]
    else:
        chosen = rng.choice(results)
    return chosen[0], chosen[1], chosen[2]


def prioritize_action_keys(available_types, action_type=None):
    action_keys = list(available_types.keys())
    if action_type in action_keys:
        action_keys.remove(action_type)
        action_keys.insert(0, action_type)
    return action_keys


def collect_weighted_matches(action_keys, mood_tag, *, get_record, mood_score=None, context=None):
    matches = []
    for action_key in action_keys:
        record = get_record(action_key, mood_tag)
        if is_record_eligible(record, mood_score=mood_score, context=context):
            matches.append((record["frames"], action_key, mood_tag, get_record_weight(record)))
    return matches


def collect_safe_results(mood_keys, action_type, *, get_record, forbidden=None, mood_score=None, context=None):
    if forbidden is None:
        forbidden = []
    safe_results = []
    normal_result = None
    for mood_tag in mood_keys:
        if mood_tag in forbidden:
            continue
        record = get_record(action_type, mood_tag)
        if not is_record_eligible(record, mood_score=mood_score, context=context):
            continue
        result = (record["frames"], action_type, mood_tag, get_record_weight(record))
        if mood_tag == "normal":
            normal_result = result
        safe_results.append(result)
    return normal_result, safe_results


def select_result_by_score(
    available_types,
    *,
    get_record,
    action_type=None,
    mood_score=60.0,
    is_adult=False,
    context=None,
    manifest_present=False,
    rng=None,
):
    if not available_types:
        return None
    if rng is None:
        rng = random_module

    priority_chain, fallback_chain, forbidden = get_mood_rules(mood_score, is_adult=is_adult)
    mood_chain = priority_chain + fallback_chain

    if action_type in available_types:
        for mood_tag in mood_chain:
            record = get_record(action_type, mood_tag)
            if is_record_eligible(record, mood_score=mood_score, context=context):
                return record["frames"], action_type, mood_tag

    action_keys = prioritize_action_keys(available_types, action_type=action_type)
    for mood_tag in mood_chain:
        weighted = choose_weighted_result(
            collect_weighted_matches(
                action_keys,
                mood_tag,
                get_record=get_record,
                mood_score=mood_score,
                context=context,
            ),
            rng=rng,
        )
        if weighted:
            return weighted

    target_action = action_type if action_type in available_types else rng.choice(list(available_types.keys()))
    normal_result, safe_results = collect_safe_results(
        list(available_types[target_action].keys()),
        target_action,
        get_record=get_record,
        forbidden=forbidden,
        mood_score=mood_score,
        context=context,
    )
    if normal_result:
        return normal_result[0], normal_result[1], normal_result[2]
    weighted = choose_weighted_result(safe_results, rng=rng)
    if weighted:
        return weighted
    if manifest_present:
        return None
    return None


def select_result_for_preferences(
    available_types,
    action_type,
    preferred_moods,
    *,
    get_record,
    forbidden=None,
    mood_score=None,
    context=None,
    rng=None,
):
    if action_type not in available_types:
        return None
    if rng is None:
        rng = random_module

    for mood_tag in preferred_moods:
        record = get_record(action_type, mood_tag)
        if is_record_eligible(record, mood_score=mood_score, context=context):
            return record["frames"], action_type, mood_tag

    normal_result, safe_results = collect_safe_results(
        list(available_types[action_type].keys()),
        action_type,
        get_record=get_record,
        forbidden=forbidden,
        mood_score=mood_score,
        context=context,
    )
    if normal_result:
        return normal_result[0], normal_result[1], normal_result[2]
    return choose_weighted_result(safe_results, rng=rng)


def _select_contextual_candidate(
    purpose_records,
    *,
    context=None,
    preferred_moods=None,
    forbidden=None,
    mood_score=None,
    ordered_preferences=False,
    rng=None,
):
    if rng is None:
        rng = random_module
    preferred_moods = tuple(preferred_moods or ())
    preferred_set = set(preferred_moods)
    forbidden = set(forbidden or ())
    preferred_results = []
    fallback_results = []
    for purpose, asset_records_for_purpose in purpose_records:
        for action_type, mood_map in asset_records_for_purpose.items():
            for mood_tag, record in mood_map.items():
                if mood_tag in forbidden:
                    continue
                if not is_record_eligible(record, mood_score=mood_score, context=context):
                    continue
                frames = record.get("frames")
                if not frames:
                    continue
                result = (
                    frames,
                    purpose,
                    action_type,
                    mood_tag,
                    get_record_weight(record),
                )
                if mood_tag in preferred_set:
                    preferred_results.append(result)
                else:
                    fallback_results.append(result)
    weighted = None
    if ordered_preferences:
        for mood_tag in preferred_moods:
            weighted = _choose_weighted_contextual_candidate(
                [result for result in preferred_results if result[3] == mood_tag],
                rng=rng,
            )
            if weighted:
                break
    else:
        weighted = _choose_weighted_contextual_candidate(preferred_results, rng=rng)
    if weighted:
        return weighted
    return _choose_weighted_contextual_candidate(fallback_results, rng=rng)


def _choose_weighted_contextual_candidate(results, rng=None):
    if not results:
        return None
    if rng is None:
        rng = random_module
    weights = [max(0.0, result[4]) for result in results]
    if any(weight > 0 for weight in weights):
        return rng.choices(results, weights=weights, k=1)[0]
    return rng.choice(results)


def select_contextual_result(
    asset_records_for_purpose,
    *,
    context=None,
    preferred_moods=None,
    forbidden=None,
    mood_score=None,
    ordered_preferences=False,
    rng=None,
):
    if not asset_records_for_purpose:
        return None
    result = _select_contextual_candidate(
        (("", asset_records_for_purpose),),
        context=context,
        preferred_moods=preferred_moods,
        forbidden=forbidden,
        mood_score=mood_score,
        ordered_preferences=ordered_preferences,
        rng=rng,
    )
    if not result:
        return None
    frames, _purpose, action_type, mood_tag, _weight = result
    return frames, action_type, mood_tag


def select_contextual_result_for_purposes(
    asset_records,
    purposes,
    *,
    context=None,
    preferred_moods=None,
    forbidden=None,
    mood_score=None,
    ordered_preferences=False,
    rng=None,
):
    purpose_records = tuple(
        (purpose, asset_records.get(purpose, {}))
        for purpose in purposes or ()
        if purpose and asset_records.get(purpose)
    )
    if not purpose_records:
        return None
    result = _select_contextual_candidate(
        purpose_records,
        context=context,
        preferred_moods=preferred_moods,
        forbidden=forbidden,
        mood_score=mood_score,
        ordered_preferences=ordered_preferences,
        rng=rng,
    )
    if not result:
        return None
    frames, purpose, action_type, mood_tag, _weight = result
    return frames, purpose, action_type, mood_tag


def select_safe_result(
    available_types,
    mood_list,
    *,
    get_record,
    forbidden=None,
    mood_score=None,
    context=None,
    rng=None,
):
    if not available_types:
        return None
    if forbidden is None:
        forbidden = []
    if rng is None:
        rng = random_module

    action_keys = list(available_types.keys())
    if hasattr(rng, "shuffle"):
        rng.shuffle(action_keys)

    for mood_tag in mood_list:
        for action_type in action_keys:
            record = get_record(action_type, mood_tag)
            if is_record_eligible(record, mood_score=mood_score, context=context):
                return record["frames"], action_type, mood_tag

    for action_type in action_keys:
        normal_result, safe_results = collect_safe_results(
            list(available_types[action_type].keys()),
            action_type,
            get_record=get_record,
            forbidden=forbidden,
            mood_score=mood_score,
            context=context,
        )
        if normal_result:
            return normal_result[0], normal_result[1], normal_result[2]
        weighted = choose_weighted_result(safe_results, rng=rng)
        if weighted:
            return weighted

    return None
