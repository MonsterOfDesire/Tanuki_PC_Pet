from dataclasses import dataclass

from .pet_intent_rules import INTENT_OBSERVE

OBSERVE_LOCK_DURATION = 3.0
OBSERVE_START_DISTANCE = 220.0
OBSERVE_KEEP_DISTANCE = 260.0
OBSERVE_BACKOFF_DISTANCE = 120.0
OBSERVE_BACKOFF_STEP = 84
OBSERVE_REENTRY_COOLDOWN = 2.5
OBSERVE_REENTRY_COOLDOWN_CROWD_BONUS = 1.5
OBSERVE_REENTRY_COOLDOWN_STREAK_STEP = 0.5
OBSERVE_REENTRY_COOLDOWN_MAX = 5.0
OBSERVE_SAME_TARGET_COOLDOWN = 7.0
OBSERVE_SAME_TARGET_COOLDOWN_STEP = 3.0
OBSERVE_SAME_TARGET_COOLDOWN_CROWD_BONUS = 2.0
OBSERVE_SAME_TARGET_COOLDOWN_MAX = 18.0
OBSERVE_ESCAPE_CROWD_VISIBLE_COUNT = 3
OBSERVE_ESCAPE_CHANCE = 0.3
OBSERVE_ESCAPE_CROWD_BONUS = 0.25
OBSERVE_ESCAPE_STREAK_BONUS = 0.1
OBSERVE_ESCAPE_CHANCE_MAX = 0.85
OBSERVE_ESCAPE_STATE_TIMER_MIN = 140
OBSERVE_ESCAPE_STATE_TIMER_MAX = 210
OBSERVE_START_CHANCE = 0.28
OBSERVE_START_CLOSE_BONUS = 0.12
OBSERVE_START_CROWD_PENALTY = 0.12
OBSERVE_START_STREAK_PENALTY = 0.06
OBSERVE_START_CHANCE_MIN = 0.08
OBSERVE_START_RETRY_COOLDOWN = 2.5
OBSERVE_START_RETRY_CROWD_BONUS = 1.0
OBSERVE_START_RETRY_STREAK_STEP = 0.75
OBSERVE_START_RETRY_MAX = 6.0
POST_OBSERVE_INTERACTION_MAX_DISTANCE = 160.0
POST_OBSERVE_INTERACTION_CHANCE = 0.28
POST_OBSERVE_INTERACTION_CLOSE_BONUS = 0.22
POST_OBSERVE_INTERACTION_CROWD_PENALTY = 0.08
POST_OBSERVE_INTERACTION_STREAK_PENALTY = 0.04
POST_OBSERVE_INTERACTION_CHANCE_MIN = 0.12
POST_OBSERVE_INTERACTION_DURATION = 1.6
POST_OBSERVE_INTERACTION_CLOSE_DURATION = 3.0
OBSERVE_EXPRESSION_CONTEXTS = {"relation_watch", "relation_close"}
OBSERVE_TARGET_NOTICE_CHANCE = 0.24
OBSERVE_TARGET_NOTICE_CROWD_PENALTY = 0.06
OBSERVE_TARGET_NOTICE_CHANCE_MIN = 0.10
OBSERVE_TARGET_NOTICE_DURATION = 1.2
OBSERVE_TARGET_NOTICE_COOLDOWN = 7.0


@dataclass(frozen=True)
class ObservePlan:
    handled: bool
    target_name: str = ""
    lock_until: float = 0.0
    desired_direction: int = 0
    should_hold_idle: bool = False
    should_backoff: bool = False
    backoff_offset: int = 0
    clear_lock: bool = False
    reason: str = ""


@dataclass(frozen=True)
class ObserveStartDecision:
    should_start: bool
    retry_cooldown: float = 0.0
    reason: str = ""


@dataclass(frozen=True)
class PostObserveInteractionDecision:
    should_start: bool
    interaction_context: str = "relation_watch"
    lock_duration: float = 0.0
    reason: str = ""


@dataclass(frozen=True)
class ObserveTargetNoticeDecision:
    should_notice: bool
    duration: float = 0.0
    cooldown: float = 0.0
    reason: str = ""


def should_pause_observe_backoff(*, now, subject_collision_displaced_until, target_collision_displaced_until):
    return (
        float(subject_collision_displaced_until or 0.0) > float(now) or
        float(target_collision_displaced_until or 0.0) > float(now)
    )


def is_observe_target_blocked(*, candidate_target_name, blocked_target_name):
    return bool(candidate_target_name) and candidate_target_name == blocked_target_name


def resolve_observe_reentry_cooldown(*, visible_pet_count, streak_count):
    cooldown = OBSERVE_REENTRY_COOLDOWN
    if int(visible_pet_count or 0) >= OBSERVE_ESCAPE_CROWD_VISIBLE_COUNT:
        cooldown += OBSERVE_REENTRY_COOLDOWN_CROWD_BONUS
    cooldown += max(0, int(streak_count or 0) - 1) * OBSERVE_REENTRY_COOLDOWN_STREAK_STEP
    return min(cooldown, OBSERVE_REENTRY_COOLDOWN_MAX)


def resolve_observe_same_target_cooldown(*, previous_target_name, streak_target_name, streak_count, visible_pet_count=0):
    if not previous_target_name:
        return 0.0, "", 0
    next_streak_count = (
        int(streak_count or 0) + 1
        if previous_target_name == streak_target_name else
        1
    )
    cooldown = OBSERVE_SAME_TARGET_COOLDOWN + (max(0, next_streak_count - 1) * OBSERVE_SAME_TARGET_COOLDOWN_STEP)
    if int(visible_pet_count or 0) >= OBSERVE_ESCAPE_CROWD_VISIBLE_COUNT:
        cooldown += OBSERVE_SAME_TARGET_COOLDOWN_CROWD_BONUS
    cooldown = min(cooldown, OBSERVE_SAME_TARGET_COOLDOWN_MAX)
    return cooldown, previous_target_name, next_streak_count


def resolve_post_observe_escape(*, previous_target_name, previous_target_dx, current_direction, visible_pet_count, streak_count, roll):
    if not previous_target_name:
        return False, 0, 0

    chance = OBSERVE_ESCAPE_CHANCE
    if int(visible_pet_count or 0) >= OBSERVE_ESCAPE_CROWD_VISIBLE_COUNT:
        chance += OBSERVE_ESCAPE_CROWD_BONUS
    chance += min(max(0, int(streak_count or 0) - 1) * OBSERVE_ESCAPE_STREAK_BONUS, 0.2)
    if float(roll) >= min(chance, OBSERVE_ESCAPE_CHANCE_MAX):
        return False, 0, 0

    if float(previous_target_dx) > 0.0:
        direction = -1
    elif float(previous_target_dx) < 0.0:
        direction = 1
    else:
        direction = (-1 if int(current_direction or 1) >= 0 else 1)

    timer = OBSERVE_ESCAPE_STATE_TIMER_MIN
    timer += max(0, int(visible_pet_count or 0) - 2) * 20
    timer += max(0, int(streak_count or 0) - 1) * 15
    timer = min(timer, OBSERVE_ESCAPE_STATE_TIMER_MAX)
    return True, direction, timer


def resolve_observe_start_decision(
    *,
    expression_animation_context,
    visible_pet_count,
    streak_count,
    roll,
    chance_bonus=0.0,
):
    if expression_animation_context not in OBSERVE_EXPRESSION_CONTEXTS:
        return ObserveStartDecision(should_start=False, reason="invalid_expression")

    chance = OBSERVE_START_CHANCE
    if expression_animation_context == "relation_close":
        chance += OBSERVE_START_CLOSE_BONUS
    chance += max(0.0, float(chance_bonus or 0.0))
    if int(visible_pet_count or 0) >= OBSERVE_ESCAPE_CROWD_VISIBLE_COUNT:
        chance -= OBSERVE_START_CROWD_PENALTY
    chance -= max(0, int(streak_count or 0) - 1) * OBSERVE_START_STREAK_PENALTY
    chance = max(chance, OBSERVE_START_CHANCE_MIN)
    if float(roll) < chance:
        return ObserveStartDecision(should_start=True, reason="observe_start_roll")

    retry_cooldown = OBSERVE_START_RETRY_COOLDOWN
    if int(visible_pet_count or 0) >= OBSERVE_ESCAPE_CROWD_VISIBLE_COUNT:
        retry_cooldown += OBSERVE_START_RETRY_CROWD_BONUS
    retry_cooldown += max(0, int(streak_count or 0) - 1) * OBSERVE_START_RETRY_STREAK_STEP
    return ObserveStartDecision(
        should_start=False,
        retry_cooldown=min(retry_cooldown, OBSERVE_START_RETRY_MAX),
        reason="observe_start_skipped",
    )


def resolve_observe_target_notice_decision(*, now, target_busy, cooldown_until, visible_pet_count, roll):
    if target_busy:
        return ObserveTargetNoticeDecision(should_notice=False, reason="target_busy")
    if float(cooldown_until or 0.0) > float(now):
        return ObserveTargetNoticeDecision(should_notice=False, reason="target_notice_cooldown")

    chance = OBSERVE_TARGET_NOTICE_CHANCE
    if int(visible_pet_count or 0) >= OBSERVE_ESCAPE_CROWD_VISIBLE_COUNT:
        chance -= OBSERVE_TARGET_NOTICE_CROWD_PENALTY
    chance = max(chance, OBSERVE_TARGET_NOTICE_CHANCE_MIN)
    if float(roll) >= chance:
        return ObserveTargetNoticeDecision(should_notice=False, reason="target_notice_skipped")

    return ObserveTargetNoticeDecision(
        should_notice=True,
        duration=OBSERVE_TARGET_NOTICE_DURATION,
        cooldown=OBSERVE_TARGET_NOTICE_COOLDOWN,
        reason="target_notice_started",
    )


def resolve_post_observe_interaction_candidate(
    *,
    previous_target_name,
    target_visible,
    target_distance,
    expression_animation_context,
    visible_pet_count,
    streak_count,
    roll,
    chance_bonus=0.0,
):
    if not previous_target_name:
        return PostObserveInteractionDecision(should_start=False, reason="no_target")
    if expression_animation_context not in OBSERVE_EXPRESSION_CONTEXTS:
        return PostObserveInteractionDecision(should_start=False, reason="invalid_expression")
    if not target_visible:
        return PostObserveInteractionDecision(should_start=False, reason="target_missing")
    if float(target_distance) <= 0.0 or float(target_distance) > POST_OBSERVE_INTERACTION_MAX_DISTANCE:
        return PostObserveInteractionDecision(should_start=False, reason="target_out_of_range")

    interaction_context = "relation_close"
    chance = POST_OBSERVE_INTERACTION_CHANCE
    if interaction_context == "relation_close":
        chance += POST_OBSERVE_INTERACTION_CLOSE_BONUS
    chance += max(0.0, float(chance_bonus or 0.0))
    if int(visible_pet_count or 0) >= OBSERVE_ESCAPE_CROWD_VISIBLE_COUNT:
        chance -= POST_OBSERVE_INTERACTION_CROWD_PENALTY
    chance -= max(0, int(streak_count or 0) - 1) * POST_OBSERVE_INTERACTION_STREAK_PENALTY
    chance = max(chance, POST_OBSERVE_INTERACTION_CHANCE_MIN)
    if float(roll) >= chance:
        return PostObserveInteractionDecision(should_start=False, reason="post_observe_interaction_skipped")

    return PostObserveInteractionDecision(
        should_start=True,
        interaction_context=interaction_context,
        lock_duration=(
            POST_OBSERVE_INTERACTION_CLOSE_DURATION
            if interaction_context == "relation_close" else
            POST_OBSERVE_INTERACTION_DURATION
        ),
        reason="post_observe_interaction_started",
    )


def resolve_observe_plan(
    *,
    now,
    intent_kind,
    locked_target_name,
    intent_locked_until,
    intent_reconsider_after,
    focus_target_name,
    expression_animation_context,
    target_visible,
    target_distance,
    target_dx,
):
    has_existing_observe = intent_kind == INTENT_OBSERVE and bool(locked_target_name)
    lock_active = (
        has_existing_observe and
        float(intent_locked_until or 0.0) > float(now)
    )

    max_distance = OBSERVE_KEEP_DISTANCE if lock_active else OBSERVE_START_DISTANCE

    if lock_active:
        target_name = locked_target_name
        lock_until = float(intent_locked_until)
    elif (
        focus_target_name and
        expression_animation_context in OBSERVE_EXPRESSION_CONTEXTS and
        float(intent_reconsider_after or 0.0) <= float(now)
    ):
        target_name = focus_target_name
        lock_until = float(now) + OBSERVE_LOCK_DURATION
    else:
        return ObservePlan(handled=False, clear_lock=has_existing_observe, reason="no_observe_target")

    if not target_visible:
        return ObservePlan(handled=False, clear_lock=True, reason="target_missing")
    if float(target_distance) <= 0.0:
        return ObservePlan(handled=False, clear_lock=True, reason="invalid_distance")
    if float(target_distance) > max_distance:
        return ObservePlan(
            handled=False,
            clear_lock=has_existing_observe,
            reason=("target_far" if lock_active else "target_out_of_range"),
        )

    desired_direction = 0
    if float(target_dx) > 0.0:
        desired_direction = 1
    elif float(target_dx) < 0.0:
        desired_direction = -1

    if float(target_distance) < OBSERVE_BACKOFF_DISTANCE:
        return ObservePlan(
            handled=True,
            target_name=target_name,
            lock_until=lock_until,
            desired_direction=(-desired_direction if desired_direction else 0),
            should_backoff=True,
            backoff_offset=OBSERVE_BACKOFF_STEP,
            reason="observe_backoff",
        )

    return ObservePlan(
        handled=True,
        target_name=target_name,
        lock_until=lock_until,
        desired_direction=desired_direction,
        should_hold_idle=True,
        reason="observe_hold",
    )
