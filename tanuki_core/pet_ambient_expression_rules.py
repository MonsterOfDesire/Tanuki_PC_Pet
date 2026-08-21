import random as random_module

from .asset_selection_rules import get_mood_band, get_record_weight


AMBIENT_LOW_MOOD_TAGS = ("angry", "sad")
AMBIENT_LOW_SAME_MOOD_FLOOR = 0.10
AMBIENT_LOW_SAME_MOOD_DECAY = 0.05


def get_ambient_low_same_mood_probability(streak):
    normalized_streak = max(1, int(streak or 0))
    return max(
        AMBIENT_LOW_SAME_MOOD_FLOOR,
        1.0 - (AMBIENT_LOW_SAME_MOOD_DECAY * normalized_streak),
    )


def choose_ambient_low_mood_tag(
    last_mood_tag,
    streak,
    available_mood_tags,
    *,
    roll,
):
    available = tuple(
        mood_tag
        for mood_tag in AMBIENT_LOW_MOOD_TAGS
        if mood_tag in set(available_mood_tags or ())
    )
    if not available:
        return None
    if len(available) == 1:
        return available[0]
    if last_mood_tag not in available:
        return None
    if float(roll) < get_ambient_low_same_mood_probability(streak):
        return last_mood_tag
    return next(
        mood_tag
        for mood_tag in available
        if mood_tag != last_mood_tag
    )


def advance_ambient_low_mood_streak(last_mood_tag, streak, selected_mood_tag):
    if selected_mood_tag not in AMBIENT_LOW_MOOD_TAGS:
        return "", 0
    if selected_mood_tag == last_mood_tag:
        return selected_mood_tag, max(1, int(streak or 0)) + 1
    return selected_mood_tag, 1


def reset_ambient_low_mood_tendency_if_inactive(pet):
    if get_mood_band(getattr(pet, "mood_score", 60.0)) == "low":
        return False
    pet.ambient_low_mood_tag = ""
    pet.ambient_low_mood_streak = 0
    return True


def _record_selected_mood(pet):
    last_mood_tag = str(getattr(pet, "ambient_low_mood_tag", "") or "")
    streak = int(getattr(pet, "ambient_low_mood_streak", 0) or 0)
    selected_mood_tag = str(getattr(pet, "current_mood_tag", "") or "")
    next_mood_tag, next_streak = advance_ambient_low_mood_streak(
        last_mood_tag,
        streak,
        selected_mood_tag,
    )
    pet.ambient_low_mood_tag = next_mood_tag
    pet.ambient_low_mood_streak = next_streak


def _choose_weighted_option(options, rng):
    weights = [max(0.0, float(option[4])) for option in options]
    if any(weight > 0.0 for weight in weights):
        return rng.choices(options, weights=weights, k=1)[0]
    return rng.choice(options)


def apply_ambient_low_mood_tendency(
    pet,
    candidates,
    *,
    context="random",
    rng=None,
):
    """Apply low-band angry/sad continuity without expanding manifest eligibility."""
    if rng is None:
        rng = random_module
    candidates = tuple(dict.fromkeys(tuple(candidates or ())))

    def apply_legacy_selection():
        return pet.change_state_candidates(candidates, context=context)

    def apply_weighted_contextual_selection():
        asset_manager = getattr(pet, "asset_manager", None)
        selector = getattr(
            asset_manager,
            "get_contextual_result_for_candidates",
            None,
        )
        apply_animation_result = getattr(pet, "apply_animation_result", None)
        if callable(selector) and callable(apply_animation_result):
            result = selector(
                candidates,
                context=context,
                mood_score=getattr(pet, "mood_score", 60.0),
                rng=rng,
            )
            if result:
                frames, purpose, action_type, mood_tag = result
                if apply_animation_result(
                    purpose,
                    (frames, action_type, mood_tag),
                ):
                    return True
        return apply_legacy_selection()

    if context != "random":
        return apply_legacy_selection()

    if get_mood_band(getattr(pet, "mood_score", 60.0)) != "low":
        reset_ambient_low_mood_tendency_if_inactive(pet)
        return apply_weighted_contextual_selection()

    should_apply_afterglow = getattr(
        pet,
        "should_apply_negative_afterglow_to_candidates",
        None,
    )
    if callable(should_apply_afterglow) and should_apply_afterglow(candidates):
        return apply_legacy_selection()

    asset_manager = getattr(pet, "asset_manager", None)
    get_specific_frames = getattr(asset_manager, "get_specific_frames", None)
    get_record = getattr(asset_manager, "get_record", None)
    apply_animation_result = getattr(pet, "apply_animation_result", None)
    if not (
        callable(get_specific_frames)
        and callable(get_record)
        and callable(apply_animation_result)
    ):
        applied = apply_default_selection()
        if applied:
            _record_selected_mood(pet)
        return applied

    options_by_mood = {mood_tag: [] for mood_tag in AMBIENT_LOW_MOOD_TAGS}
    mood_score = getattr(pet, "mood_score", 60.0)
    for purpose, action_type in candidates:
        for mood_tag in AMBIENT_LOW_MOOD_TAGS:
            frames = get_specific_frames(
                purpose,
                action_type,
                mood_tag,
                mood_score=mood_score,
                context=context,
            )
            if not frames:
                continue
            record = get_record(purpose, action_type, mood_tag)
            options_by_mood[mood_tag].append(
                (
                    frames,
                    purpose,
                    action_type,
                    mood_tag,
                    get_record_weight(record),
                )
            )

    available_moods = tuple(
        mood_tag
        for mood_tag, options in options_by_mood.items()
        if options
    )
    last_mood_tag = str(getattr(pet, "ambient_low_mood_tag", "") or "")
    streak = int(getattr(pet, "ambient_low_mood_streak", 0) or 0)
    selected_mood_tag = choose_ambient_low_mood_tag(
        last_mood_tag,
        streak,
        available_moods,
        roll=rng.random(),
    )

    # The first low-band draw uses the complete weighted manifest candidate pool.
    if selected_mood_tag is None:
        applied = apply_weighted_contextual_selection()
        if applied:
            _record_selected_mood(pet)
        return applied

    selected = _choose_weighted_option(
        options_by_mood[selected_mood_tag],
        rng,
    )
    frames, purpose, action_type, mood_tag, _weight = selected
    applied = apply_animation_result(
        purpose,
        (frames, action_type, mood_tag),
    )
    if applied:
        _record_selected_mood(pet)
        return True

    applied = apply_weighted_contextual_selection()
    if applied:
        _record_selected_mood(pet)
    return applied
