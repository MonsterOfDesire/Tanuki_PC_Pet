DEFAULT_CHILD_COMFORT_CANDIDATES = (
    ("idle", "drink"),
    ("idle", "eat"),
    ("idle", "side_hug"),
    ("idle", "side_rub"),
    ("idle", "sit_no"),
    ("idle", "squat"),
    ("idle", "side"),
)

TOKAI_TEIO_CHILD_COMFORT_CANDIDATES = (
    ("idle", "side_eat_candy"),
    ("idle", "sit"),
    ("idle", "lie"),
    ("idle", "side"),
)

TOKAI_TEIO_CHILD_RECOVERY_CANDIDATES = (
    ("move", "walk_drink"),
    ("idle", "dance_uma_drink"),
    ("idle", "side_eat_candy"),
    ("idle", "lie"),
    ("idle", "side"),
    ("idle", "sit"),
)

ADULT_COMPANION_CANDIDATES_BY_NAME = {
    "Symboli Rudolf": (
        ("idle", "sit"),
        ("idle", "sit_read"),
        ("idle", "rest"),
        ("idle", "squat"),
    ),
    "Sirius Symboli": (
        ("idle", "sit"),
        ("idle", "sit_talk"),
        ("idle", "side"),
    ),
    "Air Groove": (
        ("idle", "sit"),
        ("idle", "side"),
    ),
}

MOVE_CANDIDATES = (
    ("move", "walk"),
    ("move", "run"),
    ("move", "jog"),
    ("move", "sneak"),
    ("move", "climb"),
    ("move", "fly"),
    ("move", "fly_up"),
)

IDLE_CANDIDATES = (
    ("idle", "stand"),
    ("idle", "side"),
    ("idle", "sit"),
    ("idle", "rest"),
    ("idle", "lie"),
    ("idle", "squat"),
    ("idle", "observe"),
    ("idle", "photo"),
    ("idle", "photo_ready"),
    ("idle", "dance_three"),
    ("idle", "dance_uma"),
    ("idle", "hear"),
    ("idle", "knock"),
    ("idle", "get"),
    ("idle", "sleep"),
)

def get_child_comfort_candidates(name):
    if name == "Tokai Teio":
        return list(TOKAI_TEIO_CHILD_COMFORT_CANDIDATES)
    return list(DEFAULT_CHILD_COMFORT_CANDIDATES)


def get_child_recovery_candidates(name):
    if name == "Tokai Teio":
        return list(TOKAI_TEIO_CHILD_RECOVERY_CANDIDATES)
    return get_child_comfort_candidates(name)


def get_adult_companion_candidates(name):
    return list(ADULT_COMPANION_CANDIDATES_BY_NAME.get(name, ()))


def get_move_candidates():
    return list(MOVE_CANDIDATES)


def get_idle_candidates():
    return list(IDLE_CANDIDATES)


def get_expression_preferred_moods(animation_context):
    if animation_context == "relation_watch":
        return ["glance", "think", "smile", "happy", "confidence", "cool"]
    if animation_context == "relation_close":
        return ["smile", "happy", "confidence", "cool", "glance", "think"]
    return []
