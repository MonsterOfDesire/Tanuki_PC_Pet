from dataclasses import dataclass, field


SOCIAL_LOG_OBSERVE_CHANCE = 0.22
SOCIAL_LOG_POST_OBSERVE_CHANCE = 0.45
SOCIAL_LOG_COOLDOWN_SECONDS = 25.0
SOCIAL_LOG_AWKWARD_TEMPLATE_INDICES = {
    "observe": frozenset({3, 10, 22}),
    "post_observe_interaction": frozenset({16, 23}),
}
SOCIAL_LOG_POSITIVE_RELATION_DELTAS = {
    "observe": {"familiarity": 0.12},
    "post_observe_interaction": {"familiarity": 0.25, "attachment": 0.08},
}
SOCIAL_LOG_AWKWARD_RELATION_DELTAS = {
    "observe": {"tension": 0.10},
    "post_observe_interaction": {"trust": -0.08, "attachment": -0.03, "tension": 0.20},
}

SOCIAL_LOG_EVENT_TEMPLATES = {
    "observe": (
        "{actor}注意到{target}正在做自己的事，默默看了一會兒。",
        "{actor}和{target}短暫對上視線，氣氛放鬆了一點。",
        "{actor}在旁邊觀察了{target}一會兒，像是在記住對方的小習慣。",
        "{actor}看見{target}似乎在猶豫什麼，沒有立刻打擾。",
        "{actor}悄悄放慢腳步，等{target}先忙完眼前的小事。",
        "{actor}注意到{target}的表情變化，像是在判斷今天的心情。",
        "{actor}看著{target}整理衣角，默默把這個小習慣記了下來。",
        "{actor}望向{target}手邊的東西，像是在猜晚點會不會用得上。",
        "{actor}發現{target}靠近了些，於是稍微留出一點位置。",
        "{actor}看著{target}在窗邊停了一下，氣氛變得很安靜。",
        "{actor}注意到{target}似乎有點得意，沒有戳破，只是看了一眼。",
        "{actor}看見{target}精神不錯，自己也跟著放鬆了些。",
        "{actor}默默觀察{target}的步調，像是在配合家裡的節奏。",
        "{actor}發現{target}正看著桌面上的東西，短暫地跟著望過去。",
        "{actor}注意到{target}似乎想找人說話，先在旁邊等了一會兒。",
        "{actor}看著{target}繞過身邊，沒有催促，只是讓出通道。",
        "{actor}和{target}擦肩而過時，彼此都稍微放慢了腳步。",
        "{actor}看見{target}露出一點小表情，像是家裡才懂的暗號。",
        "{actor}注意到{target}今天特別安分，忍不住多看了幾眼。",
        "{actor}看著{target}晃到附近，像是在確認對方沒有遇到麻煩。",
        "{actor}短暫停下來觀察{target}，然後若無其事地移開視線。",
        "{actor}注意到{target}的尾巴動了一下，似乎明白了什麼。",
        "{actor}看著{target}靠近又離開，像是在衡量要不要開口。",
        "{actor}發現{target}今天的步伐很輕，心裡悄悄放心了些。",
    ),
    "post_observe_interaction": (
        "{actor}靠近{target}，短短地聊了幾句。",
        "{actor}和{target}湊在一起說了點家常。",
        "{actor}對{target}做出小小的回應，兩人很快又各自散開。",
        "{actor}問了{target}一句晚點想做什麼，對方像是認真想了一下。",
        "{actor}和{target}小聲交換了幾句，內容大概只有家裡人才懂。",
        "{actor}靠過去提醒{target}別太勉強，語氣聽起來很自然。",
        "{actor}和{target}聊起剛才發生的小事，氣氛輕輕鬆鬆。",
        "{actor}向{target}確認今天過得怎麼樣，對方給了簡短的回應。",
        "{actor}和{target}像是在討論晚餐，話題很快又被帶偏了。",
        "{actor}靠近{target}說了句玩笑話，兩人之間的距離縮短了一點。",
        "{actor}和{target}短暫並肩站著，像是在分享同一個小秘密。",
        "{actor}對{target}點了點頭，兩人默契地沒有多說。",
        "{actor}問{target}要不要休息一下，語氣比平常柔和。",
        "{actor}和{target}聊了幾句桌面上的東西，像是在安排家裡的小日程。",
        "{actor}聽{target}說了一點瑣事，沒有插話，只是安靜地陪著。",
        "{actor}靠近{target}確認狀況，確認沒事後才放心離開。",
        "{actor}和{target}小小拌了幾句嘴，但很快又恢復平常的氣氛。",
        "{actor}把剛才注意到的事告訴{target}，對方像是有點意外。",
        "{actor}和{target}討論了一下點心，結論似乎還沒定下來。",
        "{actor}對{target}說了聲辛苦了，語氣很像日常的一部分。",
        "{actor}和{target}交換了一個眼神，像是不用說也能明白。",
        "{actor}靠近{target}說了幾句叮嚀，最後還是放對方自由活動。",
        "{actor}和{target}短暫湊在一起，像是在確認彼此都還好。",
        "{actor}對{target}提出一個小建議，對方似乎沒有完全反對。",
        "{actor}陪{target}站了一會兒，家裡的空氣因此安定了些。",
    ),
}


@dataclass(frozen=True)
class SocialLogEventPlan:
    should_emit: bool
    cooldown_until: float = 0.0
    event_type: str = ""
    summary: str = ""
    relation_delta: dict[str, float] = field(default_factory=dict)
    tags: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, object] = field(default_factory=dict)
    reason: str = ""


def normalize_social_log_source(source_context: str) -> str:
    source_text = str(source_context or "")
    if source_text == "post_observe_interaction":
        return "post_observe_interaction"
    if source_text == "observe":
        return "observe"
    return ""


def get_social_log_template_count(source_context: str) -> int:
    source = normalize_social_log_source(source_context)
    return len(SOCIAL_LOG_EVENT_TEMPLATES.get(source, ()))


def resolve_social_log_event_plan(
    *,
    actor_name: str,
    target_name: str,
    source_context: str,
    now: float,
    cooldown_until: float = 0.0,
    roll: float,
    template_index: int = 0,
) -> SocialLogEventPlan:
    actor_name = str(actor_name or "").strip()
    target_name = str(target_name or "").strip()
    source = normalize_social_log_source(source_context)
    if not actor_name or not target_name:
        return SocialLogEventPlan(should_emit=False, reason="missing_participant")
    if not source:
        return SocialLogEventPlan(should_emit=False, reason="unsupported_source")
    if float(cooldown_until or 0.0) > float(now):
        return SocialLogEventPlan(should_emit=False, reason="cooldown")

    chance = (
        SOCIAL_LOG_POST_OBSERVE_CHANCE
        if source == "post_observe_interaction"
        else SOCIAL_LOG_OBSERVE_CHANCE
    )
    if float(roll) >= chance:
        return SocialLogEventPlan(should_emit=False, reason="roll_miss")

    templates = SOCIAL_LOG_EVENT_TEMPLATES[source]
    resolved_template_index = int(template_index or 0) % len(templates)
    template = templates[resolved_template_index]
    is_post_observe = source == "post_observe_interaction"
    is_awkward = resolved_template_index in SOCIAL_LOG_AWKWARD_TEMPLATE_INDICES.get(source, frozenset())
    relation_delta = dict(
        SOCIAL_LOG_AWKWARD_RELATION_DELTAS[source]
        if is_awkward
        else SOCIAL_LOG_POSITIVE_RELATION_DELTAS[source]
    )
    tags = (
        ("observe", "post_observe", "small_talk")
        if is_post_observe
        else ("observe", "ambient_social")
    )
    if is_awkward:
        tags = (*tags, "minor_tension")

    return SocialLogEventPlan(
        should_emit=True,
        cooldown_until=float(now) + SOCIAL_LOG_COOLDOWN_SECONDS,
        event_type=("post_observe_social_log" if is_post_observe else "observe_social_log"),
        summary=template.format(actor=actor_name, target=target_name),
        relation_delta=relation_delta,
        tags=tags,
        metadata={"source": source},
        reason="emit",
    )
