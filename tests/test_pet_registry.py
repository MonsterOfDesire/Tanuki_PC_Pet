import unittest

from tanuki_core.pet_registry import DEFAULT_PET_SPECS, PetRegistry


class FakePet:
    def __init__(self, name, *, visible=True):
        self.name = name
        self.visible = visible

    def isVisible(self):
        return self.visible


class PetRegistryTests(unittest.TestCase):
    def test_lookup_preserves_single_pet_instances(self):
        teio = FakePet("Tokai Teio")
        registry = PetRegistry(
            {"Tokai Teio": {"pet": teio}},
            [teio],
        )

        self.assertIs(registry.find_by_name("Tokai Teio"), teio)
        self.assertIsNone(registry.find_by_name("Symboli Rudolf"))

    def test_visible_lookup_skips_hidden_pet(self):
        teio = FakePet("Tokai Teio", visible=False)
        registry = PetRegistry({}, [teio])

        self.assertIs(registry.find_by_name("Tokai Teio"), teio)
        self.assertIsNone(
            registry.find_by_name("Tokai Teio", visible_only=True)
        )

    def test_default_specs_keep_existing_visibility_policy(self):
        visibility = {
            spec.folder_name: spec.initially_visible
            for spec in DEFAULT_PET_SPECS
        }

        self.assertTrue(visibility["Symboli Rudolf"])
        self.assertFalse(visibility["Tokai Teio"])
        self.assertEqual(len(DEFAULT_PET_SPECS), 5)


if __name__ == "__main__":
    unittest.main()
