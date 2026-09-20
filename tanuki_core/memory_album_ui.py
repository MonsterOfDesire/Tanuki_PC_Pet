from __future__ import annotations

from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QUrl,
    pyqtProperty,
)
from PyQt6.QtGui import (
    QColor,
    QDesktopServices,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QImageReader,
)
from PyQt6.QtWidgets import (
    QAbstractButton,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .ui_icons import create_ui_icon
from .ui_localization import translate_ui


PIN_COLORS = (
    "#d94f4f",
    "#3d82cf",
    "#56a64b",
    "#d39a32",
    "#8a5bc2",
)
DEFAULT_PHOTO_ASPECT_RATIO = 16.0 / 9.0
MIN_PHOTO_ASPECT_RATIO = 0.72
MAX_PHOTO_ASPECT_RATIO = 2.20
THUMBNAIL_MAX_EDGE_PX = 512


def load_memory_thumbnail(path, max_edge=THUMBNAIL_MAX_EDGE_PX):
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    source_size = reader.size()
    if source_size.isValid() and max(source_size.width(), source_size.height()) > max_edge:
        reader.setScaledSize(
            source_size.scaled(
                QSize(max_edge, max_edge),
                Qt.AspectRatioMode.KeepAspectRatio,
            )
        )
    image = reader.read()
    return QPixmap.fromImage(image), source_size


class MemoryPhotoCard(QAbstractButton):
    """A polaroid-style photo that lifts without moving the grid layout."""

    def __init__(self, entry, index=0, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.pin_color = QColor(PIN_COLORS[index % len(PIN_COLORS)])
        self._pixmap, self._source_size = load_memory_thumbnail(entry.path)
        self.photo_aspect_ratio = self._source_aspect_ratio()
        self._hover_progress = 0.0
        self._hover_animation = QPropertyAnimation(
            self,
            b"hoverProgress",
            self,
        )
        self._hover_animation.setDuration(140)
        self._hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        size_policy = QSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        size_policy.setHeightForWidth(True)
        self.setSizePolicy(size_policy)
        self.setMinimumWidth(190)
        self.setMinimumHeight(self.heightForWidth(190))
        self.setToolTip(
            translate_ui(
                "memory_album.open_photo",
                default="開啟這張照片",
            )
        )
        self.setAccessibleName(self.toolTip())
        self.clicked.connect(self.open_photo)

    def sizeHint(self):
        width = 224
        return QSize(width, self.heightForWidth(width))

    def minimumSizeHint(self):
        width = 190
        return QSize(width, self.heightForWidth(width))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        # Follow the source photograph instead of forcing every memory into a
        # 16:9 slot. Extreme panoramas/portraits keep a bounded card and are
        # still drawn with contain scaling, so no character is cropped.
        photo_width = max(1.0, float(width) - 44.0)
        return max(
            156,
            int(round(photo_width / self.photo_aspect_ratio + 68.0)),
        )

    def _source_aspect_ratio(self):
        if self._source_size.isValid() and self._source_size.height() > 0:
            source_ratio = self._source_size.width() / float(
                self._source_size.height()
            )
            return max(
                MIN_PHOTO_ASPECT_RATIO,
                min(MAX_PHOTO_ASPECT_RATIO, source_ratio),
            )
        if self._pixmap.isNull() or self._pixmap.height() <= 0:
            return DEFAULT_PHOTO_ASPECT_RATIO
        source_ratio = self._pixmap.width() / float(self._pixmap.height())
        return max(
            MIN_PHOTO_ASPECT_RATIO,
            min(MAX_PHOTO_ASPECT_RATIO, source_ratio),
        )

    def get_hover_progress(self):
        return self._hover_progress

    def set_hover_progress(self, value):
        self._hover_progress = max(0.0, min(1.0, float(value)))
        self.update()

    hoverProgress = pyqtProperty(
        float,
        fget=get_hover_progress,
        fset=set_hover_progress,
    )

    def enterEvent(self, event):
        self._animate_hover(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animate_hover(0.0)
        super().leaveEvent(event)

    def focusInEvent(self, event):
        self._animate_hover(1.0)
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self._animate_hover(0.0)
        super().focusOutEvent(event)

    def _animate_hover(self, target):
        self._hover_animation.stop()
        self._hover_animation.setStartValue(self._hover_progress)
        self._hover_animation.setEndValue(float(target))
        self._hover_animation.start()

    def open_photo(self):
        return QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(self.entry.path))
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(
            QPainter.RenderHint.SmoothPixmapTransform,
            True,
        )
        progress = self._hover_progress
        margin_x = 13.0 - 5.0 * progress
        top = 15.0 - 7.0 * progress
        bottom = 13.0 - 3.0 * progress
        card_rect = QRectF(
            margin_x,
            top,
            self.width() - margin_x * 2.0,
            self.height() - top - bottom,
        )

        shadow_rect = card_rect.translated(0.0, 4.0 + 3.0 * progress)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(35, 27, 20, int(55 + 55 * progress)))
        painter.drawRoundedRect(shadow_rect, 6.0, 6.0)

        painter.setBrush(QColor("#fffdf8"))
        painter.setPen(QPen(QColor(132, 111, 81, 95), 1.0))
        painter.drawRoundedRect(card_rect, 5.0, 5.0)

        photo_width = max(1.0, card_rect.width() - 18.0)
        photo_height = min(
            photo_width / self.photo_aspect_ratio,
            max(1.0, card_rect.height() - 40.0),
        )
        photo_rect = QRectF(
            card_rect.left() + 9.0,
            card_rect.top() + 9.0,
            photo_width,
            photo_height,
        )
        painter.setBrush(QColor("#282725"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(photo_rect, 2.5, 2.5)
        if not self._pixmap.isNull():
            painter.save()
            clip = QPainterPath()
            clip.addRoundedRect(photo_rect, 2.5, 2.5)
            painter.setClipPath(clip)
            painter.drawPixmap(
                self._contain_target_rect(photo_rect),
                self._pixmap,
                QRectF(self._pixmap.rect()),
            )
            painter.restore()
        else:
            painter.setBrush(QColor("#ded6c8"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(photo_rect, 2.5, 2.5)

        painter.setPen(QColor("#52483f"))
        font = painter.font()
        font.setPointSizeF(max(8.0, font.pointSizeF() - 1.0))
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(
            card_rect.adjusted(8.0, card_rect.height() - 27.0, -8.0, -4.0),
            Qt.AlignmentFlag.AlignCenter,
            self._display_timestamp(),
        )

        pin_center_x = card_rect.left() + 20.0
        pin_center_y = card_rect.top() + 9.0
        needle_pen = QPen(QColor(70, 50, 38, 165), 4.2)
        needle_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(needle_pen)
        painter.drawLine(
            int(pin_center_x + 2.0),
            int(pin_center_y + 5.0),
            int(pin_center_x + 9.0),
            int(pin_center_y + 20.0),
        )
        needle_highlight = QPen(QColor(255, 246, 225, 125), 1.1)
        needle_highlight.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(needle_highlight)
        painter.drawLine(
            int(pin_center_x + 2.8),
            int(pin_center_y + 5.5),
            int(pin_center_x + 8.7),
            int(pin_center_y + 18.4),
        )
        painter.setPen(QPen(self.pin_color.darker(150), 1.2))
        painter.setBrush(self.pin_color)
        painter.drawEllipse(
            QRectF(pin_center_x - 9.5, pin_center_y - 9.5, 19.0, 19.0)
        )
        highlight = QColor("#ffffff")
        highlight.setAlpha(150)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(highlight)
        painter.drawEllipse(
            QRectF(pin_center_x - 5.3, pin_center_y - 5.6, 5.2, 5.2)
        )

        if self.hasFocus():
            painter.setPen(QPen(QColor("#d9a928"), 2.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(
                card_rect.adjusted(1, 1, -1, -1),
                5.0,
                5.0,
            )

    def _contain_target_rect(self, target_rect):
        source = QRectF(self._pixmap.rect())
        if source.width() <= 0 or source.height() <= 0:
            return QRectF(target_rect)
        target_ratio = target_rect.width() / max(1.0, target_rect.height())
        source_ratio = source.width() / source.height()
        if source_ratio > target_ratio:
            height = target_rect.width() / source_ratio
            return QRectF(
                target_rect.left(),
                target_rect.center().y() - height / 2.0,
                target_rect.width(),
                height,
            )
        else:
            width = target_rect.height() * source_ratio
            return QRectF(
                target_rect.center().x() - width / 2.0,
                target_rect.top(),
                width,
                target_rect.height(),
            )

    def _display_timestamp(self):
        value = str(getattr(self.entry, "captured_at", "") or "")
        if len(value) >= 16 and value[4:5] == "-" and value[10:11] == "T":
            return f"{value[5:10].replace('-', '/')}  {value[11:16]}"
        return value.replace("T", " ")[:16]


class MemoryAlbumPanel(QWidget):
    def __init__(self, binding=None, parent=None):
        super().__init__(parent)
        self.binding = binding
        self.snapshot = None
        self._cards = []
        self._column_count = 0
        self._empty_label = None
        self.setObjectName("tanukiMemoryAlbum")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 14, 22, 18)
        layout.setSpacing(7)

        # Keep the book spine visually clear: status and folder are two small
        # paper tabs anchored to opposite pages, not one translucent toolbar
        # stretched across the whole spread.
        self.header = QWidget()
        self.header.setProperty("tanukiRole", "memoryHeader")
        controls = QHBoxLayout(self.header)
        controls.setContentsMargins(8, 3, 8, 3)
        controls.setSpacing(8)
        self.status_label = QLabel()
        self.status_label.setWordWrap(False)
        self.status_label.setProperty("tanukiRole", "memoryStatus")
        self.status_label.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Fixed,
        )
        controls.addWidget(self.status_label)
        controls.addStretch(1)
        self.open_folder_button = QPushButton()
        self.open_folder_button.setProperty("tanukiRole", "memoryFolder")
        self.open_folder_button.setIcon(
            create_ui_icon("folder", color="#3f4d37", size=18)
        )
        self.open_folder_button.setIconSize(QSize(18, 18))
        self.open_folder_button.clicked.connect(self.open_folder)
        controls.addWidget(self.open_folder_button)
        layout.addWidget(self.header)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("tanukiMemoryAlbumScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.gallery = QWidget()
        self.gallery.setObjectName("tanukiMemoryAlbumGallery")
        self.grid = QGridLayout(self.gallery)
        self.grid.setContentsMargins(10, 4, 10, 8)
        self.grid.setHorizontalSpacing(8)
        self.grid.setVerticalSpacing(4)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.gallery)
        layout.addWidget(self.scroll, stretch=1)
        self.retranslate_ui()

    def set_binding(self, binding):
        self.binding = binding
        self.refresh_from_binding()

    def set_mode(self, mode):
        if self.binding is not None and self.binding.set_mode(mode):
            self.refresh_from_binding()

    def set_capacity(self, capacity):
        if self.binding is not None and self.binding.set_capacity(capacity):
            self.refresh_from_binding()

    def open_folder(self):
        if self.binding is not None:
            self.binding.open_folder()

    def refresh_from_binding(self):
        snapshot = self.binding.snapshot() if self.binding is not None else None
        if snapshot is None:
            return False
        self.snapshot = snapshot
        if snapshot.full:
            state = "full"
            text = translate_ui(
                "memory_album.status.compact_full",
                default="相簿已滿 {count}/{capacity}",
                count=snapshot.count,
                capacity=snapshot.capacity,
            )
            detail = translate_ui(
                "memory_album.status.full",
                default="相簿已滿（{count}/{capacity}）；將不再拍攝新照片，既有照片不會自動刪除。",
                count=snapshot.count,
                capacity=snapshot.capacity,
            )
        elif snapshot.near_full:
            state = "near_full"
            text = translate_ui(
                "memory_album.status.compact_near_full",
                default="即將滿載 {count}/{capacity}",
                count=snapshot.count,
                capacity=snapshot.capacity,
            )
            detail = translate_ui(
                "memory_album.status.near_full",
                default="相簿即將滿載（{count}/{capacity}）；抵達上限後將停止拍攝。",
                count=snapshot.count,
                capacity=snapshot.capacity,
            )
        else:
            state = "normal"
            text = translate_ui(
                "memory_album.status.compact_normal",
                default="已保存 {count}/{capacity} 張",
                count=snapshot.count,
                capacity=snapshot.capacity,
            )
            detail = translate_ui(
                "memory_album.status.normal",
                default="已保存 {count}/{capacity} 張；系統不會自動刪除照片。",
                count=snapshot.count,
                capacity=snapshot.capacity,
            )
        self.status_label.setText(text)
        self.status_label.setToolTip(detail)
        self.status_label.setProperty("albumState", state)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        self._rebuild_gallery()
        return True

    def _rebuild_gallery(self):
        self._clear_gallery()
        entries = tuple(getattr(self.snapshot, "entries", ()) or ())
        if not entries:
            empty_label = QLabel(
                translate_ui(
                    "memory_album.empty",
                    default="還沒有照片。互動留下的回憶會出現在這裡。",
                )
            )
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setProperty("tanukiRole", "memoryEmpty")
            self.grid.addWidget(empty_label, 0, 0, 1, 2)
            self._empty_label = empty_label
            self._column_count = 2
            return
        self._cards = [
            MemoryPhotoCard(entry, index=index, parent=self.gallery)
            for index, entry in enumerate(entries)
        ]
        self._relayout_cards(force=True)

    def _clear_gallery(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._cards = []
        self._column_count = 0
        self._empty_label = None

    def _relayout_cards(self, force=False):
        if not self._cards:
            return
        columns = self.column_count_for_width(self.width())
        if not force and columns == self._column_count:
            return
        for card in self._cards:
            self.grid.removeWidget(card)
        for index, card in enumerate(self._cards):
            self.grid.addWidget(
                card,
                index // columns,
                index % columns,
                alignment=Qt.AlignmentFlag.AlignTop,
            )
        self._column_count = columns

    @staticmethod
    def column_count_for_width(width):
        return 4 if int(width) >= 960 else 2

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout_cards()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        outer = QRectF(self.rect()).adjusted(3.0, 3.0, -3.0, -3.0)
        painter.setPen(QPen(QColor("#263e33"), 2.0))
        painter.setBrush(QColor(49, 80, 62, 238))
        painter.drawRoundedRect(outer, 17.0, 17.0)

        page = outer.adjusted(10.0, 9.0, -10.0, -9.0)
        center = page.center().x()
        left_page = QRectF(
            page.left(),
            page.top(),
            page.width() / 2.0 - 5.0,
            page.height(),
        )
        right_page = QRectF(
            center + 5.0,
            page.top(),
            page.width() / 2.0 - 5.0,
            page.height(),
        )
        page_gradient = QLinearGradient(0.0, page.top(), 0.0, page.bottom())
        page_gradient.setColorAt(0.0, QColor("#fffdf4"))
        page_gradient.setColorAt(1.0, QColor("#f2e7cf"))
        painter.setBrush(page_gradient)
        painter.setPen(QPen(QColor(150, 124, 82, 110), 1.0))
        painter.drawRoundedRect(left_page, 12.0, 12.0)
        painter.drawRoundedRect(right_page, 12.0, 12.0)

        spine = QRectF(
            center - 5.0,
            page.top() + 3.0,
            10.0,
            page.height() - 6.0,
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(88, 64, 39, 80))
        painter.drawRoundedRect(spine, 5.0, 5.0)
        painter.setBrush(QColor("#b68a42"))
        painter.setPen(QPen(QColor("#6d4c21"), 1.0))
        for ratio in (0.19, 0.37, 0.55, 0.73):
            ring_y = page.top() + page.height() * ratio
            painter.drawEllipse(
                QRectF(center - 9.0, ring_y - 3.0, 18.0, 6.0)
            )

        super().paintEvent(event)

    def retranslate_ui(self):
        self.open_folder_button.setText(
            translate_ui(
                "memory_album.folder_short",
                default="照片資料夾",
            )
        )
        self.open_folder_button.setToolTip(
            translate_ui(
                "memory_album.open_folder",
                default="開啟照片資料夾",
            )
        )
        if self.snapshot is not None:
            self.refresh_from_binding()
