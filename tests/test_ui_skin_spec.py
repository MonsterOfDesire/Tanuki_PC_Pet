import unittest

from tanuki_core.ui_skin_spec import (
    ASSET_DASHBOARD_SIDE_ICON,
    FAMILY_AVATAR_SPECS,
    FIT_CONTAIN,
    FIT_COVER,
    OCCLUSION_DARK_PIXELS,
    SKIN_DIET,
    SKIN_EVENT_LOG,
    SKIN_FAMILY_STATUS,
    SKIN_RELATION_SUMMON,
    SKIN_STATUS_SETTINGS,
    UI_ASSET_SPECS,
    UI_SKIN_SPECS,
    GeometryRect,
    NormalizedRect,
    NormalizedLayerRect,
    align_scene_to_focus,
    compute_content_rect,
    compute_scene_rect,
    compute_skinned_scene_layout,
    expand_rect_to_minimum,
    intersect_geometry_rect,
    iter_runtime_asset_paths,
    project_normalized_rect,
)


class UiSkinSpecTests(unittest.TestCase):
    def test_scene_rect_centers_contained_asset(self):
        rect = compute_scene_rect((100, 100), (200, 100), FIT_CONTAIN)

        self.assertEqual(rect, GeometryRect(0.0, 25.0, 100.0, 50.0))

    def test_scene_rect_centers_covering_asset(self):
        rect = compute_scene_rect((100, 100), (200, 100), FIT_COVER)

        self.assertEqual(rect, GeometryRect(-50.0, 0.0, 200.0, 100.0))

    def test_project_normalized_rect_uses_outer_coordinate_space(self):
        result = project_normalized_rect(
            NormalizedRect(0.25, 0.20, 0.50, 0.60),
            GeometryRect(10.0, 20.0, 200.0, 100.0),
        )

        self.assertEqual(result, GeometryRect(60.0, 40.0, 100.0, 60.0))

    def test_minimum_rect_expands_and_stays_inside_frame(self):
        result = expand_rect_to_minimum(
            GeometryRect(-20.0, 30.0, 80.0, 40.0),
            (120, 70),
            GeometryRect(0.0, 0.0, 200.0, 100.0),
        )

        self.assertEqual(result, GeometryRect(0.0, 15.0, 120.0, 70.0))

    def test_oversized_scene_centers_and_preserves_focus_area(self):
        scene = align_scene_to_focus(
            (520, 320),
            (1080, 608),
            GeometryRect(435, 35, 480, 300),
        )

        self.assertLess(scene.x, 0)
        self.assertLess(scene.y, 0)
        self.assertGreaterEqual(scene.x + 435, 0)
        self.assertLessEqual(scene.x + 435 + 480, 520)
        self.assertGreaterEqual(scene.y + 35, 0)
        self.assertLessEqual(scene.y + 35 + 300, 320)

    def test_intersection_limits_geometry_to_scene_viewport(self):
        result = intersect_geometry_rect(
            GeometryRect(20.0, 10.0, 80.0, 60.0),
            GeometryRect(0.0, 0.0, 70.0, 50.0),
        )

        self.assertEqual(result, GeometryRect(20.0, 10.0, 50.0, 40.0))

    def test_relation_content_never_shrinks_below_declared_minimum(self):
        skin = UI_SKIN_SPECS[SKIN_RELATION_SUMMON]
        content = compute_content_rect(skin.minimum_frame_size, skin)

        self.assertGreaterEqual(content.width, skin.minimum_content_size[0])
        self.assertGreaterEqual(content.height, skin.minimum_content_size[1])

    def test_compact_relation_crops_scene_before_shrinking_content(self):
        skin = UI_SKIN_SPECS[SKIN_RELATION_SUMMON]

        scene, local_content = compute_skinned_scene_layout(
            skin.minimum_window_size,
            skin,
        )
        content = compute_content_rect(skin.minimum_window_size, skin)

        self.assertLess(scene.x, 0)
        self.assertLess(scene.y, 0)
        self.assertEqual(
            (content.width, content.height),
            tuple(float(value) for value in skin.minimum_content_size),
        )
        self.assertGreaterEqual(content.x, 0)
        self.assertGreaterEqual(content.y, 0)
        self.assertLessEqual(content.right, skin.minimum_window_size[0])
        self.assertLessEqual(content.bottom, skin.minimum_window_size[1])
        self.assertEqual(local_content.width, content.width)

    def test_information_skins_separate_scene_floor_from_window_floor(self):
        for skin_key in (
            SKIN_RELATION_SUMMON,
            SKIN_EVENT_LOG,
            SKIN_FAMILY_STATUS,
            SKIN_STATUS_SETTINGS,
        ):
            with self.subTest(skin_key=skin_key):
                skin = UI_SKIN_SPECS[skin_key]
                self.assertLessEqual(
                    skin.minimum_window_size[0],
                    skin.minimum_frame_size[0],
                )
                self.assertLessEqual(
                    skin.minimum_window_size[1],
                    skin.minimum_frame_size[1],
                )
                self.assertNotEqual(
                    skin.minimum_window_size,
                    skin.minimum_frame_size,
                )

    def test_relation_skin_declares_independent_foreground(self):
        skin = UI_SKIN_SPECS[SKIN_RELATION_SUMMON]

        self.assertEqual(skin.foreground_asset_key, "relation_character")
        self.assertIsNotNone(skin.foreground_rect)
        self.assertEqual(skin.fit_mode, FIT_CONTAIN)
        self.assertEqual(skin.occlusion_role, "whiteboard")
        self.assertEqual(len(skin.occlusion_rects), 2)
        self.assertEqual(skin.occlusion_mask_mode, OCCLUSION_DARK_PIXELS)
        self.assertEqual(len(skin.foreground_frame_map), 13)
        self.assertGreater(skin.foreground_rect.x + skin.foreground_rect.width, 1.0)

    def test_each_runtime_skin_declares_its_character_foreground(self):
        expected_foregrounds = {
            SKIN_DIET: "diet_character",
            SKIN_RELATION_SUMMON: "relation_character",
            SKIN_EVENT_LOG: "event_character",
            SKIN_FAMILY_STATUS: "family_character",
            SKIN_STATUS_SETTINGS: "settings_character",
        }

        for skin_key, foreground_asset_key in expected_foregrounds.items():
            with self.subTest(skin_key=skin_key):
                skin = UI_SKIN_SPECS[skin_key]
                self.assertEqual(skin.foreground_asset_key, foreground_asset_key)
                self.assertIsNotNone(skin.foreground_rect)
                self.assertTrue(UI_ASSET_SPECS[foreground_asset_key].animated)

    def test_event_and_family_characters_use_requested_lower_corner_anchors(self):
        event_foreground = UI_SKIN_SPECS[SKIN_EVENT_LOG].foreground_rect
        family_foreground = UI_SKIN_SPECS[SKIN_FAMILY_STATUS].foreground_rect

        self.assertLess(event_foreground.x, 0.0)
        self.assertGreater(event_foreground.y, 0.40)
        self.assertGreater(family_foreground.x, 0.55)
        self.assertGreater(family_foreground.y, 0.45)

    def test_foreground_layer_rect_can_overscan_scene_viewport(self):
        rect = NormalizedLayerRect(0.8, 0.7, 0.5, 0.6)

        self.assertGreater(rect.x + rect.width, 1.0)

    def test_relation_text_mask_stays_clear_of_whiteboard_lower_left_corner(self):
        skin = UI_SKIN_SPECS[SKIN_RELATION_SUMMON]

        self.assertTrue(all(rect.x >= 0.42 for rect in skin.occlusion_rects))
        self.assertLess(skin.occlusion_rects[0].y + skin.occlusion_rects[0].height, 0.31)

    def test_family_avatars_define_independent_first_frame_head_crops(self):
        self.assertEqual(len(FAMILY_AVATAR_SPECS), 5)
        self.assertTrue(all(spec.crop_rect is not None for spec in FAMILY_AVATAR_SPECS))
        self.assertEqual(len({spec.crop_rect.height for spec in FAMILY_AVATAR_SPECS}), 4)
        self.assertTrue(all(UI_ASSET_SPECS[spec.asset_key].first_frame_only for spec in FAMILY_AVATAR_SPECS))

    def test_runtime_paths_exclude_concept_mockups(self):
        paths = iter_runtime_asset_paths()

        self.assertTrue(all(path.startswith("UI/") for path in paths))
        self.assertFalse(any("concepts" in path for path in paths))

    def test_dashboard_launcher_side_icon_is_a_packaged_runtime_asset(self):
        spec = UI_ASSET_SPECS[ASSET_DASHBOARD_SIDE_ICON]

        self.assertEqual(spec.relative_path, "UI/side.png")
        self.assertEqual(spec.source_size, (393, 388))
        self.assertIn("UI/side.png", iter_runtime_asset_paths())


if __name__ == "__main__":
    unittest.main()
