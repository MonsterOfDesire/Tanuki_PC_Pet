from .pet_social_rules import parse_interaction_action
from .runtime import app_now
from .transformation_profiles import get_pet_form_key
from .transformation_social_rules import (
    get_transformed_rudolf_social_cooldown,
    is_transformed_rudolf_social_pair,
)


class SocialCareEffects:
    def clear_care_lock(self, pet):
        if pet.care_lock_mode == "hidden" and not pet.isVisible():
            pet.show()
        pet.care_partner = None
        pet.care_lock_mode = "none"
        pet.care_lock_end_time = 0.0

    def start_social_mode(self, pet, mode, target, now):
        pet.social_mode = mode
        pet.social_target = target
        pet.social_started_at = now
        pet.social_timer_frames = pet.get_social_duration_frames(mode)
        pet.star_timer.start(30)

    def stop_social_mode(self, pet, now, apply_cooldown=True):
        if apply_cooldown and pet.social_mode != "none":
            target = pet.social_target
            transformed_rudolf_influence = (
                target is not None
                and is_transformed_rudolf_social_pair(
                    observer_name=getattr(pet, "name", ""),
                    observer_form=get_pet_form_key(pet),
                    target_name=getattr(target, "name", ""),
                    target_form=get_pet_form_key(target),
                )
            )
            cooldown_seconds = get_transformed_rudolf_social_cooldown(
                pet.get_social_cooldown_seconds(),
                influenced=transformed_rudolf_influence,
            )
            pet.social_cooldown_end = now + cooldown_seconds
        pet.social_mode = "none"
        pet.social_target = None
        pet.social_started_at = 0.0
        pet.social_timer_frames = 0

    def start_care_approach(self, adult, child, now):
        self.stop_social_mode(adult, now, apply_cooldown=False)
        adult.care_mode = "approach"
        adult.care_target = child
        adult.care_plan = "auto"
        child.care_partner = adult

    def begin_hidden_interaction(self, adult, child, animation_spec, now):
        action_key, mood, frames = animation_spec
        parsed = parse_interaction_action(action_key)
        motion = parsed[0] if parsed else "idle"
        adult.care_mode = "moving_interaction" if motion == "move" else "interaction"
        adult.care_end_time = now + 3.0
        adult.is_hugging = True
        adult.care_move_direction = adult.direction or 1
        child.care_partner = adult
        child.care_lock_mode = "hidden"
        child.care_lock_end_time = adult.care_end_time
        child.hide()
        adult.current_frames = frames
        adult.frame_index = 0
        if hasattr(adult, "animation_step_budget"):
            adult.animation_step_budget = 0.0
        animation_stepper = getattr(adult, "animation_stepper", None)
        if animation_stepper is not None:
            animation_stepper.reset()
        adult.current_purpose = "interaction"
        adult.current_action_tag = action_key
        adult.current_mood_tag = mood
        adult.state = "move" if adult.care_mode == "moving_interaction" else "idle"

    def begin_companion_care(self, adult, child, now):
        adult.care_mode = "sit"
        adult.care_end_time = now + 5.0
        child.care_partner = adult
        child.care_lock_mode = "comfort"
        child.care_lock_end_time = adult.care_end_time
        child.show()
        adult.state = "idle"
        adult.apply_care_companion_animation()
        child.state = "idle"
        child.ensure_candidate_animation(child.get_child_comfort_candidates())

    def finish_care_mode(self, adult, success, now):
        child = adult.care_target
        previous_mode = adult.care_mode
        if child:
            if previous_mode == "moving_interaction":
                adult.release_hidden_child_nearby(child)
            if not child.isVisible():
                child.show()
            child.clear_care_lock()
            if success:
                child.mood_score = min(100, child.mood_score + 25)
                if hasattr(child, "sync_mood_state_with_score"):
                    child.sync_mood_state_with_score()
                child.pop_heart()
                child.start_recovery(now)
        adult.is_hugging = False
        adult.care_mode = "none"
        adult.care_target = None
        adult.care_end_time = 0.0
        adult.care_move_direction = 0
        adult.care_plan = "auto"
        adult.care_cooldown_end = now + 4.0
        adult.state = "idle"
        adult.change_state("idle", "stand")

    def cancel_care_mode(self, adult):
        child = adult.care_target
        if child:
            if adult.care_mode == "moving_interaction":
                adult.release_hidden_child_nearby(child)
            if not child.isVisible():
                child.show()
            child.clear_care_lock()
        adult.is_hugging = False
        adult.care_mode = "none"
        adult.care_target = None
        adult.care_end_time = 0.0
        adult.care_move_direction = 0
        adult.care_plan = "auto"


SOCIAL_CARE_EFFECTS = SocialCareEffects()
