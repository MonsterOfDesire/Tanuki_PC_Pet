import os
from dataclasses import dataclass, field
from collections import OrderedDict


@dataclass
class AssetStore:
    manifest_data: dict
    assets: dict
    asset_records: dict

    @classmethod
    def empty(cls):
        return cls({}, {}, {})

    def get_record(self, purpose, action_type, mood):
        return self.asset_records.get(purpose, {}).get(action_type, {}).get(mood)

    def get_any_available_frames(self):
        for purpose_map in self.assets.values():
            for type_map in purpose_map.values():
                for frames in type_map.values():
                    return frames
        return []

    def get_action_keys(self, purpose):
        return list(self.assets.get(purpose, {}).keys())

    def has_action(self, purpose, action_type):
        return action_type in self.assets.get(purpose, {})


def get_file_signature(gif_path):
    stat = os.stat(gif_path)
    return stat.st_mtime_ns, stat.st_size


@dataclass
class FrameCache:
    signature_getter: callable = get_file_signature
    raw_frames: OrderedDict = field(default_factory=OrderedDict)
    scaled_frames: OrderedDict = field(default_factory=OrderedDict)
    file_signatures: dict = field(default_factory=dict)
    max_raw_entries: int = 512
    max_scaled_entries: int = 1024

    @staticmethod
    def normalize_scale(scale_factor):
        return round(float(scale_factor), 4)

    def _invalidate_stale_entries(self, gif_path):
        signature = self.signature_getter(gif_path)
        previous = self.file_signatures.get(gif_path)
        if previous == signature:
            return signature
        if previous is not None:
            raw_key = (gif_path, previous)
            self.raw_frames.pop(raw_key, None)
            stale_scaled = [key for key in self.scaled_frames if key[:2] == (gif_path, previous)]
            for key in stale_scaled:
                self.scaled_frames.pop(key, None)
        self.file_signatures[gif_path] = signature
        return signature

    @staticmethod
    def _prune_cache(mapping, max_entries):
        while len(mapping) > max_entries:
            mapping.popitem(last=False)

    def clear_path(self, gif_path):
        self.file_signatures.pop(gif_path, None)
        raw_keys = [key for key in self.raw_frames if key[0] == gif_path]
        for key in raw_keys:
            self.raw_frames.pop(key, None)
        scaled_keys = [key for key in self.scaled_frames if key[0] == gif_path]
        for key in scaled_keys:
            self.scaled_frames.pop(key, None)

    def get_raw_frames(self, gif_path, raw_loader):
        signature = self._invalidate_stale_entries(gif_path)
        raw_key = (gif_path, signature)
        if raw_key not in self.raw_frames:
            self.raw_frames[raw_key] = raw_loader(gif_path)
            self._prune_cache(self.raw_frames, self.max_raw_entries)
        else:
            self.raw_frames.move_to_end(raw_key)
        return self.raw_frames[raw_key], signature

    def get_scaled_frames(self, gif_path, scale_factor, *, raw_loader, scaler):
        raw_frames, signature = self.get_raw_frames(gif_path, raw_loader)
        scaled_key = (gif_path, signature, self.normalize_scale(scale_factor))
        if scaled_key not in self.scaled_frames:
            self.scaled_frames[scaled_key] = scaler(raw_frames, scale_factor)
            self._prune_cache(self.scaled_frames, self.max_scaled_entries)
        else:
            self.scaled_frames.move_to_end(scaled_key)
        return self.scaled_frames[scaled_key]


_SHARED_FRAME_CACHE = FrameCache()


def get_shared_frame_cache():
    return _SHARED_FRAME_CACHE


def get_manifest_path(character_path):
    return os.path.join(character_path, "manifest_edit.json")


def parse_asset_filename(file_name):
    base_name, _ = os.path.splitext(file_name)
    mood = base_name.split("-", 1)[1] if "-" in base_name else ""
    name_part = base_name.split("-", 1)[0]
    parts = name_part.split("_")
    purpose = parts[0]
    action_type = "_".join(parts[1:]) if len(parts) > 1 else "default"
    return purpose, action_type, mood


def extract_raw_frames(gif_path):
    from PyQt6.QtGui import QMovie

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
        frames.append(img.copy())
    return frames


def scale_frames(raw_frames, scale_factor):
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QPixmap

    frames = []
    for img in raw_frames:
        scaled_img = img.scaled(
            img.size() * scale_factor,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        frames.append(QPixmap.fromImage(scaled_img))
    return frames


def extract_frames(gif_path, scale_factor, frame_cache=None, raw_loader=None, scaler=None):
    if frame_cache is None:
        frame_cache = get_shared_frame_cache()
    if raw_loader is None:
        raw_loader = extract_raw_frames
    if scaler is None:
        scaler = scale_frames
    return frame_cache.get_scaled_frames(
        gif_path,
        scale_factor,
        raw_loader=raw_loader,
        scaler=scaler,
    )


def get_asset_store_signature(character_path, file_names=None):
    entries = []
    manifest_path = get_manifest_path(character_path)
    manifest_signature = get_file_signature(manifest_path) if os.path.exists(manifest_path) else None
    entries.append(("manifest_edit.json", manifest_signature))

    if file_names is None:
        file_names = sorted(f for f in os.listdir(character_path) if f.endswith(".gif"))

    for file_name in file_names:
        gif_path = os.path.join(character_path, file_name)
        entries.append((file_name, get_file_signature(gif_path)))
    return tuple(entries)


def load_asset_indexes(character_path, manifest_data, scale_factor, frame_extractor=None, file_names=None, error_sink=None):
    assets = {}
    asset_records = {}

    if frame_extractor is None:
        frame_extractor = extract_frames

    if file_names is None:
        file_names = sorted(f for f in os.listdir(character_path) if f.endswith(".gif"))

    for file_name in file_names:
        try:
            purpose, action_type, mood = parse_asset_filename(file_name)
            frames = frame_extractor(os.path.join(character_path, file_name), scale_factor)
            if not frames:
                continue
            assets.setdefault(purpose, {}).setdefault(action_type, {})[mood] = frames
            asset_records.setdefault(purpose, {}).setdefault(action_type, {})[mood] = {
                "frames": frames,
                "file_name": file_name,
                "manifest": manifest_data.get(file_name, {}),
            }
        except Exception as exc:
            if error_sink:
                error_sink(file_name, exc)

    return assets, asset_records


def build_asset_store(character_path, manifest_data, scale_factor, frame_extractor=None, file_names=None, error_sink=None):
    assets, asset_records = load_asset_indexes(
        character_path,
        manifest_data,
        scale_factor,
        frame_extractor=frame_extractor,
        file_names=file_names,
        error_sink=error_sink,
    )
    return AssetStore(manifest_data=manifest_data, assets=assets, asset_records=asset_records)


@dataclass
class AssetStoreCache:
    stores: OrderedDict = field(default_factory=OrderedDict)
    max_entries: int = 16

    @staticmethod
    def normalize_key(character_path, scale_factor):
        return os.path.abspath(character_path), FrameCache.normalize_scale(scale_factor)

    def get_or_load(self, character_path, manifest_data, scale_factor, *, frame_extractor=None, file_names=None, error_sink=None):
        if file_names is None:
            file_names = sorted(f for f in os.listdir(character_path) if f.endswith(".gif"))
        signature = get_asset_store_signature(character_path, file_names=file_names)
        cache_key = self.normalize_key(character_path, scale_factor)
        cached_entry = self.stores.get(cache_key)
        if cached_entry and cached_entry[0] == signature:
            self.stores.move_to_end(cache_key)
            return cached_entry[1]
        store = build_asset_store(
            character_path,
            manifest_data,
            scale_factor,
            frame_extractor=frame_extractor,
            file_names=file_names,
            error_sink=error_sink,
        )
        self.stores[cache_key] = (signature, store)
        self._prune_cache()
        return store

    def _prune_cache(self):
        while len(self.stores) > self.max_entries:
            self.stores.popitem(last=False)

    def clear_character(self, character_path):
        normalized_path = os.path.abspath(character_path)
        stale_keys = [key for key in self.stores if key[0] == normalized_path]
        for key in stale_keys:
            self.stores.pop(key, None)


_SHARED_ASSET_STORE_CACHE = AssetStoreCache()


def get_shared_asset_store_cache():
    return _SHARED_ASSET_STORE_CACHE


def load_asset_store(character_path, manifest_data, scale_factor, frame_extractor=None, file_names=None, error_sink=None, store_cache=None):
    if store_cache is None:
        return build_asset_store(
            character_path,
            manifest_data,
            scale_factor,
            frame_extractor=frame_extractor,
            file_names=file_names,
            error_sink=error_sink,
        )
    return store_cache.get_or_load(
        character_path,
        manifest_data,
        scale_factor,
        frame_extractor=frame_extractor,
        file_names=file_names,
        error_sink=error_sink,
    )
