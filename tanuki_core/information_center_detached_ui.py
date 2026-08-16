from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from .ui_theme import DEFAULT_UI_THEME, build_ui_stylesheet
from .window_chrome import SkinnedToolWindowChrome


class DetachedInformationPageWindow(QWidget):
    dock_requested = pyqtSignal(str)

    def __init__(
        self,
        page_spec,
        page,
        page_icon,
        *,
        initial_size=None,
        theme=DEFAULT_UI_THEME,
    ):
        super().__init__(None, Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setObjectName("tanukiDetachedInformationPage")
        self.setWindowTitle(
            f"狸貓資訊中心 — {page_spec.navigation_label}"
        )
        self.page_spec = page_spec
        self.page = page
        self.theme = theme

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.header = QFrame()
        self.header.setObjectName("tanukiInformationNavigation")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(
            theme.spacing_lg,
            theme.spacing_sm,
            theme.spacing_lg,
            theme.spacing_sm,
        )
        header_layout.setSpacing(theme.spacing_sm)

        self.icon_label = QLabel()
        self.icon_label.setPixmap(page_icon.pixmap(18, 18))
        header_layout.addWidget(self.icon_label)

        self.title_label = QLabel(
            f"{page_spec.navigation_label}（分離視窗）"
        )
        self.title_label.setProperty("tanukiRole", "navigationTitle")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch(1)

        self.window_chrome = SkinnedToolWindowChrome(
            self,
            drag_widgets=(self.header, self.title_label),
            controls_variant="dark",
        )
        self.window_chrome.controls.close_button.setToolTip(
            "關閉並歸回資訊中心"
        )
        self.window_chrome.controls.close_button.setAccessibleName(
            "關閉並歸回資訊中心"
        )
        header_layout.addWidget(self.window_chrome.controls)
        root_layout.addWidget(self.header)

        self.page_host = QWidget()
        self.page_layout = QVBoxLayout(self.page_host)
        self.page_layout.setContentsMargins(0, 0, 0, 0)
        self.page_layout.setSpacing(0)
        self.page_layout.addWidget(page)
        root_layout.addWidget(self.page_host, stretch=1)

        page_minimum_width, page_minimum_height = (
            page.skin_spec.minimum_window_size
        )
        header_height = theme.navigation_height + theme.spacing_sm * 2
        self.setMinimumSize(
            page_minimum_width,
            page_minimum_height + header_height,
        )
        if initial_size is not None:
            self.resize(QSize(initial_size))
        self.setStyleSheet(build_ui_stylesheet(theme))
        self.window_chrome.refresh_geometry()

    def release_page(self):
        page = self.page
        if page is None:
            return None
        page.set_animation_active(False)
        self.page_layout.removeWidget(page)
        self.page = None
        return page

    def show_page(self):
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
        self.raise_()
        self.activateWindow()
        if self.page is not None:
            self.page.set_animation_active(True)

    def resizeEvent(self, event):
        self.window_chrome.refresh_geometry()
        super().resizeEvent(event)

    def showEvent(self, event):
        if self.page is not None:
            self.page.set_animation_active(True)
        super().showEvent(event)

    def hideEvent(self, event):
        if self.page is not None:
            self.page.set_animation_active(False)
        super().hideEvent(event)

    def closeEvent(self, event):
        if self.page is not None:
            self.dock_requested.emit(self.page_spec.page_id)
        event.accept()
