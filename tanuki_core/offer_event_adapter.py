from __future__ import annotations

from .offer_interaction_rules import (
    ITEM_BOTTLE,
    ITEM_HONEY,
    get_offer_item_definition,
)
from .runtime import app_now
from .shared_food_profiles import (
    SHARED_FOOD_OUTCOME_HOLDER_KEEPS,
    SHARED_FOOD_OUTCOME_SHARE_BOTH,
)


class OfferEventAdapter:
    """Builds canonical offer events, achievement metadata and mood rewards."""

    def __init__(
        self,
        *,
        achievement_runtime_coordinator,
        pet_registry,
        record_household_event,
        scene_provider,
        scene_id_provider,
        now_provider=app_now,
    ):
        self.achievement_runtime_coordinator = (
            achievement_runtime_coordinator
        )
        self.pet_registry = pet_registry
        self.record_household_event = record_household_event
        self.scene_provider = scene_provider
        self.scene_id_provider = scene_id_provider
        self.now_provider = now_provider

    def _base_metadata(self, *, source, item_kind, scene_kind):
        return {
            "source": source,
            "item_kind": item_kind,
            "scene_kind": scene_kind,
        }

    def record_offer_event(
        self,
        item_kind,
        actor_name,
        target_name,
        scene_kind,
        source="offer_tray",
    ):
        metadata = self._base_metadata(
            source=source,
            item_kind=item_kind,
            scene_kind=scene_kind,
        )
        if item_kind == ITEM_BOTTLE and scene_kind == "direct_accept":
            self.record_household_event(
                occurred_at=self.now_provider(),
                category="player_offer",
                event_type=(
                    "offer_bottle_success"
                    if source == "offer_tray"
                    else "ground_bottle_pickup"
                ),
                summary=(
                    "鶴寶接過奶瓶，安靜地喝了起來。"
                    if source == "offer_tray"
                    else "鶴寶路過時撿起地上的奶瓶，乖乖地喝了起來。"
                ),
                actor_name=(
                    "Player" if source == "offer_tray" else target_name
                ),
                target_name=target_name,
                household_pressure_delta=-3.0,
                metadata=metadata,
            )
            return
        if item_kind == ITEM_BOTTLE and scene_kind == "bottle_feed":
            self.record_household_event(
                occurred_at=self.now_provider(),
                category="player_offer",
                event_type=(
                    "offer_bottle_feed"
                    if source == "offer_tray"
                    else "ground_bottle_feed"
                ),
                summary=(
                    f"{actor_name} 拿著奶瓶陪在一旁，看著鶴寶乖乖喝了幾口。"
                    if source == "offer_tray"
                    else f"{actor_name} 撿起地上的奶瓶後陪在一旁，讓鶴寶安心喝了幾口。"
                ),
                actor_name=actor_name,
                target_name=target_name,
                household_pressure_delta=-3.0,
                metadata=metadata,
            )
            return
        if item_kind == ITEM_HONEY and scene_kind == "direct_accept":
            if source == "offer_tray":
                summary = (
                    "天狼星接過蜂蜜，神情明顯放鬆了些。"
                    if target_name == "Sirius Symboli"
                    else "帝寶接過蜂蜜，露出心滿意足的表情。"
                )
            else:
                summary = (
                    "天狼星路過時撿起地上的蜂蜜，神情明顯放鬆了些。"
                    if target_name == "Sirius Symboli"
                    else "帝寶路過時撿起地上的蜂蜜，露出心滿意足的表情。"
                )
            self.record_household_event(
                occurred_at=self.now_provider(),
                category="player_offer",
                event_type=(
                    "offer_honey_success"
                    if source == "offer_tray"
                    else "ground_honey_pickup"
                ),
                summary=summary,
                actor_name=(
                    "Player" if source == "offer_tray" else target_name
                ),
                target_name=target_name,
                household_pressure_delta=-1.0,
                metadata=metadata,
            )
            return
        if scene_kind == "direct_accept":
            item_definition = get_offer_item_definition(item_kind)
            item_label = (
                item_definition.label
                if item_definition is not None
                else item_kind
            )
            self.record_household_event(
                occurred_at=self.now_provider(),
                category="player_offer",
                event_type=(
                    f"offer_{item_kind}_success"
                    if source == "offer_tray"
                    else f"ground_{item_kind}_pickup"
                ),
                summary=(
                    f"{target_name} 接過了{item_label}，看起來相當滿足。"
                    if source == "offer_tray"
                    else f"{target_name} 路過時撿起地上的{item_label}，看起來相當滿足。"
                ),
                actor_name=(
                    "Player" if source == "offer_tray" else target_name
                ),
                target_name=target_name,
                household_pressure_delta=-1.0,
                metadata=metadata,
            )
            return
        if item_kind == ITEM_HONEY and scene_kind == "honey_guard":
            occurred_at = self.now_provider()
            scene = self.scene_provider()
            activity_id = self.scene_id_provider(scene)
            achievement_metadata = (
                self.achievement_runtime_coordinator.build_honey_guard_metadata(
                    scene_id=activity_id,
                    source=str(source or "offer_tray"),
                    started_at=float(
                        getattr(scene, "started_at", occurred_at)
                        or occurred_at
                    ),
                    occurred_at=float(occurred_at),
                    guardian_name=actor_name,
                    target_name=target_name,
                    item_kind=item_kind,
                )
            )
            self.record_household_event(
                occurred_at=occurred_at,
                category="player_offer",
                event_type="offer_honey_guarded",
                summary=f"{actor_name} 趕緊把鶴寶手邊的蜂蜜拿走，免得她誤食。",
                actor_name=actor_name,
                target_name=target_name,
                relation_delta={
                    "trust": -0.05,
                    "attachment": 0.05,
                    "tension": 0.35,
                },
                household_pressure_delta=1.5,
                metadata=achievement_metadata,
            )
            return
        if item_kind == ITEM_HONEY and scene_kind == "deny_only":
            self.record_household_event(
                occurred_at=self.now_provider(),
                category="player_offer",
                event_type="offer_honey_denied",
                summary="鶴寶眼巴巴地看著蜂蜜，最後還是沒能拿到。",
                actor_name=(
                    "Player" if source == "offer_tray" else target_name
                ),
                target_name=target_name,
                household_pressure_delta=2.0,
                metadata=metadata,
            )
            return
        if scene_kind == "hover_timeout_reaction":
            item_definition = get_offer_item_definition(item_kind)
            item_label = (
                item_definition.label
                if item_definition is not None
                else item_kind
            )
            self.record_household_event(
                occurred_at=self.now_provider(),
                category="player_offer",
                event_type="offer_hover_timeout",
                summary=(
                    f"{target_name} 等了太久都沒拿到{item_label}，明顯鬧起了情緒。"
                ),
                actor_name="Player",
                target_name=target_name,
                household_pressure_delta=2.5,
                metadata=metadata,
            )

    def build_shared_food_achievement_metadata(
        self,
        profile,
        shared_state,
        *,
        source,
        now,
    ):
        scene = self.scene_provider()
        activity_id = self.scene_id_provider(scene)
        return self.achievement_runtime_coordinator.build_shared_food_metadata(
            scene_id=activity_id,
            source=str(source or "offer_tray"),
            started_at=float(getattr(scene, "started_at", now) or now),
            occurred_at=float(now),
            holder_name=shared_state.holder_name,
            partner_name=shared_state.partner_name,
            consumer_names=shared_state.consumer_names,
            item_kind=profile.item_kind,
            profile_key=profile.profile_key,
            outcome=shared_state.outcome_key,
        )

    def record_shared_food_event(
        self,
        profile,
        shared_state,
        source="offer_tray",
    ):
        now = self.now_provider()
        item_definition = get_offer_item_definition(profile.item_kind)
        item_label = (
            item_definition.label
            if item_definition is not None
            else profile.item_kind
        )
        if shared_state.outcome_key == SHARED_FOOD_OUTCOME_SHARE_BOTH:
            summary = profile.success_summary_by_holder.get(
                shared_state.holder_name,
                (
                    f"{shared_state.holder_name} 和 "
                    f"{shared_state.partner_name} 分享了{item_label}。"
                ),
            )
        elif shared_state.outcome_key == SHARED_FOOD_OUTCOME_HOLDER_KEEPS:
            summary = (
                f"{shared_state.partner_name} 靠過來看了看，"
                f"{shared_state.holder_name} 最後還是自己享用了{item_label}。"
            )
        else:
            summary = (
                f"{shared_state.holder_name} 把{item_label}讓給了"
                f"{shared_state.partner_name}。"
            )
        metadata = self.build_shared_food_achievement_metadata(
            profile,
            shared_state,
            source=source,
            now=now,
        )
        self.record_household_event(
            occurred_at=now,
            category="player_offer",
            event_type=profile.success_event_type,
            summary=summary,
            actor_name=shared_state.holder_name,
            target_name=shared_state.partner_name,
            household_pressure_delta=-1.0,
            metadata=metadata,
        )

    def apply_offer_mood_reward(self, target_name, amount=10.0):
        pet = self.pet_registry.find_by_name(
            target_name,
            visible_only=False,
        )
        if pet is None:
            return False
        clear_negative_afterglow = getattr(
            pet,
            "clear_negative_afterglow",
            None,
        )
        if callable(clear_negative_afterglow):
            clear_negative_afterglow()
        else:
            pet.negative_afterglow_until = 0.0
            pet.negative_afterglow_preferred_moods = ()
            pet.negative_afterglow_forbidden_moods = ()
        pet.offer_hover_reaction_cooldown_until = 0.0
        pet.mood_score = min(
            100.0,
            float(pet.mood_score) + float(amount),
        )
        if hasattr(pet, "sync_mood_state_with_score"):
            pet.sync_mood_state_with_score()
        if hasattr(pet, "pop_heart"):
            pet.pop_heart()
        return True
