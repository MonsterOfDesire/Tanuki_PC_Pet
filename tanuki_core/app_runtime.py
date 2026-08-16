import random
import time
from dataclasses import dataclass, field

from PyQt6.QtWidgets import QApplication

from .activity_coordinator import ActivityCoordinator
from .activity_runtime_controller import ActivityRuntimeController
from .activity_runtime_adapter import ActivityRuntimeAdapter
from .activity_rhythm_provider import ActivityRhythmProvider
from .achievement_eligibility import AchievementEligibilityGuard
from .achievement_gameplay_bridge import AchievementGameplayBridge
from .achievement_runtime_coordinator import AchievementRuntimeCoordinator
from .achievement_runtime_service import AchievementRuntimeService
from .achievement_state import AchievementState
from .asset_manager import AssetManager
from .bottle_honey_scene_executor import BottleHoneySceneExecutor
from .config_save_scheduler import ConfigSaveScheduler
from .config_store import ConfigStore
from .dashboard_shell import GlobalMouseListener, SensorZone
from .dashboard_shell_lifecycle import DashboardShellLifecycle
from .dashboard_ui import Dashboard
from .direct_hover_scene_executor import DirectHoverSceneExecutor
from .ground_item_coordinator import GroundItemCoordinator
from .gameplay_app_adapter import GameplayAppAdapterMixin
from .gameplay_reward_adapter import GameplayRewardAdapter
from .household_app_adapter import HouseholdAppAdapterMixin
from .household_event_gateway import HouseholdEventGateway
from .household_event_rules import (
    HouseholdEventScheduleState,
    build_household_event_schedule,
)
from .household_runtime_coordinator import HouseholdRuntimeCoordinator
from .household_state import (
    HouseholdEventLog,
    HouseholdState,
    build_default_household_event_log,
    build_default_household_state,
)
from .item_scene_coordinator import (
    ActiveItemScene,
    ItemSceneCoordinator,
)
from .offer_animation_support import OfferAnimationSupport
from .offer_event_adapter import OfferEventAdapter
from .offer_item_scene_runtime_controller import (
    OfferItemSceneRuntimeController,
)
from .offer_item_scene_app_adapter import OfferItemSceneAppAdapterMixin
from .pet_registry import DEFAULT_PET_SPECS, PetRegistry, PetSpec
from .runtime import (
    AdaptivePetLogicScheduler,
    SIM_CLOCK,
    RuntimeProfiler,
    app_now,
)
from .runtime_persistence_coordinator import RuntimePersistenceCoordinator
from .settings_provider import RuntimeSettings
from .shared_food_profiles import get_shared_food_profile_for_holder
from .shared_food_scene_executor import SharedFoodSceneExecutor
from .transformation_runtime_controller import (
    TransformationRuntimeController,
)
from .window_tracker import WindowTracker


ActiveOfferScene = ActiveItemScene


@dataclass
class TanukiAppRuntime(
    OfferItemSceneAppAdapterMixin,
    HouseholdAppAdapterMixin,
    GameplayAppAdapterMixin,
):
    app: QApplication
    settings_provider: RuntimeSettings
    config_store: ConfigStore
    save_scheduler: ConfigSaveScheduler
    window_tracker: WindowTracker
    pets_dict: dict
    pets_list: list
    dashboard: Dashboard
    sensor: SensorZone
    monitor: GlobalMouseListener
    shell: DashboardShellLifecycle | None = None
    timers: dict = field(default_factory=dict)
    household: HouseholdState = field(default_factory=build_default_household_state)
    household_event_log: HouseholdEventLog = field(default_factory=build_default_household_event_log)
    household_event_schedule: HouseholdEventScheduleState = field(default_factory=build_household_event_schedule)
    achievement_state: AchievementState = field(
        default_factory=AchievementState
    )
    achievement_eligibility_guard: AchievementEligibilityGuard = field(
        default_factory=AchievementEligibilityGuard,
        repr=False,
    )
    achievement_runtime_service: AchievementRuntimeService = field(
        init=False,
        repr=False,
    )
    achievement_gameplay_bridge: AchievementGameplayBridge = field(
        init=False,
        repr=False,
    )
    achievement_runtime_coordinator: AchievementRuntimeCoordinator = field(
        init=False,
        repr=False,
    )
    profiler: RuntimeProfiler = field(default_factory=RuntimeProfiler)
    logic_scheduler: AdaptivePetLogicScheduler = field(default_factory=AdaptivePetLogicScheduler)
    item_scene_coordinator: ItemSceneCoordinator = field(init=False, repr=False)
    household_coordinator: HouseholdRuntimeCoordinator = field(init=False, repr=False)
    household_event_gateway: HouseholdEventGateway = field(init=False, repr=False)
    runtime_persistence_coordinator: RuntimePersistenceCoordinator = field(
        init=False,
        repr=False,
    )
    activity_coordinator: ActivityCoordinator = field(init=False, repr=False)
    activity_runtime_adapter: ActivityRuntimeAdapter = field(init=False, repr=False)
    activity_runtime_controller: ActivityRuntimeController = field(
        init=False,
        repr=False,
    )
    transformation_runtime_controller: TransformationRuntimeController = field(
        init=False,
        repr=False,
    )
    rudolf_work_settlement_adapter: object = field(init=False, repr=False)
    rudolf_work_executor: object = field(init=False, repr=False)
    sleep_executor: object = field(init=False, repr=False)
    race_executor: object = field(init=False, repr=False)
    race_event_adapter: object = field(init=False, repr=False)
    chorus_executor: object = field(init=False, repr=False)
    chorus_event_adapter: object = field(init=False, repr=False)
    transformation_executor: object = field(init=False, repr=False)
    transformation_tendency_coordinator: object = field(init=False, repr=False)
    offer_item_scene_runtime_controller: OfferItemSceneRuntimeController = field(
        init=False,
        repr=False,
    )
    offer_animation_support: OfferAnimationSupport = field(
        init=False,
        repr=False,
    )
    offer_event_adapter: OfferEventAdapter = field(init=False, repr=False)
    ground_item_coordinator: GroundItemCoordinator = field(init=False, repr=False)
    direct_hover_scene_executor: DirectHoverSceneExecutor = field(init=False, repr=False)
    bottle_honey_scene_executor: BottleHoneySceneExecutor = field(init=False, repr=False)
    shared_food_scene_executor: SharedFoodSceneExecutor = field(init=False, repr=False)
    pet_registry: PetRegistry = field(init=False, repr=False)
    activity_rhythm_provider: ActivityRhythmProvider = field(
        init=False,
        repr=False,
    )
    gameplay_reward_adapter: GameplayRewardAdapter = field(
        init=False,
        repr=False,
    )
    def __post_init__(self):
        self.pet_registry = PetRegistry(self.pets_dict, self.pets_list)
        self.household_coordinator = HouseholdRuntimeCoordinator(
            household=self.household,
            event_log=self.household_event_log,
            event_schedule=self.household_event_schedule,
        )
        self.activity_coordinator = ActivityCoordinator()
        self.activity_runtime_adapter = ActivityRuntimeAdapter()
        self.achievement_runtime_coordinator = (
            AchievementRuntimeCoordinator.create_default(
                resource_resolver=AssetManager.get_resource_path,
                state=self.achievement_state,
                eligibility_guard=self.achievement_eligibility_guard,
                time_scale_provider=lambda: float(SIM_CLOCK.speed),
                world_mode_provider=(
                    lambda: str(self.settings_provider.world_mode or "")
                ),
                save_callback=getattr(self.dashboard, "schedule_save", None),
                unlock_callback=getattr(
                    self.dashboard,
                    "handle_achievement_unlocks",
                    None,
                ),
            )
        )
        self.achievement_runtime_service = (
            self.achievement_runtime_coordinator.service
        )
        self.achievement_gameplay_bridge = (
            self.achievement_runtime_coordinator.gameplay_bridge
        )
        self.transformation_runtime_controller = (
            TransformationRuntimeController.create_default(
                achievement_runtime_coordinator=(
                    self.achievement_runtime_coordinator
                ),
                pets=self.pets_list,
                pet_registry=self.pet_registry,
                world_mode_provider=(
                    lambda: str(self.settings_provider.world_mode or "")
                ),
                household_pressure_provider=(
                    lambda: float(self.household.household_pressure)
                ),
                record_household_event=(
                    lambda **kwargs: self.record_household_event(**kwargs)
                ),
                refresh_household_summary=getattr(
                    self.dashboard,
                    "refresh_household_summary_if_open",
                    None,
                ),
            )
        )
        self.transformation_executor = (
            self.transformation_runtime_controller.executor
        )
        self.transformation_tendency_coordinator = (
            self.transformation_runtime_controller.tendency_coordinator
        )
        self.household_event_gateway = HouseholdEventGateway(
            household_coordinator=self.household_coordinator,
            dashboard=self.dashboard,
            pets=self.pets_list,
            transformation_tendency_coordinator=(
                self.transformation_tendency_coordinator
            ),
            transformation_executor=self.transformation_executor,
            achievement_runtime_coordinator=(
                self.achievement_runtime_coordinator
            ),
        )
        self.runtime_persistence_coordinator = RuntimePersistenceCoordinator(
            household_coordinator=self.household_coordinator,
            achievement_runtime_coordinator=(
                self.achievement_runtime_coordinator
            ),
            dashboard=self.dashboard,
        )
        self.gameplay_reward_adapter = GameplayRewardAdapter(
            pet_registry=self.pet_registry,
            household=self.household,
        )
        self.activity_runtime_controller = (
            ActivityRuntimeController.create_default(
                activity_coordinator=self.activity_coordinator,
                runtime_adapter=self.activity_runtime_adapter,
                race_frequency_provider=(
                    lambda: getattr(
                        self.settings_provider,
                        "race_frequency",
                        "normal",
                    )
                ),
                chorus_frequency_provider=(
                    lambda: getattr(
                        self.settings_provider,
                        "chorus_frequency",
                        "normal",
                    )
                ),
                achievement_runtime_coordinator=(
                    self.achievement_runtime_coordinator
                ),
                transformation_runtime_controller=(
                    self.transformation_runtime_controller
                ),
                pets=self.pets_list,
                pet_registry=self.pet_registry,
                household=self.household,
                household_event_schedule=self.household_event_schedule,
                world_mode_provider=(
                    lambda: str(self.settings_provider.world_mode or "")
                ),
                record_household_event=(
                    lambda **kwargs: self.record_household_event(**kwargs)
                ),
                record_resolved_household_event=(
                    lambda event: self._record_resolved_household_event(event)
                ),
                apply_race_mood_reward=(
                    self.gameplay_reward_adapter.apply_mood_reward
                ),
                apply_reverse_race_relationship_reward=(
                    self.gameplay_reward_adapter.apply_relationship_reward
                ),
                apply_chorus_mood_reward=(
                    self.gameplay_reward_adapter.apply_mood_reward
                ),
                apply_chorus_relationship_reward=(
                    self.gameplay_reward_adapter.apply_relationship_reward
                ),
                refresh_relationship_table=getattr(
                    self.dashboard,
                    "refresh_relationship_table_if_open",
                    None,
                ),
            )
        )
        self.rudolf_work_settlement_adapter = (
            self.activity_runtime_controller.work_settlement_adapter
        )
        self.rudolf_work_executor = self.activity_runtime_controller.work_executor
        self.sleep_executor = self.activity_runtime_controller.sleep_executor
        self.race_executor = self.activity_runtime_controller.race_executor
        self.race_event_adapter = self.activity_runtime_controller.race_event_adapter
        self.chorus_executor = self.activity_runtime_controller.chorus_executor
        self.chorus_event_adapter = self.activity_runtime_controller.chorus_event_adapter
        self.offer_animation_support = OfferAnimationSupport(
            pets=self.pets_list,
            pet_registry=self.pet_registry,
            lock_pet_for_offer_scene=(
                lambda pet, scene_kind, until: (
                    self.offer_item_scene_runtime_controller.lock_pet_for_offer_scene(
                        pet,
                        scene_kind,
                        until,
                    )
                )
            ),
            held_item_position_updater=(
                lambda *args, **kwargs: self.update_held_offer_widget_position(
                    *args,
                    **kwargs,
                )
            ),
            now_provider=lambda: app_now(),
        )
        self.offer_event_adapter = OfferEventAdapter(
            achievement_runtime_coordinator=(
                self.achievement_runtime_coordinator
            ),
            pet_registry=self.pet_registry,
            record_household_event=(
                lambda **kwargs: self.record_household_event(**kwargs)
            ),
            scene_provider=lambda: self.offer_scene,
            scene_id_provider=(
                lambda scene: self.item_scene_coordinator.get_scene_id(scene)
            ),
            now_provider=lambda: app_now(),
        )
        self.offer_item_scene_runtime_controller = (
            OfferItemSceneRuntimeController(
                pets=self.pets_list,
                pet_registry=self.pet_registry,
                achievement_runtime_coordinator=(
                    self.achievement_runtime_coordinator
                ),
                profiler=self.profiler,
                support=self._build_offer_item_scene_support(),
                now_provider=lambda: app_now(),
                random_provider=lambda: random.random(),
                random_choice_provider=lambda values: random.choice(values),
                shared_food_profile_provider=(
                    lambda item_kind, pet_name: (
                        get_shared_food_profile_for_holder(
                            item_kind,
                            pet_name,
                        )
                    )
                ),
            )
        )
        self.item_scene_coordinator = (
            self.offer_item_scene_runtime_controller.item_scene_coordinator
        )
        self.ground_item_coordinator = (
            self.offer_item_scene_runtime_controller.ground_item_coordinator
        )
        self.direct_hover_scene_executor = (
            self.offer_item_scene_runtime_controller.direct_hover_scene_executor
        )
        self.bottle_honey_scene_executor = (
            self.offer_item_scene_runtime_controller.bottle_honey_scene_executor
        )
        self.shared_food_scene_executor = (
            self.offer_item_scene_runtime_controller.shared_food_scene_executor
        )
        self.activity_rhythm_provider = ActivityRhythmProvider(
            activity_coordinator=self.activity_coordinator,
            race_executor=self.race_executor,
            chorus_executor=self.chorus_executor,
            sleep_executor=self.sleep_executor,
            pets=self.pets_list,
        )

    def shutdown(self):
        for timer in self.timers.values():
            if timer.isActive():
                timer.stop()
        self.activity_runtime_controller.shutdown()
        self.transformation_runtime_controller.shutdown()
        self.offer_item_scene_runtime_controller.shutdown()
        if self.shell is not None:
            self.shell.shutdown()

    def find_pet_by_name(self, pet_name, visible_only=False):
        registry = getattr(self, "pet_registry", None)
        if registry is None:
            registry = PetRegistry(
                getattr(self, "pets_dict", {}),
                self.pets_list,
            )
        return registry.find_by_name(
            pet_name,
            visible_only=visible_only,
        )
