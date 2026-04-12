import os
import random
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMovie, QPixmap

from .validation import load_manifest_entries


def get_base_path():
    if "__compiled__" in globals() or getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class AssetManager:
    """
    負責解析檔名、載入 GIF 幀、縮放並快取素材。
    檔名規則解析：purpose_action-mood.gif (例如: move_walk-happy.gif)
    """

    def __init__(self, character_path, scale_factor=0.4):
        self.character_path = character_path
        self.scale_factor = scale_factor
        self.assets = {}
        self.asset_records = {}
        self.manifest_data = {}
        self.refresh_assets()

    def load_manifest(self):
        manifest_path = os.path.join(self.character_path, "manifest_edit.json")
        manifest, warnings = load_manifest_entries(manifest_path)
        for warning in warnings:
            print(f"manifest 提示 {self.character_path}: {warning}")
        return manifest

    def normalize_manifest_entry(self, meta):
        bands = []
        for raw_band in meta.get("band", []):
            if not isinstance(raw_band, str):
                continue
            normalized = raw_band.replace(".", ",")
            for token in normalized.split(","):
                band = token.strip()
                if band in {"normal", "low", "severe"} and band not in bands:
                    bands.append(band)
        contexts = []
        for raw_context in meta.get("contexts", []):
            if not isinstance(raw_context, str):
                continue
            context = raw_context.strip()
            if context and context not in contexts:
                contexts.append(context)
        try:
            weight = float(meta.get("weight", 1.0))
        except (TypeError, ValueError):
            weight = 1.0
        return {
            "band": bands,
            "contexts": contexts,
            "weight": max(0.0, weight),
        }

    def get_mood_band(self, mood_score):
        if mood_score < 20:
            return "severe"
        if mood_score < 50:
            return "low"
        return "normal"

    def get_record(self, purpose, action_type, mood):
        return self.asset_records.get(purpose, {}).get(action_type, {}).get(mood)

    def get_action_keys_for_context(self, purpose, mood_score=None, context=None):
        keys = []
        for action_type, mood_map in self.asset_records.get(purpose, {}).items():
            for mood_tag in mood_map.keys():
                record = self.get_record(purpose, action_type, mood_tag)
                if self.is_record_eligible(record, mood_score=mood_score, context=context):
                    keys.append(action_type)
                    break
        return keys

    def get_record_weight(self, record):
        if not record:
            return 1.0
        meta = record.get("manifest") or {}
        return max(0.0, float(meta.get("weight", 1.0) or 0.0))

    def is_record_eligible(self, record, mood_score=None, context=None):
        if not record:
            return False
        meta = record.get("manifest") or {}
        bands = meta.get("band") or []
        if mood_score is not None and bands:
            if self.get_mood_band(mood_score) not in bands:
                return False
        contexts = meta.get("contexts") or []
        if context and contexts and context not in contexts:
            return False
        return True

    def choose_weighted_result(self, results):
        if not results:
            return None
        weights = [max(0.0, result[3]) for result in results]
        if any(weight > 0 for weight in weights):
            chosen = random.choices(results, weights=weights, k=1)[0]
        else:
            chosen = random.choice(results)
        return chosen[0], chosen[1], chosen[2]

    def get_safe_frames(self, purpose, mood_list, forbidden=None):
        if forbidden is None:
            forbidden = []
        if purpose not in self.assets:
            return self.get_any_available_frames()
        available_types = self.assets[purpose]
        type_keys = list(available_types.keys())
        random.shuffle(type_keys)
        for mood_tag in mood_list:
            for t_key in type_keys:
                mood_map = available_types[t_key]
                if mood_tag in mood_map:
                    return mood_map[mood_tag]
        for t_key in type_keys:
            mood_map = available_types[t_key]
            safe_keys = [k for k in mood_map.keys() if k not in forbidden]
            if safe_keys:
                if "normal" in safe_keys:
                    return mood_map["normal"]
                return mood_map[random.choice(safe_keys)]
        return self.get_any_available_frames()

    def get_safe_reaction_result(self, purpose, mood_list, forbidden=None):
        if forbidden is None:
            forbidden = []
        if purpose not in self.assets:
            return None
        available_types = self.assets[purpose]
        type_keys = list(available_types.keys())
        random.shuffle(type_keys)
        for mood_tag in mood_list:
            for action_type in type_keys:
                record = self.get_record(purpose, action_type, mood_tag)
                if record:
                    return record["frames"], action_type, mood_tag
        for action_type in type_keys:
            mood_map = available_types[action_type]
            safe_keys = [tag for tag in mood_map.keys() if tag not in forbidden]
            if safe_keys:
                chosen_mood = "normal" if "normal" in safe_keys else random.choice(safe_keys)
                record = self.get_record(purpose, action_type, chosen_mood)
                if record:
                    return record["frames"], action_type, chosen_mood
        fallback = self.get_any_available_frames()
        if fallback:
            return fallback, "default", ""
        return None

    def get_mood_rules(self, mood_score, is_adult=False):
        if mood_score < 20:
            if is_adult:
                return (
                    ["scold", "sad", "angry", "exhausted"],
                    ["awkward", "think", "hurry", "effort", "sleep"],
                    ["happy", "smile", "confidence", "cool", "cry", "hard-cry", "scared"],
                )
            return (
                ["scold", "hard-cry", "cry", "exhausted", "scared"],
                ["sad", "angry", "awkward", "think", "hurry", "effort", "sleep"],
                ["happy", "smile", "confidence", "cool"],
            )
        if mood_score < 50:
            return (
                ["angry", "sad", "think", "awkward", "hurry", "effort", "sleep"],
                ["cry", "hard-cry", "scold", "exhausted", "scared"],
                ["happy", "smile", "confidence", "cool"],
            )
        return (
            ["happy", "smile", "confidence", "cool", "glance"],
            ["awkward", "think"],
            ["cry", "hard-cry", "sad", "angry", "scold"],
        )

    def get_frames_by_score(self, purpose, action_type=None, mood_score=60.0, is_adult=False, context=None):
        if purpose not in self.assets:
            return self.get_any_available_frames(), "default", ""

        available_types = self.assets[purpose]
        priority_chain, fallback_chain, forbidden = self.get_mood_rules(mood_score, is_adult=is_adult)

        if action_type in available_types:
            for mood_tag in priority_chain + fallback_chain:
                record = self.get_record(purpose, action_type, mood_tag)
                if self.is_record_eligible(record, mood_score=mood_score, context=context):
                    return record["frames"], action_type, mood_tag

        type_keys = list(available_types.keys())
        if action_type in type_keys:
            type_keys.remove(action_type)
            type_keys.insert(0, action_type)
        for mood_tag in priority_chain + fallback_chain:
            matches = []
            for t_key in type_keys:
                record = self.get_record(purpose, t_key, mood_tag)
                if self.is_record_eligible(record, mood_score=mood_score, context=context):
                    matches.append((record["frames"], t_key, mood_tag, self.get_record_weight(record)))
            weighted = self.choose_weighted_result(matches)
            if weighted:
                return weighted

        target_action = action_type if action_type in available_types else random.choice(list(available_types.keys()))
        safe_results = []
        normal_result = None
        for mood_tag in available_types[target_action].keys():
            if mood_tag in forbidden:
                continue
            record = self.get_record(purpose, target_action, mood_tag)
            if not self.is_record_eligible(record, mood_score=mood_score, context=context):
                continue
            result = (record["frames"], target_action, mood_tag, self.get_record_weight(record))
            if mood_tag == "normal":
                normal_result = result
            safe_results.append(result)
        if normal_result:
            return normal_result[0], normal_result[1], normal_result[2]
        weighted = self.choose_weighted_result(safe_results)
        if weighted:
            return weighted
        if self.manifest_data:
            return None
        return self.get_any_available_frames(), "default", ""

    def get_frames_for_action_by_score(self, purpose, action_type, mood_score=60.0, is_adult=False, context=None):
        if purpose not in self.assets or action_type not in self.assets[purpose]:
            return None

        priority_chain, fallback_chain, forbidden = self.get_mood_rules(mood_score, is_adult=is_adult)

        for mood_tag in priority_chain + fallback_chain:
            record = self.get_record(purpose, action_type, mood_tag)
            if self.is_record_eligible(record, mood_score=mood_score, context=context):
                return record["frames"], action_type, mood_tag

        safe_results = []
        normal_result = None
        for mood_tag in self.assets[purpose][action_type].keys():
            if mood_tag in forbidden:
                continue
            record = self.get_record(purpose, action_type, mood_tag)
            if not self.is_record_eligible(record, mood_score=mood_score, context=context):
                continue
            result = (record["frames"], action_type, mood_tag, self.get_record_weight(record))
            if mood_tag == "normal":
                normal_result = result
            safe_results.append(result)
        if normal_result:
            return normal_result[0], normal_result[1], normal_result[2]
        weighted = self.choose_weighted_result(safe_results)
        if weighted:
            return weighted

        return None

    def get_frames_for_action_by_preferences(self, purpose, action_type, preferred_moods, forbidden=None, mood_score=None, context=None):
        if purpose not in self.assets or action_type not in self.assets[purpose]:
            return None
        for mood_tag in preferred_moods:
            record = self.get_record(purpose, action_type, mood_tag)
            if self.is_record_eligible(record, mood_score=mood_score, context=context):
                return record["frames"], action_type, mood_tag
        if forbidden is None:
            forbidden = []
        safe_results = []
        normal_result = None
        for mood_tag in self.assets[purpose][action_type].keys():
            if mood_tag in forbidden:
                continue
            record = self.get_record(purpose, action_type, mood_tag)
            if not self.is_record_eligible(record, mood_score=mood_score, context=context):
                continue
            result = (record["frames"], action_type, mood_tag, self.get_record_weight(record))
            if mood_tag == "normal":
                normal_result = result
            safe_results.append(result)
        if normal_result:
            return normal_result[0], normal_result[1], normal_result[2]
        weighted = self.choose_weighted_result(safe_results)
        if weighted:
            return weighted
        return None

    def get_contextual_result(self, purpose, context=None, preferred_moods=None):
        if purpose not in self.asset_records:
            return None
        preferred_moods = preferred_moods or []
        preferred_results = []
        fallback_results = []
        for action_type, mood_map in self.asset_records[purpose].items():
            for mood_tag, record in mood_map.items():
                meta = record.get("manifest") or {}
                contexts = meta.get("contexts") or []
                if context and contexts and context not in contexts:
                    continue
                result = (
                    record["frames"],
                    action_type,
                    mood_tag,
                    self.get_record_weight(record),
                )
                if mood_tag in preferred_moods:
                    preferred_results.append(result)
                else:
                    fallback_results.append(result)
        weighted = self.choose_weighted_result(preferred_results)
        if weighted:
            return weighted
        return self.choose_weighted_result(fallback_results)

    @staticmethod
    def get_resource_path(relative_path):
        base = get_base_path()
        return os.path.join(base, relative_path)

    def refresh_assets(self):
        if not os.path.exists(self.character_path):
            return
        self.assets = {}
        self.asset_records = {}
        self.manifest_data = self.load_manifest()
        files = [f for f in os.listdir(self.character_path) if f.endswith(".gif")]
        for file in files:
            try:
                base_name, _ = os.path.splitext(file)
                mood = base_name.split("-", 1)[1] if "-" in base_name else ""
                name_part = base_name.split("-", 1)[0]

                parts = name_part.split("_")
                purpose = parts[0]
                action_type = "_".join(parts[1:]) if len(parts) > 1 else "default"

                frames = self.extract_frames(os.path.join(self.character_path, file))
                if frames:
                    if purpose not in self.assets:
                        self.assets[purpose] = {}
                    if purpose not in self.asset_records:
                        self.asset_records[purpose] = {}
                    if action_type not in self.assets[purpose]:
                        self.assets[purpose][action_type] = {}
                    if action_type not in self.asset_records[purpose]:
                        self.asset_records[purpose][action_type] = {}
                    self.assets[purpose][action_type][mood] = frames
                    self.asset_records[purpose][action_type][mood] = {
                        "frames": frames,
                        "file_name": file,
                        "manifest": self.manifest_data.get(file, {}),
                    }
            except Exception as exc:
                print(f"解析失敗 {file}: {exc}")

    def extract_frames(self, gif_path):
        movie = QMovie(gif_path)
        movie.setCacheMode(QMovie.CacheMode.CacheAll)
        movie.jumpToFrame(0)
        frames = []
        count = movie.frameCount()
        for i in range(max(1, count)):
            movie.jumpToFrame(i)
            img = movie.currentImage()
            if img.isNull():
                break
            scaled_img = img.scaled(
                img.size() * self.scale_factor,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            frames.append(QPixmap.fromImage(scaled_img))
        return frames

    def get_any_available_frames(self):
        for purpose_map in self.assets.values():
            for type_map in purpose_map.values():
                for frames in type_map.values():
                    return frames
        return []

    def get_specific_frames(self, purpose, action_type, mood, mood_score=None, context=None):
        record = self.get_record(purpose, action_type, mood)
        if self.is_record_eligible(record, mood_score=mood_score, context=context):
            return record["frames"]
        return None

    def get_action_keys(self, purpose):
        return list(self.assets.get(purpose, {}).keys())

    def has_action(self, purpose, action_type):
        return action_type in self.assets.get(purpose, {})
