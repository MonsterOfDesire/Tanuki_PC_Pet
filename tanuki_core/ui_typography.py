"""Shared, image-independent interface text sizing."""

import re


UI_TEXT_SIZE_OPTIONS = ("small", "medium", "large")
UI_TEXT_SIZE_FACTORS = {"small": 0.8, "medium": 1.0, "large": 1.5}
_current_text_size = "medium"


def normalize_ui_text_size(value):
    return value if value in UI_TEXT_SIZE_OPTIONS else "medium"


def get_ui_text_size():
    return _current_text_size


def ui_text_scale():
    return UI_TEXT_SIZE_FACTORS[_current_text_size]


def ui_font_pixels(base_pixels):
    return max(1, round(float(base_pixels) * ui_text_scale()))


def scale_ui_font_styles(stylesheet):
    return re.sub(
        r"(font-size\s*:\s*)(\d+(?:\.\d+)?)(px|pt)",
        lambda match: (
            f"{match[1]}{float(match[2]) * ui_text_scale():g}{match[3]}"
        ),
        stylesheet,
    )


def set_ui_text_size(value):
    """Refresh existing themed surfaces; newly opened ones use the same size."""
    global _current_text_size
    value = normalize_ui_text_size(value)
    changed = value != _current_text_size
    _current_text_size = value

    from PyQt6.QtGui import QFont
    from PyQt6.QtWidgets import QApplication, QToolTip
    from .ui_theme import build_ui_stylesheet

    app = QApplication.instance()
    if app is None:
        return changed
    if not changed and getattr(app, "_tanuki_applied_text_size", None) == value:
        return False
    if not hasattr(app, "_tanuki_base_ui_font"):
        app._tanuki_base_ui_font = QFont(app.font())
    font = QFont(app._tanuki_base_ui_font)
    if font.pixelSize() > 0:
        font.setPixelSize(ui_font_pixels(font.pixelSize()))
    else:
        font.setPointSizeF(font.pointSizeF() * ui_text_scale())
    app.setFont(font)
    QToolTip.setFont(font)
    app._tanuki_applied_text_size = value
    widgets = QApplication.allWidgets()
    for widget in widgets:
        tokens = getattr(widget, "_tanuki_ui_theme", None)
        if tokens is not None:
            widget.setStyleSheet(build_ui_stylesheet(tokens))
    for widget in widgets:
        refresh = getattr(widget, "refresh_ui_text_size", None)
        if callable(refresh):
            refresh()
        widget.updateGeometry()
        widget.update()
    return True
