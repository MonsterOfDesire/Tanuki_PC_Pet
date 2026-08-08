import unittest
from types import SimpleNamespace

from tanuki_core.transformation_profiles import (
    CAPABILITY_AUTONOMOUS_FLIGHT,
    CAPABILITY_BOTTLE_FEED_HOLDER,
    CAPABILITY_CARE_GIVER,
    CAPABILITY_COMBINED_CARE,
    CAPABILITY_HONEY_GUARDIAN,
    CAPABILITY_RACE,
    CAPABILITY_SHARED_FOOD,
    CAPABILITY_SLEEP,
    CAPABILITY_SOCIAL_FOLLOW,
    CAPABILITY_SOCIAL_MIMIC,
    CAPABILITY_WORK,
    apply_pet_form_mood_floor,
    pet_form_allows_capability,
    pet_form_allows_care_target,
    pet_form_allows_offer_item,
)
from tanuki_core.transformation_state import (
    FORM_TRANSFORMED,
    PetTransformationState,
)


def build_pet(name, *, transformed=False, is_adult=False):
    state = PetTransformationState()
    if transformed:
        state.current_form = FORM_TRANSFORMED
    return SimpleNamespace(
        name=name,
        is_adult=is_adult,
        transformation_state=state,
    )


class TransformationProfileTests(unittest.TestCase):
    def test_transformed_teio_capabilities_match_design(self):
        pet = build_pet("Tokai Teio", transformed=True)

        self.assertFalse(pet_form_allows_capability(pet, CAPABILITY_SLEEP))
        self.assertFalse(pet_form_allows_capability(pet, CAPABILITY_SHARED_FOOD))
        self.assertFalse(pet_form_allows_capability(pet, CAPABILITY_SOCIAL_FOLLOW))
        self.assertFalse(pet_form_allows_capability(pet, CAPABILITY_SOCIAL_MIMIC))
        self.assertFalse(pet_form_allows_capability(pet, CAPABILITY_COMBINED_CARE))
        self.assertTrue(pet_form_allows_capability(pet, CAPABILITY_BOTTLE_FEED_HOLDER))
        self.assertTrue(pet_form_allows_capability(pet, CAPABILITY_HONEY_GUARDIAN))
        self.assertTrue(pet_form_allows_capability(pet, CAPABILITY_CARE_GIVER))
        self.assertTrue(pet_form_allows_capability(pet, CAPABILITY_AUTONOMOUS_FLIGHT))
        self.assertFalse(pet_form_allows_capability(pet, CAPABILITY_RACE))
        self.assertTrue(pet_form_allows_offer_item(pet, "bottle"))
        self.assertFalse(pet_form_allows_offer_item(pet, "ramen"))
        self.assertTrue(pet_form_allows_care_target(pet, "Tsurumaru Tsuyoshi"))
        self.assertFalse(pet_form_allows_care_target(pet, "Tokai Teio"))

    def test_transformed_rudolf_capabilities_match_design(self):
        pet = build_pet("Symboli Rudolf", transformed=True, is_adult=True)

        self.assertFalse(pet_form_allows_capability(pet, CAPABILITY_SLEEP))
        self.assertFalse(pet_form_allows_capability(pet, CAPABILITY_WORK))
        self.assertFalse(pet_form_allows_capability(pet, CAPABILITY_SHARED_FOOD))
        self.assertFalse(pet_form_allows_capability(pet, CAPABILITY_BOTTLE_FEED_HOLDER))
        self.assertFalse(pet_form_allows_capability(pet, CAPABILITY_COMBINED_CARE))
        self.assertFalse(pet_form_allows_capability(pet, CAPABILITY_AUTONOMOUS_FLIGHT))
        self.assertTrue(pet_form_allows_capability(pet, CAPABILITY_RACE))
        self.assertTrue(pet_form_allows_capability(pet, CAPABILITY_HONEY_GUARDIAN))
        self.assertTrue(pet_form_allows_capability(pet, CAPABILITY_CARE_GIVER))
        self.assertFalse(pet_form_allows_offer_item(pet, "bottle"))

    def test_transformed_mood_floor_keeps_normal_band(self):
        transformed = build_pet("Tokai Teio", transformed=True)
        base = build_pet("Tokai Teio")

        self.assertEqual(apply_pet_form_mood_floor(transformed, 12.0), 50.0)
        self.assertEqual(apply_pet_form_mood_floor(base, 12.0), 12.0)

if __name__ == "__main__":
    unittest.main()
