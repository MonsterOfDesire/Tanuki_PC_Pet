import unittest

from tanuki_core.race_profiles import (
    RACE_PROFILE,
    build_race_requirements,
    evaluate_race_capability,
    race_profile_supports_form,
)


class FakeAssetManager:
    def __init__(self):
        self.calls = []

    def get_contextual_result_for_purposes(
        self,
        purposes,
        context=None,
        preferred_moods=None,
        forbidden=None,
        mood_score=None,
        ordered_preferences=False,
    ):
        self.calls.append((context, mood_score))
        return ([context], "idle", "manifest-action", "manifest-mood")


class RaceProfileTests(unittest.TestCase):
    def test_profile_uses_only_manifest_context_bindings(self):
        contexts = {
            RACE_PROFILE.challenge_animation.contexts[0],
            RACE_PROFILE.consider_animation.contexts[0],
            RACE_PROFILE.accept_animation.contexts[0],
            RACE_PROFILE.decline_animation.contexts[0],
            RACE_PROFILE.to_start_animation.contexts[0],
            RACE_PROFILE.ready_animation.contexts[0],
            RACE_PROFILE.running_animation.contexts[0],
            RACE_PROFILE.finish_win_animation.contexts[0],
            RACE_PROFILE.finish_lose_animation.contexts[0],
            RACE_PROFILE.recovery_animation.contexts[0],
            RACE_PROFILE.sirius_teio_running_animation.contexts[0],
        }

        self.assertEqual(
            contexts,
            {
                "activity_race_challenge",
                "activity_race_consider",
                "activity_race_accept",
                "activity_race_decline",
                "activity_race_to_start",
                "activity_race_ready",
                "activity_race_running",
                "activity_race_finish_win",
                "activity_race_finish_lose",
                "activity_race_recovery",
                "activity_race_running_teio",
            },
        )

    def test_sirius_uses_teio_running_context_only_against_base_teio(self):
        special = RACE_PROFILE.running_animation_for(
            "Sirius Symboli",
            "Tokai Teio",
            opponent_form="base",
        )
        generic = RACE_PROFILE.running_animation_for(
            "Sirius Symboli",
            "Symboli Rudolf",
        )

        self.assertEqual(special.contexts, ("activity_race_running_teio",))
        self.assertEqual(generic.contexts, ("activity_race_running",))

    def test_opponent_preflight_includes_consider_before_response(self):
        requirements = build_race_requirements(
            character_name="Tokai Teio",
            opponent_name="Symboli Rudolf",
            opponent_form="base",
            role="opponent",
            accepted=True,
        )

        self.assertEqual(
            requirements[0].binding.contexts,
            ("activity_race_consider",),
        )
        self.assertEqual(
            requirements[1].binding.contexts,
            ("activity_race_accept",),
        )

    def test_transformed_teio_is_excluded_but_transformed_rudolf_is_supported(self):
        self.assertFalse(race_profile_supports_form("Tokai Teio", "transformed"))
        self.assertTrue(
            race_profile_supports_form("Symboli Rudolf", "transformed")
        )

    def test_finish_capability_uses_result_band_override(self):
        manager = FakeAssetManager()
        winner_requirements = build_race_requirements(
            character_name="Tokai Teio",
            opponent_name="Symboli Rudolf",
            opponent_form="base",
            role="challenger",
            accepted=True,
            winner=True,
        )
        loser_requirements = build_race_requirements(
            character_name="Symboli Rudolf",
            opponent_name="Tokai Teio",
            opponent_form="base",
            role="opponent",
            accepted=True,
            winner=False,
        )

        self.assertTrue(
            evaluate_race_capability(
                manager,
                mood_score=35.0,
                requirements=winner_requirements,
            ).ready
        )
        self.assertIn(("activity_race_finish_win", 60.0), manager.calls)
        manager.calls.clear()
        self.assertTrue(
            evaluate_race_capability(
                manager,
                mood_score=60.0,
                requirements=loser_requirements,
            ).ready
        )
        self.assertIn(("activity_race_finish_lose", 60.0), manager.calls)

        manager.calls.clear()
        adult_loser_requirements = build_race_requirements(
            character_name="Sirius Symboli",
            opponent_name="Symboli Rudolf",
            opponent_form="base",
            role="opponent",
            accepted=True,
            winner=False,
        )
        self.assertTrue(
            evaluate_race_capability(
                manager,
                mood_score=60.0,
                requirements=adult_loser_requirements,
            ).ready
        )
        self.assertIn(("activity_race_finish_lose", 30.0), manager.calls)

    def test_transformed_rudolf_loss_still_uses_normal_band(self):
        manager = FakeAssetManager()
        requirements = build_race_requirements(
            character_name="Symboli Rudolf",
            opponent_name="Tokai Teio",
            opponent_form="base",
            role="challenger",
            accepted=True,
            winner=False,
            transformed=True,
        )

        evaluate_race_capability(
            manager,
            mood_score=50.0,
            requirements=requirements,
        )

        self.assertIn(("activity_race_finish_lose", 60.0), manager.calls)


if __name__ == "__main__":
    unittest.main()
