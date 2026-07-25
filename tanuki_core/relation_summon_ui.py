from PyQt6.QtCore import QEvent, QPointF, QRectF, QSize, QSignalBlocker, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .ui_theme import DEFAULT_UI_THEME
from .ui_icons import METRIC_COLORS, create_metric_icon
from .ui_localization import character_display_name
from .ui_controls import ToggleSwitch


def crop_avatar_first_frame(assets, avatar_spec):
    return assets.load_avatar_pixmap(avatar_spec)


def create_relation_arrow_pixmap(width=18, height=14):
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor(80, 68, 59, 190), 2.0)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    center_y = height / 2.0
    painter.drawLine(QPointF(2.0, center_y), QPointF(width - 3.0, center_y))
    painter.drawLine(QPointF(width - 7.0, center_y - 4.0), QPointF(width - 3.0, center_y))
    painter.drawLine(QPointF(width - 7.0, center_y + 4.0), QPointF(width - 3.0, center_y))
    painter.end()
    return pixmap


def create_relation_stat_icon(stat_kind, size=13):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    scale = size / 16.0
    if stat_kind == "affinity":
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#d9782d"))
        painter.drawPolygon(
            QPolygonF(
                QPointF(x * scale, y * scale)
                for x, y in (
                    (8, 1),
                    (10, 6),
                    (15, 6),
                    (11, 9),
                    (13, 15),
                    (8, 12),
                    (3, 15),
                    (5, 9),
                    (1, 6),
                    (6, 6),
                )
            )
        )
    else:
        pen = QPen(QColor("#75685f"), max(1.0, 1.5 * scale))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QRectF(2 * scale, 2 * scale, 12 * scale, 12 * scale))
        painter.drawLine(QPointF(8 * scale, 4 * scale), QPointF(8 * scale, 8 * scale))
        painter.drawLine(QPointF(8 * scale, 8 * scale), QPointF(11 * scale, 10 * scale))
    painter.end()
    return QIcon(pixmap)


class RelationMetricBar(QWidget):
    def __init__(self, metric_kind, value, parent=None):
        super().__init__(parent)
        self.metric_kind = metric_kind
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        icon_label = QLabel()
        icon_label.setPixmap(create_metric_icon(metric_kind, size=18).pixmap(18, 18))
        icon_label.setToolTip(self.metric_label(metric_kind))
        layout.addWidget(icon_label)
        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(max(0, min(100, int(round(value)))))
        progress.setTextVisible(False)
        progress.setProperty("tanukiRole", "relationMetric")
        progress.setProperty("metricKind", metric_kind)
        progress.setToolTip(f"{self.metric_label(metric_kind)} {value:.2f}")
        progress.setFixedWidth(52)
        layout.addWidget(progress)
        value_label = QLabel(f"{value:.0f}")
        value_label.setProperty("tanukiRole", "relationMetricValue")
        value_label.setFixedWidth(18)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(value_label)

    @staticmethod
    def metric_label(metric_kind):
        return {
            "familiarity": "熟悉",
            "trust": "信任",
            "attachment": "依附",
            "tension": "緊張",
        }[metric_kind]


class SummonSwitch(ToggleSwitch):
    def __init__(self, parent=None):
        super().__init__(parent, width=38, height=20)
        self.setProperty("tanukiRole", "relationSummon")


class RelationshipRowCard(QFrame):
    def __init__(self, row, actor_icon, target_icon, parent=None):
        super().__init__(parent)
        self.row = row
        self.setProperty("tanukiRole", "relationRowCard")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 4, 5, 4)
        layout.setSpacing(5)

        pair_column = QVBoxLayout()
        pair_column.setContentsMargins(0, 0, 0, 0)
        pair_column.setSpacing(0)
        pair_layout = QHBoxLayout()
        pair_layout.setContentsMargins(0, 0, 0, 0)
        pair_layout.setSpacing(2)
        actor_label = QLabel()
        actor_label.setPixmap(actor_icon.pixmap(46, 46))
        actor_label.setFixedSize(48, 48)
        actor_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        actor_label.setToolTip(character_display_name(row.actor_name))
        pair_layout.addWidget(actor_label)
        arrow_label = QLabel()
        arrow_label.setPixmap(create_relation_arrow_pixmap())
        pair_layout.addWidget(arrow_label)
        target_label = QLabel()
        target_label.setPixmap(target_icon.pixmap(46, 46))
        target_label.setFixedSize(48, 48)
        target_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        target_label.setToolTip(character_display_name(row.target_name))
        pair_layout.addWidget(target_label)
        pair_column.addLayout(pair_layout)

        pair_stats_layout = QHBoxLayout()
        pair_stats_layout.setContentsMargins(0, 0, 0, 0)
        pair_stats_layout.setSpacing(3)
        pair_stats_layout.addStretch(1)
        affinity_icon_label = QLabel()
        affinity_icon_label.setPixmap(
            create_relation_stat_icon("affinity").pixmap(13, 13)
        )
        affinity_icon_label.setToolTip("好感度")
        pair_stats_layout.addWidget(affinity_icon_label)
        self.affinity_value_label = QLabel(f"{row.affinity:.1f}")
        self.affinity_value_label.setProperty("tanukiRole", "relationAffinityValue")
        self.affinity_value_label.setToolTip(f"好感度 {row.affinity:.2f}")
        pair_stats_layout.addWidget(self.affinity_value_label)
        event_icon_label = QLabel()
        event_icon_label.setPixmap(
            create_relation_stat_icon("events").pixmap(13, 13)
        )
        event_icon_label.setToolTip("事件次數")
        pair_stats_layout.addWidget(event_icon_label)
        self.event_count_label = QLabel(str(row.event_count))
        self.event_count_label.setProperty("tanukiRole", "relationEventCount")
        self.event_count_label.setToolTip(f"事件次數 {row.event_count}")
        pair_stats_layout.addWidget(self.event_count_label)
        pair_stats_layout.addStretch(1)
        pair_column.addLayout(pair_stats_layout)
        layout.addLayout(pair_column)

        metric_grid = QGridLayout()
        metric_grid.setContentsMargins(0, 0, 0, 0)
        metric_grid.setHorizontalSpacing(5)
        metric_grid.setVerticalSpacing(1)
        metric_grid.addWidget(RelationMetricBar("familiarity", row.familiarity), 0, 0)
        metric_grid.addWidget(RelationMetricBar("trust", row.trust), 0, 1)
        metric_grid.addWidget(RelationMetricBar("attachment", row.attachment), 1, 0)
        metric_grid.addWidget(RelationMetricBar("tension", row.tension), 1, 1)
        metric_grid.setColumnStretch(0, 1)
        metric_grid.setColumnStretch(1, 1)
        layout.addLayout(metric_grid, stretch=1)


class RelationSummonPanel(QWidget):
    def __init__(self, assets, binding=None, parent=None, theme=DEFAULT_UI_THEME):
        super().__init__(parent)
        self.assets = assets
        self.binding = None
        self.theme = theme
        self.selected_character_name = ""
        self._applying_presentation = False
        self.avatar_specs = {
            avatar_spec.character_name: avatar_spec
            for avatar_spec in assets.avatar_specs
        }
        self.avatar_icons = {
            character_name: QIcon(crop_avatar_first_frame(assets, avatar_spec))
            for character_name, avatar_spec in self.avatar_specs.items()
        }
        self.avatar_buttons = {}
        self.avatar_button_names = {}
        self.summon_buttons = {}

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(theme.spacing_sm)

        roster_frame = QFrame()
        roster_frame.setProperty("tanukiRole", "relationRoster")
        roster_layout = QVBoxLayout(roster_frame)
        roster_layout.setContentsMargins(
            theme.spacing_xs,
            theme.spacing_xs,
            theme.spacing_xs,
            theme.spacing_xs,
        )
        roster_layout.setSpacing(1)
        self.avatar_group = QButtonGroup(self)
        self.avatar_group.setExclusive(True)
        for avatar_spec in assets.avatar_specs:
            character_name = avatar_spec.character_name
            member_row = QFrame()
            member_row.setProperty("tanukiRole", "relationMemberRow")
            member_layout = QHBoxLayout(member_row)
            member_layout.setContentsMargins(2, 1, 2, 1)
            member_layout.setSpacing(4)

            avatar_button = QToolButton()
            avatar_button.setCheckable(True)
            avatar_button.setIcon(self.avatar_icons[character_name])
            avatar_button.setIconSize(QSize(46, 46))
            avatar_button.setFixedSize(50, 50)
            display_name = character_display_name(character_name)
            avatar_button.setToolTip(f"查看 {display_name} 對其他角色的關係")
            avatar_button.setAccessibleName(display_name)
            avatar_button.setProperty("tanukiRole", "relationRosterAvatar")
            avatar_button.clicked.connect(
                lambda checked=False, name=character_name: self.select_character(name)
            )
            self.avatar_group.addButton(avatar_button)
            self.avatar_buttons[character_name] = avatar_button
            self.avatar_button_names[avatar_button] = character_name
            avatar_button.installEventFilter(self)
            member_layout.addWidget(avatar_button)

            summon_button = SummonSwitch()
            summon_button.setAccessibleName(f"召喚 {display_name}")
            summon_button.toggled.connect(
                lambda summoned, name=character_name: self.set_summoned(name, summoned)
            )
            self.summon_buttons[character_name] = summon_button
            member_layout.addWidget(
                summon_button,
                alignment=Qt.AlignmentFlag.AlignVCenter,
            )
            member_layout.addStretch(1)
            roster_layout.addWidget(member_row)
        roster_layout.addStretch(1)
        root_layout.addWidget(roster_frame)

        relationship_column = QVBoxLayout()
        relationship_column.setContentsMargins(0, 0, 0, 0)
        relationship_column.setSpacing(theme.spacing_xs)
        self.unavailable_label = QLabel("角色資料尚未連接執行中的 Dashboard。")
        self.unavailable_label.setProperty("tanukiRole", "relationNotice")
        self.unavailable_label.setWordWrap(True)
        relationship_column.addWidget(self.unavailable_label)

        legend_row = QHBoxLayout()
        legend_row.setSpacing(theme.spacing_sm)
        self.metric_legend_labels = {}
        for metric_kind in ("familiarity", "trust", "attachment", "tension"):
            legend_item = QWidget()
            legend_layout = QHBoxLayout(legend_item)
            legend_layout.setContentsMargins(0, 0, 0, 0)
            legend_layout.setSpacing(3)
            icon_label = QLabel()
            icon_label.setPixmap(create_metric_icon(metric_kind, size=18).pixmap(18, 18))
            legend_layout.addWidget(icon_label)
            text_label = QLabel(RelationMetricBar.metric_label(metric_kind))
            text_label.setProperty("tanukiRole", "relationLegend")
            legend_layout.addWidget(text_label)
            self.metric_legend_labels[metric_kind] = text_label
            legend_row.addWidget(legend_item)
        legend_row.addStretch(1)
        relationship_column.addLayout(legend_row)

        self.relationship_list = QListWidget()
        self.relationship_list.setProperty("tanukiRole", "relationList")
        self.relationship_list.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        self.relationship_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.relationship_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.relationship_list.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerItem
        )
        self.relationship_list.setSpacing(4)
        self.relationship_list.setFixedHeight(184)
        relationship_column.addWidget(self.relationship_list)
        self.affinity_formula_label = QLabel(
            "好感度＝熟悉×45%＋信任×30%\n"
            f"{'　' * 5}＋依附×35%－緊張×20%"
        )
        self.affinity_formula_label.setProperty("tanukiRole", "relationFormula")
        self.affinity_formula_label.setWordWrap(True)
        relationship_column.addWidget(self.affinity_formula_label)
        relationship_column.addStretch(1)
        root_layout.addLayout(relationship_column, stretch=1)

        self.set_binding(binding)

    def set_binding(self, binding):
        self.binding = binding
        connected = binding is not None
        self.unavailable_label.setVisible(not connected)
        if connected:
            self.refresh_from_binding()
        else:
            self.relationship_list.clear()
            self.relationship_list.addItem("目前尚無角色關係資料。")
            self._set_controls_unavailable()

    def set_summoned(self, character_name, summoned):
        if self._applying_presentation or self.binding is None:
            return
        self.binding.set_summoned(character_name, bool(summoned))
        self.refresh_from_binding()

    def select_character(self, character_name):
        self.selected_character_name = str(character_name or "")
        self.refresh_from_binding()

    def refresh_from_binding(self):
        if self.binding is None:
            return
        presentation = self.binding.presentation(
            selected_character_name=self.selected_character_name,
        )
        self.apply_presentation(presentation)

    def apply_presentation(self, presentation):
        self._applying_presentation = True
        try:
            self.selected_character_name = presentation.selected_character_name
            member_by_name = {
                member.character_name: member
                for member in presentation.members
            }
            for character_name, avatar_button in self.avatar_buttons.items():
                member = member_by_name.get(character_name)
                display_name = character_display_name(character_name)
                avatar_blocker = QSignalBlocker(avatar_button)
                summon_button = self.summon_buttons[character_name]
                summon_blocker = QSignalBlocker(summon_button)
                avatar_button.setEnabled(member is not None)
                avatar_button.setChecked(
                    member is not None
                    and character_name == presentation.selected_character_name
                )
                avatar_button.setToolTip(
                    self._build_avatar_tooltip(character_name, member)
                )
                summon_button.setEnabled(member is not None and member.available)
                summon_button.setChecked(member.summoned if member is not None else False)
                summon_button.setText("")
                summon_button.setToolTip(
                    (
                        "隱藏" if member is not None and member.summoned else "召喚"
                    )
                    + f" {display_name}"
                    if member is not None and member.available
                    else f"{display_name} 尚未載入"
                )
                del summon_blocker
                del avatar_blocker
            self.relationship_list.clear()
            if presentation.relationship_rows:
                for row in presentation.relationship_rows:
                    item = QListWidgetItem()
                    item.setSizeHint(QSize(0, 84))
                    item.setData(
                        Qt.ItemDataRole.UserRole,
                        (row.actor_name, row.target_name),
                    )
                    item.setToolTip(
                        f"{character_display_name(row.actor_name)} → "
                        f"{character_display_name(row.target_name)}｜"
                        f"好感 {row.affinity:.2f}｜事件 {row.event_count}"
                    )
                    self.relationship_list.addItem(item)
                    self.relationship_list.setItemWidget(
                        item,
                        RelationshipRowCard(
                            row,
                            self.avatar_icons.get(row.actor_name, QIcon()),
                            self.avatar_icons.get(row.target_name, QIcon()),
                        ),
                    )
            else:
                self.relationship_list.addItem(
                    presentation.empty_text or "目前沒有可顯示的關係資料。"
                )
        finally:
            self._applying_presentation = False

    def _set_controls_unavailable(self):
        for character_name, avatar_button in self.avatar_buttons.items():
            avatar_button.setEnabled(False)
            summon_button = self.summon_buttons[character_name]
            summon_button.setEnabled(False)
            summon_button.setText("")
            summon_button.setToolTip(
                f"{character_display_name(character_name)} 尚未載入"
            )

    @staticmethod
    def _build_avatar_tooltip(character_name, member):
        if member is None or not member.available:
            return f"{character_display_name(character_name)} 尚未載入"
        return RelationSummonPanel._format_avatar_tooltip(
            character_name,
            member.mood_score,
            member.mood_state,
        )

    @staticmethod
    def _format_avatar_tooltip(character_name, mood_score, mood_state):
        mood_labels = {
            "normal": "平穩",
            "unhappy": "低落",
            "depressed": "非常低落",
        }
        if mood_score is None:
            mood_text = "心情：尚無資料"
        else:
            mood_label = mood_labels.get(mood_state, "平穩")
            mood_text = f"心情：{mood_label}（{mood_score:.0f}/100）"
        return (
            f"查看 {character_display_name(character_name)} 對其他角色的關係\n"
            f"{mood_text}"
        )

    def eventFilter(self, watched, event):
        character_name = self.avatar_button_names.get(watched)
        if (
            character_name
            and event.type() == QEvent.Type.Enter
            and self.binding is not None
            and hasattr(self.binding, "mood_snapshot")
        ):
            mood = self.binding.mood_snapshot().get(character_name)
            if mood is not None:
                watched.setToolTip(
                    self._format_avatar_tooltip(character_name, mood[0], mood[1])
                )
        return super().eventFilter(watched, event)
