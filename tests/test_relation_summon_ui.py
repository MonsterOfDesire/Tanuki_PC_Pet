import os
import unittest
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtWidgets import QApplication, QProgressBar

from tanuki_core.asset_manager import AssetManager
from tanuki_core.dashboard_presenter import (
    RelationshipRowPresentation,
    RelationshipTablePresentation,
)
from tanuki_core.dashboard_ui import Dashboard
from tanuki_core.information_center_spec import PAGE_RELATION_SUMMON
from tanuki_core.relation_summon_binding import (
    DashboardRelationSummonBinding,
    RaceSummaryPresentation,
    RelationSummonPresentation,
    SummonMemberPresentation,
)
from tanuki_core.relation_summon_ui import (
    RelationSummonPanel,
    RelationshipRowCard,
    crop_avatar_first_frame,
)
from tanuki_core.ui_skin_assets import UiSkinAssets


def relationship_row(actor_name="Air Groove", target_name="Tokai Teio"):
    return RelationshipRowPresentation(
        actor_name=actor_name,
        target_name=target_name,
        affinity=18.5,
        familiarity=20.0,
        trust=15.0,
        attachment=14.0,
        tension=2.0,
        event_count=3,
    )


class FakeRelationSummonBinding:
    def __init__(self):
        self.calls = []
        self.summon_calls = []
        self.states = {"Air Groove": True, "Tokai Teio": False}
        self.moods = {
            "Air Groove": (72.0, "normal"),
            "Tokai Teio": (34.0, "unhappy"),
        }

    def presentation(self, selected_character_name=""):
        self.calls.append(selected_character_name)
        if selected_character_name not in self.states:
            selected_character_name = "Air Groove"
        target_name = "Tokai Teio" if selected_character_name == "Air Groove" else "Air Groove"
        rows = (relationship_row(selected_character_name, target_name),)
        return RelationSummonPresentation(
            title="角色關係＋召喚",
            selected_character_name=selected_character_name,
            members=tuple(
                SummonMemberPresentation(
                    name,
                    summoned,
                    mood_score=self.moods[name][0],
                    mood_state=self.moods[name][1],
                )
                for name, summoned in self.states.items()
            ),
            relationship_rows=rows,
            race_summary=RaceSummaryPresentation(
                completed_races=12,
                wins=8,
                losses=4,
                win_rate=66.666,
            ),
        )

    def set_summoned(self, character_name, summoned):
        self.summon_calls.append((character_name, summoned))
        self.states[character_name] = summoned
        return True

    def mood_snapshot(self):
        return dict(self.moods)


class RelationSummonPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.assets = UiSkinAssets(AssetManager.get_resource_path)

    def setUp(self):
        self.binding = FakeRelationSummonBinding()
        self.panel = RelationSummonPanel(self.assets, self.binding)
        self.panel.resize(520, 330)
        self.panel.show()
        self.app.processEvents()

    def tearDown(self):
        self.panel.close()
        self.panel.deleteLater()
        self.app.processEvents()

    def test_panel_loads_first_frame_head_crops_and_relationship_cards(self):
        avatar_spec = self.assets.avatar_specs[0]
        source_spec = self.assets.get_asset_spec(avatar_spec.asset_key)
        cropped = crop_avatar_first_frame(self.assets, avatar_spec)

        self.assertLess(cropped.height(), source_spec.source_size[1])
        self.assertTrue(self.panel.avatar_buttons["Air Groove"].isChecked())
        self.assertTrue(self.panel.summon_buttons["Air Groove"].isChecked())
        self.assertEqual(
            self.panel.avatar_buttons["Air Groove"].accessibleName(),
            "氣槽",
        )
        self.assertIn("查看 氣槽", self.panel.avatar_buttons["Air Groove"].toolTip())
        self.assertIn("心情：平穩（72/100）", self.panel.avatar_buttons["Air Groove"].toolTip())
        self.assertEqual(self.panel.relationship_list.item(0).text(), "")
        self.assertEqual(
            self.panel.relationship_list.item(0).data(Qt.ItemDataRole.UserRole),
            ("Air Groove", "Tokai Teio"),
        )
        self.assertIn(
            "氣槽 → 帝寶",
            self.panel.relationship_list.item(0).toolTip(),
        )
        row_card = self.panel.relationship_list.itemWidget(
            self.panel.relationship_list.item(0)
        )
        self.assertIsInstance(row_card, RelationshipRowCard)
        self.assertEqual(len(row_card.findChildren(QProgressBar)), 4)
        self.assertEqual(row_card.affinity_value_label.text(), "18.5")
        self.assertEqual(row_card.affinity_value_label.toolTip(), "好感度 18.50")
        self.assertEqual(row_card.event_count_label.text(), "3")
        self.assertEqual(row_card.event_count_label.toolTip(), "事件次數 3")
        self.assertEqual(
            self.panel.race_summary_label.text(),
            "🏁 競賽 12 場　8 勝 4 敗　勝率 66.7%",
        )
        self.assertEqual(
            self.panel.affinity_formula_label.text(),
            "好感度＝熟悉×45%＋信任×30%\n"
            f"{'　' * 5}＋依附×35%－緊張×20%",
        )

    def test_selecting_left_avatar_filters_to_that_actor_view(self):
        self.panel.avatar_buttons["Tokai Teio"].click()
        row_card = self.panel.relationship_list.itemWidget(
            self.panel.relationship_list.item(0)
        )

        self.assertEqual(self.binding.calls[-1], "Tokai Teio")
        self.assertEqual(row_card.row.actor_name, "Tokai Teio")
        self.assertEqual(row_card.row.target_name, "Air Groove")

    def test_avatar_hover_refreshes_current_mood_tooltip(self):
        self.binding.moods["Air Groove"] = (18.0, "depressed")

        QApplication.sendEvent(
            self.panel.avatar_buttons["Air Groove"],
            QEvent(QEvent.Type.Enter),
        )

        self.assertIn(
            "心情：非常低落（18/100）",
            self.panel.avatar_buttons["Air Groove"].toolTip(),
        )

    def test_summon_toggle_calls_binding_and_updates_label(self):
        self.panel.summon_buttons["Tokai Teio"].click()

        self.assertEqual(self.binding.summon_calls[-1], ("Tokai Teio", True))
        self.assertTrue(self.panel.summon_buttons["Tokai Teio"].isChecked())
        self.assertEqual(self.panel.summon_buttons["Tokai Teio"].text(), "")
        self.assertIn("隱藏", self.panel.summon_buttons["Tokai Teio"].toolTip())

    def test_page_omits_redundant_refresh_info_and_selected_name_controls(self):
        self.assertFalse(hasattr(self.panel, "refresh_button"))
        self.assertFalse(hasattr(self.panel, "relationship_info_button"))
        self.assertFalse(hasattr(self.panel, "selected_label"))

    def test_unchanged_presentation_keeps_existing_relationship_cards(self):
        original_card = self.panel.relationship_list.itemWidget(
            self.panel.relationship_list.item(0)
        )

        self.panel.refresh_from_binding()

        self.assertIs(
            self.panel.relationship_list.itemWidget(
                self.panel.relationship_list.item(0)
            ),
            original_card,
        )

    def test_avatar_without_runtime_or_relationship_member_is_disabled(self):
        self.assertFalse(self.panel.avatar_buttons["Sirius Symboli"].isEnabled())
        self.assertFalse(self.panel.summon_buttons["Sirius Symboli"].isEnabled())


class DashboardRelationSummonBindingTests(unittest.TestCase):
    def test_binding_combines_structured_relationships_and_summon_states(self):
        relationship = RelationshipTablePresentation(
            title="關係表",
            table_text="relationship text",
            actor_names=("Air Groove", "Tokai Teio"),
            rows=(
                relationship_row("Air Groove", "Tokai Teio"),
                relationship_row("Tokai Teio", "Air Groove"),
            ),
        )

        class Controller:
            def __init__(self):
                self.visibility_calls = []

            def build_relationship_table_presentation(self, dashboard):
                return relationship

            def set_pet_visibility_by_name(self, dashboard, character_name, summoned):
                self.visibility_calls.append((dashboard, character_name, summoned))
                return True

        dashboard = SimpleNamespace(controller=Controller())
        dashboard.get_pet_summon_states = lambda: (
            ("Air Groove", True, 72.0, "normal"),
            ("Tokai Teio", False, 34.0, "unhappy"),
        )
        dashboard.get_household_state_snapshot = lambda: SimpleNamespace(
            race_statistics=SimpleNamespace(
                entries={
                    "Air Groove": SimpleNamespace(
                        completed_races=5,
                        wins=3,
                        losses=2,
                        win_rate=60.0,
                    )
                }
            )
        )
        binding = DashboardRelationSummonBinding(dashboard)

        presentation = binding.presentation("Air Groove")
        mood_snapshot = binding.mood_snapshot()
        result = binding.set_summoned("Tokai Teio", True)

        self.assertEqual(presentation.selected_character_name, "Air Groove")
        self.assertEqual(presentation.relationship_rows, (relationship.rows[0],))
        self.assertEqual(presentation.race_summary.completed_races, 5)
        self.assertEqual(presentation.race_summary.win_rate, 60.0)
        self.assertTrue(presentation.members[0].summoned)
        self.assertEqual(presentation.members[0].mood_score, 72.0)
        self.assertEqual(presentation.members[0].mood_state, "normal")
        self.assertEqual(mood_snapshot["Tokai Teio"], (34.0, "unhappy"))
        self.assertTrue(result)
        self.assertEqual(
            dashboard.controller.visibility_calls,
            [(dashboard, "Tokai Teio", True)],
        )


class DashboardRelationSummonRefreshTests(unittest.TestCase):
    def test_relationship_event_refreshes_visible_current_relation_page(self):
        information_center = SimpleNamespace(
            is_page_visible=lambda page_id: (
                page_id == PAGE_RELATION_SUMMON
            ),
            refresh_calls=0,
        )

        def refresh_relation_summon():
            information_center.refresh_calls += 1

        information_center.refresh_relation_summon = refresh_relation_summon
        dashboard = SimpleNamespace(
            relationship_table_window=None,
            information_center_window=information_center,
        )

        Dashboard.refresh_relationship_table_if_open(dashboard)

        self.assertEqual(information_center.refresh_calls, 1)

    def test_relationship_event_does_not_refresh_background_page(self):
        information_center = SimpleNamespace(
            is_page_visible=lambda page_id: False,
            refresh_calls=0,
        )
        information_center.refresh_relation_summon = lambda: setattr(
            information_center,
            "refresh_calls",
            information_center.refresh_calls + 1,
        )
        dashboard = SimpleNamespace(
            relationship_table_window=None,
            information_center_window=information_center,
        )

        Dashboard.refresh_relationship_table_if_open(dashboard)

        self.assertEqual(information_center.refresh_calls, 0)


if __name__ == "__main__":
    unittest.main()
