import os
from dataclasses import dataclass

from PyQt6.QtCore import QRect
from PyQt6.QtGui import QImageReader, QMovie, QPixmap

from .ui_skin_spec import FAMILY_AVATAR_SPECS, UI_ASSET_SPECS, UI_SKIN_SPECS


class UiSkinAssetError(RuntimeError):
    pass


@dataclass(frozen=True)
class UiSkinAssetIssue:
    asset_key: str
    relative_path: str
    message: str


class UiSkinAssets:
    def __init__(self, resource_resolver, asset_specs=None, skin_specs=None, avatar_specs=None):
        if not callable(resource_resolver):
            raise TypeError("resource_resolver must be callable")
        self.resource_resolver = resource_resolver
        self.asset_specs = UI_ASSET_SPECS if asset_specs is None else asset_specs
        self.skin_specs = UI_SKIN_SPECS if skin_specs is None else skin_specs
        self.avatar_specs = FAMILY_AVATAR_SPECS if avatar_specs is None else tuple(avatar_specs)

    def get_asset_spec(self, asset_key):
        try:
            return self.asset_specs[asset_key]
        except KeyError as exc:
            raise UiSkinAssetError(f"unknown UI asset: {asset_key}") from exc

    def get_skin_spec(self, skin_key):
        try:
            return self.skin_specs[skin_key]
        except KeyError as exc:
            raise UiSkinAssetError(f"unknown UI skin: {skin_key}") from exc

    def resolve_asset_path(self, asset_key):
        spec = self.get_asset_spec(asset_key)
        return os.path.normpath(str(self.resource_resolver(spec.relative_path)))

    def validate_assets(self, asset_keys=None):
        keys = tuple(self.asset_specs) if asset_keys is None else tuple(asset_keys)
        issues = []
        for asset_key in keys:
            spec = self.get_asset_spec(asset_key)
            path = self.resolve_asset_path(asset_key)
            if not os.path.isfile(path):
                issues.append(UiSkinAssetIssue(asset_key, spec.relative_path, "file is missing"))
                continue

            reader = QImageReader(path)
            if not reader.canRead():
                issues.append(UiSkinAssetIssue(asset_key, spec.relative_path, "file is not a readable image"))
                continue
            size = reader.size()
            actual_size = (size.width(), size.height())
            if actual_size != spec.source_size:
                issues.append(
                    UiSkinAssetIssue(
                        asset_key,
                        spec.relative_path,
                        f"declared size {spec.source_size} does not match {actual_size}",
                    )
                )
            if spec.animated and not reader.supportsAnimation():
                issues.append(
                    UiSkinAssetIssue(
                        asset_key,
                        spec.relative_path,
                        "asset is declared animated but is not animated",
                    )
                )
        return tuple(issues)

    def load_pixmap(self, asset_key):
        spec = self.get_asset_spec(asset_key)
        pixmap = QPixmap(self.resolve_asset_path(asset_key))
        if pixmap.isNull():
            raise UiSkinAssetError(f"failed to load UI image: {spec.relative_path}")
        return pixmap

    def load_first_frame(self, asset_key):
        spec = self.get_asset_spec(asset_key)
        reader = QImageReader(self.resolve_asset_path(asset_key))
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            raise UiSkinAssetError(f"failed to read first frame: {spec.relative_path}")
        return QPixmap.fromImage(image)

    def load_avatar_pixmap(self, avatar_spec):
        pixmap = self.load_first_frame(avatar_spec.asset_key)
        crop_rect = avatar_spec.crop_rect
        if crop_rect is None:
            return pixmap
        source_rect = QRect(
            int(round(pixmap.width() * crop_rect.x)),
            int(round(pixmap.height() * crop_rect.y)),
            max(1, int(round(pixmap.width() * crop_rect.width))),
            max(1, int(round(pixmap.height() * crop_rect.height))),
        ).intersected(pixmap.rect())
        return pixmap.copy(source_rect)

    def create_movie(self, asset_key, parent=None):
        spec = self.get_asset_spec(asset_key)
        if not spec.animated:
            raise UiSkinAssetError(f"asset is not animated: {spec.relative_path}")
        movie = QMovie(self.resolve_asset_path(asset_key), parent=parent)
        movie.setCacheMode(QMovie.CacheMode.CacheAll)
        if not movie.isValid():
            movie.deleteLater()
            raise UiSkinAssetError(f"failed to load UI movie: {spec.relative_path}")
        return movie
