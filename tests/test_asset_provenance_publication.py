from copy import deepcopy
import unittest

from tools.check_asset_provenance_publication import is_public_provenance_path, validate_records


class AssetProvenancePublicationTests(unittest.TestCase):
    def test_public_scope_excludes_raw_media_and_snapshots(self):
        for suffix in ("README.md", "data/asset_inventory.json"):
            self.assertTrue(is_public_provenance_path("docs/asset_provenance/" + suffix))
        for suffix in ("source.zip", "source.mp4", "data/source.png", "data/../secret.json", "video_analysis/report.md", "creator_archive_20220119/inventory.json"):
            self.assertFalse(is_public_provenance_path("docs/asset_provenance/" + suffix))

    def setUp(self):
        self.inventory = {"asset_count": 1, "assets": [{"asset_id": "a"}]}
        self.decisions = {"asset_count": 1, "decision_counts": {"orange": 1, "green": 0}, "assets": [{"asset_id": "a", "publication_decision": "orange"}]}
        self.graph = {"node_count": 1, "edge_count": 1, "nodes": [{"node_id": "a"}], "edges": [{"edge_id": "e", "source": "a", "target": "a"}]}

    def test_complete_records_pass(self):
        validate_records(self.inventory, self.decisions, self.graph)

    def test_missing_decision_is_rejected(self):
        changed = deepcopy(self.decisions)
        changed["assets"][0]["asset_id"] = "missing"
        with self.assertRaisesRegex(AssertionError, "coverage"):
            validate_records(self.inventory, changed, self.graph)

    def test_dangling_graph_edge_is_rejected(self):
        changed = deepcopy(self.graph)
        changed["edges"][0]["target"] = "missing"
        with self.assertRaisesRegex(AssertionError, "dangling"):
            validate_records(self.inventory, self.decisions, changed)


if __name__ == "__main__":
    unittest.main()
