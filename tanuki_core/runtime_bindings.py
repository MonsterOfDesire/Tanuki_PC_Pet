def bind_pet_runtime_providers(runtime):
    for pet in runtime.pets_list:
        pet.runtime_profiler = runtime.profiler
        pet.activity_user_interrupt_provider = (
            lambda target_pet, reason="user_drag", runtime=runtime: (
                runtime.interrupt_pet_activity_for_user(
                    target_pet,
                    reason=reason,
                )
            )
        )
        pet.sleep_join_behavior_provider = (
            lambda target_pet, all_pets, now, runtime=runtime: (
                runtime.update_sleep_join_behavior(
                    target_pet,
                    all_pets,
                    now=now,
                )
            )
        )
        pet.care_activity_event_provider = (
            lambda stage, caregiver, target, now, success=None,
            care_mode="", runtime=runtime: (
                runtime.handle_care_activity_event(
                    stage,
                    caregiver,
                    target,
                    now=now,
                    success=success,
                    care_mode=care_mode,
                )
            )
        )
        pet.ambient_animation_event_provider = (
            lambda target_pet, context, now, runtime=runtime: (
                runtime.achievement_runtime_coordinator
                .handle_ambient_animation_context(
                    target_pet,
                    context,
                    now=now,
                )
            )
        )


def bind_dashboard_runtime_providers(runtime):
    dashboard = runtime.dashboard
    dashboard.set_household_data_providers(
        household_state_provider=lambda runtime=runtime: runtime.household,
        household_events_provider=(
            lambda limit=24, runtime=runtime: (
                runtime.recent_household_events(limit=limit)
            )
        ),
        activity_rhythm_provider=(
            lambda runtime=runtime: runtime.get_activity_rhythm_snapshot()
        ),
    )
    dashboard.set_achievement_data_provider(
        achievement_snapshot_provider=(
            lambda runtime=runtime: (
                runtime.achievement_runtime_coordinator.build_cabinet_snapshot()
            )
        ),
    )
    dashboard.set_household_action_providers(
        household_donate_provider=(
            lambda amount=100, runtime=runtime: (
                runtime.donate_household_fund(amount=amount)
            )
        ),
    )
    dashboard.set_activity_action_providers(
        rudolf_work_preview_provider=(
            lambda runtime=runtime: runtime.preview_rudolf_work()
        ),
        rudolf_work_preview_active_provider=(
            lambda runtime=runtime: runtime.is_rudolf_work_preview_active()
        ),
        race_preview_provider=(
            lambda runtime=runtime: runtime.preview_rudolf_teio_race()
        ),
        race_preview_active_provider=(
            lambda runtime=runtime: runtime.is_race_preview_active()
        ),
        chorus_preview_provider=(
            lambda runtime=runtime: runtime.preview_chorus()
        ),
        chorus_preview_active_provider=(
            lambda runtime=runtime: runtime.is_chorus_preview_active()
        ),
        transformation_toggle_provider=(
            lambda pet_name, runtime=runtime: (
                runtime.toggle_transformation_preview(pet_name)
            )
        ),
        transformation_state_provider=(
            lambda pet_name, runtime=runtime: (
                runtime.get_transformation_preview_state(pet_name)
            )
        ),
        sleep_toggle_provider=(
            lambda pet_name, runtime=runtime: (
                runtime.toggle_sleep_control(pet_name)
            )
        ),
        sleep_state_provider=(
            lambda pet_name, runtime=runtime: (
                runtime.get_sleep_control_state(pet_name)
            )
        ),
    )
    dashboard.set_household_persistence_providers(
        household_capture_provider=(
            lambda runtime=runtime: (
                runtime.capture_household_persistence_state()
            )
        ),
        household_load_provider=(
            lambda payload, runtime=runtime: (
                runtime.apply_household_persistence_state(payload)
            )
        ),
        world_mode_change_provider=(
            lambda mode, previous_mode=None, runtime=runtime: (
                runtime.handle_world_mode_change(
                    mode,
                    previous_mode=previous_mode,
                )
            )
        ),
        achievement_time_scale_provider=(
            lambda time_scale, runtime=runtime: (
                runtime.achievement_runtime_coordinator.observe_time_scale(
                    time_scale
                )
            )
        ),
    )
    dashboard.set_offer_interaction_provider(
        offer_drop_provider=(
            lambda item_kind, global_pos, runtime=runtime: (
                runtime.handle_offer_drop(
                    item_kind=item_kind,
                    global_pos=global_pos,
                )
            )
        ),
        offer_hover_provider=(
            lambda item_kind, global_pos, runtime=runtime: (
                runtime.handle_offer_hover(
                    item_kind=item_kind,
                    global_pos=global_pos,
                )
            )
        ),
        offer_hover_clear_provider=(
            lambda runtime=runtime: runtime.clear_offer_hover()
        ),
    )


def bind_runtime_providers(runtime):
    bind_pet_runtime_providers(runtime)
    bind_dashboard_runtime_providers(runtime)
