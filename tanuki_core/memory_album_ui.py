from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QButtonGroup,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .memory_album import MEMORY_ALBUM_CAPACITIES, MEMORY_ALBUM_MODES
from .ui_localization import translate_ui


class MemoryAlbumPanel(QWidget):
    def __init__(self, binding=None, parent=None):
        super().__init__(parent)
        self.binding = binding
        self.snapshot = None
        self._cards = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        controls = QHBoxLayout()
        controls.setSpacing(6)
        self.mode_label = QLabel()
        controls.addWidget(self.mode_label)
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.mode_buttons = {}
        for mode in MEMORY_ALBUM_MODES:
            button = QPushButton()
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, value=mode: self.set_mode(value))
            self.mode_group.addButton(button)
            self.mode_buttons[mode] = button
            controls.addWidget(button)
        controls.addSpacing(12)
        self.capacity_label = QLabel()
        controls.addWidget(self.capacity_label)
        self.capacity_group = QButtonGroup(self)
        self.capacity_group.setExclusive(True)
        self.capacity_buttons = {}
        for capacity in MEMORY_ALBUM_CAPACITIES:
            button = QPushButton(str(capacity))
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, value=capacity: self.set_capacity(value))
            self.capacity_group.addButton(button)
            self.capacity_buttons[capacity] = button
            controls.addWidget(button)
        controls.addStretch(1)
        self.open_folder_button = QPushButton()
        self.open_folder_button.clicked.connect(self.open_folder)
        controls.addWidget(self.open_folder_button)
        layout.addLayout(controls)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setProperty("tanukiRole", "pagePlaceholder")
        layout.addWidget(self.status_label)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.gallery = QWidget()
        self.grid = QGridLayout(self.gallery)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(10)
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
        self.mode_buttons.get(snapshot.mode, self.mode_buttons["off"]).setChecked(True)
        self.capacity_buttons.get(snapshot.capacity, self.capacity_buttons[20]).setChecked(True)
        if snapshot.full:
            text = translate_ui(
                "memory_album.status.full",
                default="相簿已滿（{count}/{capacity}）；將不再拍攝新照片，既有照片不會自動刪除。",
                count=snapshot.count,
                capacity=snapshot.capacity,
            )
        elif snapshot.near_full:
            text = translate_ui(
                "memory_album.status.near_full",
                default="相簿即將滿載（{count}/{capacity}）；抵達上限後將停止拍攝。",
                count=snapshot.count,
                capacity=snapshot.capacity,
            )
        else:
            text = translate_ui(
                "memory_album.status.normal",
                default="已保存 {count}/{capacity} 張；系統不會自動刪除照片。",
                count=snapshot.count,
                capacity=snapshot.capacity,
            )
        self.status_label.setText(text)
        self._rebuild_gallery()
        return True

    def _rebuild_gallery(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._cards = []
        entries = tuple(getattr(self.snapshot, "entries", ()) or ())
        columns = max(2, min(5, max(1, self.width()) // 220))
        for index, entry in enumerate(entries):
            card = QToolButton()
            card.setMinimumSize(180, 150)
            card.setProperty("tanukiRole", "achievementCard")
            card.setToolButtonStyle(
                Qt.ToolButtonStyle.ToolButtonTextUnderIcon
            )
            pixmap = QPixmap(str(entry.path))
            if not pixmap.isNull():
                card.setIcon(QIcon(pixmap))
                card.setIconSize(QSize(168, 112))
            card.setText(str(entry.captured_at).replace("T", " ")[:19])
            card.setToolTip(
                translate_ui(
                    "memory_album.open_photo",
                    default="開啟這張照片",
                )
            )
            card.clicked.connect(
                lambda checked=False, path=entry.path: QDesktopServices.openUrl(
                    QUrl.fromLocalFile(str(path))
                )
            )
            self.grid.addWidget(card, index // columns, index % columns)
            self._cards.append(card)
        self.grid.setRowStretch((len(entries) + columns - 1) // columns, 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.snapshot is not None:
            self._rebuild_gallery()

    def retranslate_ui(self):
        self.mode_label.setText(translate_ui("memory_album.mode.label", default="拍照模式"))
        for mode, default in {
            "off": "不開啟",
            "events": "互動事件",
            "random": "隨機拍照",
        }.items():
            self.mode_buttons[mode].setText(
                translate_ui(f"memory_album.mode.{mode}", default=default)
            )
        self.capacity_label.setText(
            translate_ui("memory_album.capacity", default="照片上限")
        )
        self.open_folder_button.setText(
            translate_ui("memory_album.open_folder", default="開啟照片資料夾")
        )
        if self.snapshot is not None:
            self.refresh_from_binding()
