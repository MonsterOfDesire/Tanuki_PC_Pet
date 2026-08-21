from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QBitmap, QImage, QMovie, QPainter, QRegion
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QWidget

from .ui_skin_spec import (
    GeometryRect,
    compute_scene_rect,
    compute_skinned_scene_layout,
    project_normalized_rect,
    OCCLUSION_DARK_PIXELS,
)
from .ui_theme import DEFAULT_UI_THEME, build_ui_stylesheet


class _ScaledAssetLayer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self._movie = None
        self._frame_offsets = ()
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    @property
    def movie(self):
        return self._movie

    def clear(self):
        if self._movie is not None:
            try:
                self._movie.frameChanged.disconnect(self._on_frame_changed)
            except (TypeError, RuntimeError):
                pass
            self._movie.stop()
            self._movie.deleteLater()
        self._movie = None
        self._pixmap = None
        self._frame_offsets = ()
        self.update()

    def set_pixmap(self, pixmap):
        self.clear()
        self._pixmap = pixmap
        self.update()

    def set_movie(self, movie, frame_offsets=()):
        self.clear()
        self._movie = movie
        self._frame_offsets = tuple(frame_offsets or ())
        self._movie.frameChanged.connect(self._on_frame_changed)
        self._movie.jumpToFrame(0)
        self.update()

    def _on_frame_changed(self, _frame_number):
        self.update()

    def paintEvent(self, event):
        pixmap = self._movie.currentPixmap() if self._movie is not None else self._pixmap
        if pixmap is None or pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        target_rect = self.rect()
        if self._movie is not None and self._frame_offsets:
            frame_number = self._movie.currentFrameNumber()
            if 0 <= frame_number < len(self._frame_offsets):
                offset_x, offset_y = self._frame_offsets[frame_number]
                scale_x = self.width() / max(1, pixmap.width())
                scale_y = self.height() / max(1, pixmap.height())
                target_rect = target_rect.translated(
                    int(round(offset_x * scale_x)),
                    int(round(offset_y * scale_y)),
                )
        painter.drawPixmap(target_rect, pixmap, pixmap.rect())

    def current_pixmap(self):
        return self._movie.currentPixmap() if self._movie is not None else self._pixmap


class SkinnedWindowFrame(QWidget):
    def __init__(
        self,
        assets,
        skin_key,
        parent=None,
        theme=DEFAULT_UI_THEME,
        *,
        defer_skin=False,
    ):
        super().__init__(parent)
        self.assets = assets
        self.theme = theme
        self.skin_spec = None
        self._animation_active = False
        self._frame_sync_movie = None
        self._occlusion_source_bitmap = None
        self._pending_skin_key = None
        self._skin_loaded = False

        self.scene_viewport = QFrame(self)
        self.scene_viewport.setObjectName("tanukiSceneViewport")
        self.scene_viewport.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.background_layer = _ScaledAssetLayer(self.scene_viewport)
        self.occlusion_surface = QFrame(self.scene_viewport)
        self.occlusion_surface.setObjectName("tanukiSkinOcclusionSurface")
        self.content_surface = QFrame(self.scene_viewport)
        self.content_surface.setObjectName("tanukiSkinContentSurface")
        self.content_layout = QVBoxLayout(self.content_surface)
        self.content_layout.setContentsMargins(
            theme.spacing_lg,
            theme.spacing_lg,
            theme.spacing_lg,
            theme.spacing_lg,
        )
        self.content_layout.setSpacing(theme.spacing_md)
        self.foreground_layer = _ScaledAssetLayer(self.scene_viewport)
        self.setStyleSheet(build_ui_stylesheet(theme))
        if defer_skin:
            self._prepare_deferred_skin(skin_key)
        else:
            self.set_skin(skin_key)

    @property
    def skin_loaded(self):
        return self._skin_loaded

    def _prepare_deferred_skin(self, skin_key):
        self._pending_skin_key = str(skin_key)
        self.skin_spec = self.assets.get_skin_spec(skin_key)
        self.setMinimumSize(*self.skin_spec.minimum_window_size)
        self.content_surface.setProperty(
            "surfaceRole",
            self.skin_spec.surface_role,
        )
        self.occlusion_surface.hide()
        self.foreground_layer.hide()

    def ensure_skin_loaded(self):
        if self._skin_loaded:
            return False
        skin_key = self._pending_skin_key
        if skin_key is None:
            return False
        self.set_skin(skin_key)
        return True

    def set_skin(self, skin_key):
        self._disconnect_foreground_frame_sync()
        spec = self.assets.get_skin_spec(skin_key)
        self.skin_spec = spec
        self.setMinimumSize(*spec.minimum_window_size)
        self.content_surface.setProperty("surfaceRole", spec.surface_role)
        self.content_surface.style().unpolish(self.content_surface)
        self.content_surface.style().polish(self.content_surface)
        if spec.occlusion_rects:
            self.occlusion_surface.setProperty("occlusionRole", spec.occlusion_role)
            self.occlusion_surface.style().unpolish(self.occlusion_surface)
            self.occlusion_surface.style().polish(self.occlusion_surface)
            self.occlusion_surface.show()
        else:
            self.occlusion_surface.clearMask()
            self.occlusion_surface.hide()

        background_spec = self.assets.get_asset_spec(spec.background_asset_key)
        if background_spec.animated:
            self.background_layer.set_movie(
                self.assets.create_movie(spec.background_asset_key, parent=self),
                frame_offsets=background_spec.frame_offsets,
            )
        else:
            self.background_layer.set_pixmap(self.assets.load_pixmap(spec.background_asset_key))

        self._prepare_occlusion_mask()

        if spec.foreground_asset_key:
            foreground_spec = self.assets.get_asset_spec(spec.foreground_asset_key)
            if foreground_spec.animated:
                self.foreground_layer.set_movie(
                    self.assets.create_movie(spec.foreground_asset_key, parent=self),
                    frame_offsets=foreground_spec.frame_offsets,
                )
            else:
                self.foreground_layer.set_pixmap(self.assets.load_pixmap(spec.foreground_asset_key))
            self.foreground_layer.show()
        else:
            self.foreground_layer.clear()
            self.foreground_layer.hide()

        self._connect_foreground_frame_sync()

        self._pending_skin_key = None
        self._skin_loaded = True
        self._update_layer_geometry()
        self.set_animation_active(self.isVisible())

    def set_content_widget(self, widget):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            old_widget = item.widget()
            if old_widget is not None:
                old_widget.setParent(None)
        if widget is not None:
            self.content_layout.addWidget(widget)

    def set_content_margins(self, left, top, right, bottom):
        self.content_layout.setContentsMargins(
            int(left),
            int(top),
            int(right),
            int(bottom),
        )

    def set_animation_active(self, active):
        self._animation_active = bool(active)
        if not self._skin_loaded:
            return
        layers = [self.background_layer]
        if not self.skin_spec.foreground_frame_map:
            layers.append(self.foreground_layer)
        for layer in layers:
            movie = layer.movie
            if movie is None:
                continue
            if self._animation_active:
                if movie.state() == QMovie.MovieState.NotRunning:
                    movie.start()
                else:
                    movie.setPaused(False)
            elif movie.state() == QMovie.MovieState.Running:
                movie.setPaused(True)
        if self.skin_spec.foreground_frame_map:
            self._sync_foreground_frame(self.background_layer.movie.currentFrameNumber())

    def scene_geometry(self):
        return self.scene_viewport.geometry()

    def content_geometry(self):
        return self.content_surface.geometry()

    def foreground_geometry(self):
        return self.foreground_layer.geometry()

    def occlusion_geometry(self):
        return self.occlusion_surface.geometry()

    def resizeEvent(self, event):
        self._update_layer_geometry()
        super().resizeEvent(event)

    def showEvent(self, event):
        self._update_layer_geometry()
        self.set_animation_active(True)
        super().showEvent(event)

    def hideEvent(self, event):
        self.set_animation_active(False)
        super().hideEvent(event)

    def _update_layer_geometry(self):
        if self.skin_spec is None or self.width() <= 0 or self.height() <= 0:
            return
        frame_size = (self.width(), self.height())
        background = self.assets.get_asset_spec(self.skin_spec.background_asset_key)
        scene_rect, content_rect = compute_skinned_scene_layout(
            frame_size,
            self.skin_spec,
            self.assets.asset_specs,
        )
        self.scene_viewport.setGeometry(QRect(*scene_rect.rounded()))
        scene_bounds = self.scene_viewport.rect()
        self.background_layer.setGeometry(scene_bounds)

        viewport_rect = compute_scene_rect(
            (scene_bounds.width(), scene_bounds.height()),
            background.source_size,
            self.skin_spec.fit_mode,
        )
        self.content_surface.setGeometry(QRect(*content_rect.rounded()))

        if self.skin_spec.occlusion_rects:
            self._update_occlusion_geometry(viewport_rect, scene_bounds)

        if self.skin_spec.foreground_rect is not None:
            foreground_rect = project_normalized_rect(self.skin_spec.foreground_rect, viewport_rect)
            self.foreground_layer.setGeometry(QRect(*foreground_rect.rounded()))

        self.background_layer.lower()
        self.occlusion_surface.raise_()
        self.content_surface.raise_()
        self.foreground_layer.raise_()

    def _connect_foreground_frame_sync(self):
        if not self.skin_spec.foreground_frame_map:
            return
        background_movie = self.background_layer.movie
        foreground_movie = self.foreground_layer.movie
        if background_movie is None or foreground_movie is None:
            return
        background_movie.frameChanged.connect(self._sync_foreground_frame)
        self._frame_sync_movie = background_movie
        self._sync_foreground_frame(background_movie.currentFrameNumber())

    def _disconnect_foreground_frame_sync(self):
        if self._frame_sync_movie is None:
            return
        try:
            self._frame_sync_movie.frameChanged.disconnect(self._sync_foreground_frame)
        except (TypeError, RuntimeError):
            pass
        self._frame_sync_movie = None

    def _sync_foreground_frame(self, background_frame_number):
        frame_map = self.skin_spec.foreground_frame_map
        movie = self.foreground_layer.movie
        if not frame_map or movie is None or background_frame_number < 0:
            return
        mapped_frame = frame_map[background_frame_number % len(frame_map)]
        if movie.currentFrameNumber() != mapped_frame:
            movie.jumpToFrame(mapped_frame)

    def _prepare_occlusion_mask(self):
        self._occlusion_source_bitmap = None
        if (
            not self.skin_spec.occlusion_rects
            or self.skin_spec.occlusion_mask_mode != OCCLUSION_DARK_PIXELS
        ):
            return
        pixmap = self.background_layer.current_pixmap()
        if pixmap is None or pixmap.isNull():
            return
        self._occlusion_source_bitmap = self._build_dark_pixel_bitmap(
            pixmap,
            self.skin_spec.occlusion_rects,
        )

    def _update_occlusion_geometry(self, viewport_rect, scene_bounds):
        self.occlusion_surface.setGeometry(scene_bounds)
        if self._occlusion_source_bitmap is not None:
            scaled_bitmap = QBitmap.fromPixmap(
                self._occlusion_source_bitmap.scaled(
                    scene_bounds.size(),
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.FastTransformation,
                )
            )
            self.occlusion_surface.setMask(scaled_bitmap)
            return

        region = QRegion()
        for rect in self.skin_spec.occlusion_rects:
            projected = project_normalized_rect(rect, viewport_rect)
            region = region.united(QRegion(QRect(*projected.rounded())))
        self.occlusion_surface.setMask(region)

    @staticmethod
    def _build_dark_pixel_bitmap(pixmap, sample_rects, threshold=242, padding=3):
        image = pixmap.toImage().convertToFormat(QImage.Format.Format_RGB888)
        width = image.width()
        height = image.height()
        bitmap = QBitmap(width, height)
        bitmap.clear()
        if width <= 0 or height <= 0:
            return bitmap

        bits = image.bits()
        pixel_bytes = bits.asstring(image.sizeInBytes())
        bytes_per_line = image.bytesPerLine()
        source_bounds = GeometryRect(0.0, 0.0, float(width), float(height))
        runs = []
        for sample_rect in sample_rects:
            projected = project_normalized_rect(sample_rect, source_bounds)
            left, top, rect_width, rect_height = projected.rounded()
            right = min(width, left + rect_width)
            bottom = min(height, top + rect_height)
            left = max(0, left)
            top = max(0, top)
            for y in range(top, bottom):
                run_start = None
                row_offset = y * bytes_per_line
                for x in range(left, right):
                    pixel_offset = row_offset + x * 3
                    red = pixel_bytes[pixel_offset]
                    green = pixel_bytes[pixel_offset + 1]
                    blue = pixel_bytes[pixel_offset + 2]
                    is_dark = red + green + blue < threshold * 3
                    if is_dark and run_start is None:
                        run_start = x
                    elif not is_dark and run_start is not None:
                        runs.append((run_start, x, y))
                        run_start = None
                if run_start is not None:
                    runs.append((run_start, right, y))

        painter = QPainter(bitmap)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(Qt.GlobalColor.color1)
        for start_x, end_x, y in runs:
            run_left = max(0, start_x - padding)
            run_top = max(0, y - padding)
            run_right = min(width, end_x + padding)
            run_bottom = min(height, y + padding + 1)
            painter.drawRect(
                QRect(
                    run_left,
                    run_top,
                    run_right - run_left,
                    run_bottom - run_top,
                )
            )
        painter.end()
        return bitmap
