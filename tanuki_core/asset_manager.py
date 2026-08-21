import os
import random
import sys

from .asset_loader import (
    AssetStore,
    extract_frames,
    get_runtime_asset_file_names,
    get_runtime_asset_file_names_for_contexts,
    get_shared_asset_store_cache,
    get_shared_frame_cache,
    load_asset_store,
)
from .asset_selection_rules import (
    choose_weighted_result as choose_weighted_result_rule,
    get_mood_band as get_mood_band_rule,
    get_mood_rules as get_mood_rules_rule,
    get_record_weight as get_record_weight_rule,
    is_record_eligible as is_record_eligible_rule,
    select_contextual_result,
    select_contextual_result_for_candidates,
    select_contextual_result_for_purposes,
    select_result_by_score,
    select_result_for_preferences,
    select_safe_result,
)
from .validation import load_manifest_entries


def is_frozen_runtime():
    return "__compiled__" in globals() or getattr(sys, "frozen", False)


def get_runtime_base_path():
    if is_frozen_runtime():
        executable = getattr(sys, "executable", None) or sys.argv[0]
        return os.path.dirname(os.path.abspath(executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_resource_base_path():
    if is_frozen_runtime():
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            return meipass
        return get_runtime_base_path()
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))



class AssetManager:
    """
    負責解析檔名、載入 GIF 幀、縮放並快取素材。
    檔名規則解析：purpose_action-mood.gif (例如: move_walk-happy.gif)
    """

    def __init__(self, character_path, scale_factor=0.4, frame_cache=None, store_cache=None):
        self.character_path = character_path
        self.scale_factor = scale_factor
        self.frame_cache = frame_cache or get_shared_frame_cache()
        self.store_cache = store_cache or get_shared_asset_store_cache()
        self.store = AssetStore.empty()
        self._runtime_file_names = set()
        self._loaded_file_names = set()
        self._all_runtime_assets_loaded = False
        self.refresh_assets()

    @property
    def assets(self):
        return self.store.assets

    @property
    def asset_records(self):
        return self.store.asset_records

    @property
    def manifest_data(self):
        return self.store.manifest_data

    def load_manifest(self):
        manifest_path = os.path.join(self.character_path, "manifest_edit.json")
        manifest, warnings = load_manifest_entries(manifest_path)
        for warning in warnings:
            print(f"manifest 提示 {self.character_path}: {warning}")
        return manifest

    def get_mood_band(self, mood_score):
        return get_mood_band_rule(mood_score)

    def get_record(self, purpose, action_type, mood):
        return self.store.get_record(purpose, action_type, mood)

    def get_action_keys_for_context(self, purpose, mood_score=None, context=None):
        self.ensure_context_assets(context)
        keys = []
        for action_type, mood_map in self.asset_records.get(purpose, {}).items():
            for mood_tag in mood_map.keys():
                record = self.get_record(purpose, action_type, mood_tag)
                if self.is_record_eligible(record, mood_score=mood_score, context=context):
                    keys.append(action_type)
                    break
        return keys

    def get_record_weight(self, record):
        return get_record_weight_rule(record)

    def is_record_eligible(self, record, mood_score=None, context=None):
        return is_record_eligible_rule(record, mood_score=mood_score, context=context)

    def choose_weighted_result(self, results):
        return choose_weighted_result_rule(results, rng=random)

    def get_safe_frames(self, purpose, mood_list, forbidden=None):
        if purpose not in self.assets:
            return self.get_any_available_frames()
        result = select_safe_result(
            self.assets[purpose],
            mood_list,
            get_record=lambda selected_action, selected_mood: self.get_record(purpose, selected_action, selected_mood),
            forbidden=forbidden,
            rng=random,
        )
        if result:
            return result[0]
        return self.get_any_available_frames()

    def get_safe_reaction_result(self, purpose, mood_list, forbidden=None):
        if purpose not in self.assets:
            return None
        result = select_safe_result(
            self.assets[purpose],
            mood_list,
            get_record=lambda selected_action, selected_mood: self.get_record(purpose, selected_action, selected_mood),
            forbidden=forbidden,
            rng=random,
        )
        if result:
            return result
        fallback = self.get_any_available_frames()
        if fallback:
            return fallback, "default", ""
        return None

    def get_mood_rules(self, mood_score, is_adult=False):
        return get_mood_rules_rule(mood_score, is_adult=is_adult)

    def get_frames_by_score(self, purpose, action_type=None, mood_score=60.0, is_adult=False, context=None):
        self.ensure_context_assets(context)
        if purpose not in self.assets:
            return self.get_any_available_frames(), "default", ""

        weighted = select_result_by_score(
            self.assets[purpose],
            get_record=lambda selected_action, selected_mood: self.get_record(purpose, selected_action, selected_mood),
            action_type=action_type,
            mood_score=mood_score,
            is_adult=is_adult,
            context=context,
            manifest_present=bool(self.manifest_data),
            rng=random,
        )
        if weighted:
            return weighted
        if self.manifest_data:
            return None
        return self.get_any_available_frames(), "default", ""

    def get_frames_for_action_by_score(self, purpose, action_type, mood_score=60.0, is_adult=False, context=None):
        self.ensure_context_assets(context)
        if purpose not in self.assets or action_type not in self.assets[purpose]:
            return None

        return select_result_by_score(
            {action_type: self.assets[purpose][action_type]},
            get_record=lambda selected_action, selected_mood: self.get_record(purpose, selected_action, selected_mood),
            action_type=action_type,
            mood_score=mood_score,
            is_adult=is_adult,
            context=context,
            manifest_present=True,
            rng=random,
        )

    def get_frames_for_action_by_preferences(self, purpose, action_type, preferred_moods, forbidden=None, mood_score=None, context=None):
        self.ensure_context_assets(context)
        if purpose not in self.assets or action_type not in self.assets[purpose]:
            return None
        return select_result_for_preferences(
            self.assets[purpose],
            action_type,
            preferred_moods,
            get_record=lambda selected_action, selected_mood: self.get_record(purpose, selected_action, selected_mood),
            forbidden=forbidden,
            mood_score=mood_score,
            context=context,
            rng=random,
        )

    def get_contextual_result(
        self,
        purpose,
        context=None,
        preferred_moods=None,
        forbidden=None,
        mood_score=None,
        ordered_preferences=False,
    ):
        self.ensure_context_assets(context)
        if purpose not in self.asset_records:
            return None
        return select_contextual_result(
            self.asset_records[purpose],
            context=context,
            preferred_moods=preferred_moods,
            forbidden=forbidden,
            mood_score=mood_score,
            ordered_preferences=ordered_preferences,
            rng=random,
        )

    def get_contextual_result_for_purposes(
        self,
        purposes,
        context=None,
        preferred_moods=None,
        forbidden=None,
        mood_score=None,
        ordered_preferences=False,
    ):
        self.ensure_context_assets(context)
        return select_contextual_result_for_purposes(
            self.asset_records,
            purposes,
            context=context,
            preferred_moods=preferred_moods,
            forbidden=forbidden,
            mood_score=mood_score,
            ordered_preferences=ordered_preferences,
            rng=random,
        )

    def get_contextual_result_for_candidates(
        self,
        candidates,
        context=None,
        preferred_moods=None,
        forbidden=None,
        mood_score=None,
        ordered_preferences=False,
        rng=None,
    ):
        self.ensure_context_assets(context)
        return select_contextual_result_for_candidates(
            self.asset_records,
            candidates,
            context=context,
            preferred_moods=preferred_moods,
            forbidden=forbidden,
            mood_score=mood_score,
            ordered_preferences=ordered_preferences,
            rng=rng or random,
        )

    def get_contextual_result_for_any_purpose(
        self,
        context=None,
        preferred_moods=None,
        forbidden=None,
        mood_score=None,
        ordered_preferences=False,
    ):
        self.ensure_context_assets(context)
        return select_contextual_result_for_purposes(
            self.asset_records,
            tuple(self.asset_records.keys()),
            context=context,
            preferred_moods=preferred_moods,
            forbidden=forbidden,
            mood_score=mood_score,
            ordered_preferences=ordered_preferences,
            rng=random,
        )

    @staticmethod
    def get_resource_path(relative_path):
        writable_names = {"config.json"}
        base = get_runtime_base_path() if relative_path in writable_names else get_resource_base_path()
        return os.path.join(base, relative_path)

    def refresh_assets(self):
        if not os.path.exists(self.character_path):
            self.store = AssetStore.empty()
            self._runtime_file_names = set()
            self._loaded_file_names = set()
            self._all_runtime_assets_loaded = False
            return
        manifest_data = self.load_manifest()
        self._runtime_file_names = set(get_runtime_asset_file_names(self.character_path, manifest_data))
        file_names = sorted(self._runtime_file_names)
        self._loaded_file_names = set(file_names)
        self._all_runtime_assets_loaded = self._runtime_file_names.issubset(
            self._loaded_file_names
        )
        self.store = load_asset_store(
            self.character_path,
            manifest_data,
            self.scale_factor,
            frame_extractor=lambda gif_path, scale_factor: extract_frames(
                gif_path,
                scale_factor,
                frame_cache=self.frame_cache,
            ),
            file_names=file_names,
            error_sink=lambda file_name, exc: print(f"解析失敗 {file_name}: {exc}"),
            store_cache=self.store_cache,
        )

    def ensure_context_assets(self, context):
        if not context or not self.manifest_data:
            return
        if self._all_runtime_assets_loaded:
            return
        context_file_names = set(
            get_runtime_asset_file_names_for_contexts(
                self.character_path,
                self.manifest_data,
                context,
            )
        )
        missing = sorted(context_file_names - self._loaded_file_names)
        if not missing:
            return
        partial_store = load_asset_store(
            self.character_path,
            self.manifest_data,
            self.scale_factor,
            frame_extractor=lambda gif_path, scale_factor: extract_frames(
                gif_path,
                scale_factor,
                frame_cache=self.frame_cache,
            ),
            file_names=missing,
            error_sink=lambda file_name, exc: print(f"解析失敗 {file_name}: {exc}"),
            store_cache=None,
        )
        self._merge_store(partial_store)
        self._loaded_file_names.update(missing)
        self._all_runtime_assets_loaded = self._runtime_file_names.issubset(
            self._loaded_file_names
        )

    def _merge_store(self, partial_store):
        for purpose, action_map in partial_store.assets.items():
            target_actions = self.store.assets.setdefault(purpose, {})
            for action_type, mood_map in action_map.items():
                target_moods = target_actions.setdefault(action_type, {})
                target_moods.update(mood_map)
        for purpose, action_map in partial_store.asset_records.items():
            target_actions = self.store.asset_records.setdefault(purpose, {})
            for action_type, mood_map in action_map.items():
                target_moods = target_actions.setdefault(action_type, {})
                target_moods.update(mood_map)

    def get_any_available_frames(self):
        return self.store.get_any_available_frames()

    def get_specific_frames(self, purpose, action_type, mood, mood_score=None, context=None):
        self.ensure_context_assets(context)
        record = self.get_record(purpose, action_type, mood)
        if self.is_record_eligible(record, mood_score=mood_score, context=context):
            return record["frames"]
        return None

    def get_action_keys(self, purpose):
        return self.store.get_action_keys(purpose)

    def has_action(self, purpose, action_type):
        return self.store.has_action(purpose, action_type)
