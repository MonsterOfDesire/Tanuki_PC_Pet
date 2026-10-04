import unittest

from tanuki_core.bounded_key_set import BoundedKeySet


class BoundedKeySetTests(unittest.TestCase):
    def test_oldest_key_is_evicted_and_duplicate_does_not_reorder(self):
        keys = BoundedKeySet(("a", "b"), max_entries=2)

        keys.add("a")
        keys.add("c")

        self.assertNotIn("a", keys)
        self.assertIn("b", keys)
        self.assertIn("c", keys)
        self.assertEqual(list(keys), ["b", "c"])

    def test_update_never_exceeds_bound(self):
        keys = BoundedKeySet(max_entries=3)

        keys.update(str(index) for index in range(10))

        self.assertEqual(len(keys), 3)
        self.assertEqual(list(keys), ["7", "8", "9"])


if __name__ == "__main__":
    unittest.main()
