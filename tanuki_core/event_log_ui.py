from PyQt6.QtCore import QSignalBlocker, QSize, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .ui_theme import DEFAULT_UI_THEME
from .ui_icons import (
    EVENT_CHANNEL_COLORS,
    METRIC_COLORS,
    create_metric_icon,
    create_ui_icon,
    create_ui_pixmap,
)
from .ui_localization import (
    character_display_name,
    localize_character_names_in_text,
)


EVENT_LOG_FILTER_OPTIONS = (
    ("all", "全部"),
    ("personal", "個人"),
    ("social", "社交"),
    ("economy", "經濟"),
    ("item", "道具"),
    ("system", "系統"),
)

EVENT_IMPORTANCE_LABELS = {
    "low": "一般",
    "normal": "一般",
    "major": "重要",
    "high": "重要",
    "critical": "關鍵",
}


class EventLogPanel(QWidget):
    TIME_COLUMN = 0
    CHANNEL_COLUMN = 1
    PARTICIPANT_COLUMN = 2
    SUMMARY_COLUMN = 3

    def __init__(self, binding=None, parent=None, theme=DEFAULT_UI_THEME):
        super().__init__(parent)
        self.binding = None
        self.theme = theme
        self.filter_mode = "all"
        self.participant_name = ""
        self.entries = ()
        self._selected_sequence = None
        self._applying_presentation = False
        self.effect_value_labels = {}
        self.effect_icon_labels = {}

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(theme.spacing_sm)

        heading_row = QHBoxLayout()
        heading_row.setSpacing(theme.spacing_sm)
        self.title_label = QLabel("事件日誌")
        self.title_label.setProperty("tanukiRole", "eventHeading")
        heading_row.addWidget(self.title_label)
        heading_row.addStretch(1)
        root_layout.addLayout(heading_row)

        self.unavailable_label = QLabel("事件日誌尚未連接執行中的 Dashboard。")
        self.unavailable_label.setProperty("tanukiRole", "eventNotice")
        self.unavailable_label.setWordWrap(True)
        root_layout.addWidget(self.unavailable_label)

        controls_row = QHBoxLayout()
        controls_row.setSpacing(theme.spacing_sm)
        self.filter_group = QButtonGroup(self)
        self.filter_group.setExclusive(True)
        self.filter_buttons = {}
        for mode, label in EVENT_LOG_FILTER_OPTIONS:
            button = QPushButton(label)
            button.setCheckable(True)
            button.setProperty("tanukiRole", "eventFilter")
            button.setIcon(create_ui_icon(mode, size=16))
            button.setIconSize(QSize(16, 16))
            button.clicked.connect(
                lambda checked=False, selected_mode=mode: self.set_filter_mode(selected_mode)
            )
            self.filter_group.addButton(button)
            self.filter_buttons[mode] = button
            controls_row.addWidget(button)
        controls_row.addStretch(1)
        self.participant_label = QLabel()
        self.participant_label.setPixmap(create_ui_pixmap("personal", size=18))
        self.participant_label.setFixedSize(22, 22)
        self.participant_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.participant_label.setAccessibleName("個人篩選角色")
        self.participant_label.setToolTip("個人篩選角色")
        self.participant_label.setProperty("tanukiRole", "eventLabel")
        controls_row.addWidget(self.participant_label)
        self.participant_combo = QComboBox()
        self.participant_combo.setMinimumWidth(130)
        self.participant_combo.setPlaceholderText("個人篩選")
        self.participant_combo.setToolTip("僅在「個人」篩選時使用")
        self.participant_combo.setProperty("tanukiRole", "eventParticipant")
        self.participant_combo.currentIndexChanged.connect(
            self._handle_participant_index_changed
        )
        controls_row.addWidget(self.participant_combo)
        root_layout.addLayout(controls_row)

        self.content_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.content_splitter.setObjectName("tanukiEventSplitter")
        self.content_splitter.setChildrenCollapsible(False)
        self.content_splitter.setHandleWidth(5)
        root_layout.addWidget(self.content_splitter, stretch=1)

        self.list_pane = QFrame()
        self.list_pane.setProperty("tanukiRole", "eventPane")
        list_layout = QVBoxLayout(self.list_pane)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)
        self.list_stack = QStackedWidget()
        list_layout.addWidget(self.list_stack)

        self.event_table = QTableWidget(0, 4)
        self.event_table.setProperty("tanukiRole", "eventList")
        self.event_table.setAccessibleName("事件列表")
        self.event_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.event_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.event_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.event_table.setShowGrid(True)
        self.event_table.setAlternatingRowColors(False)
        self.event_table.setWordWrap(True)
        self.event_table.setIconSize(QSize(17, 17))
        self.event_table.verticalHeader().hide()
        self.event_table.horizontalHeader().hide()
        self.event_table.setColumnWidth(self.TIME_COLUMN, 98)
        self.event_table.setColumnWidth(self.CHANNEL_COLUMN, 72)
        self.event_table.setColumnWidth(self.PARTICIPANT_COLUMN, 145)
        table_header = self.event_table.horizontalHeader()
        table_header.setSectionResizeMode(self.TIME_COLUMN, QHeaderView.ResizeMode.Fixed)
        table_header.setSectionResizeMode(self.CHANNEL_COLUMN, QHeaderView.ResizeMode.Fixed)
        table_header.setSectionResizeMode(self.PARTICIPANT_COLUMN, QHeaderView.ResizeMode.Fixed)
        table_header.setSectionResizeMode(self.SUMMARY_COLUMN, QHeaderView.ResizeMode.Stretch)
        self.event_table.currentCellChanged.connect(self._on_current_cell_changed)
        self.list_stack.addWidget(self.event_table)

        self.empty_list_label = QLabel("目前沒有符合條件的紀錄。")
        self.empty_list_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_list_label.setWordWrap(True)
        self.empty_list_label.setProperty("tanukiRole", "eventEmpty")
        self.list_stack.addWidget(self.empty_list_label)

        self.detail_pane = QFrame()
        self.detail_pane.setProperty("tanukiRole", "eventPane")
        detail_pane_layout = QVBoxLayout(self.detail_pane)
        detail_pane_layout.setContentsMargins(0, 0, 0, 0)
        detail_pane_layout.setSpacing(0)
        self.detail_stack = QStackedWidget()
        detail_pane_layout.addWidget(self.detail_stack)

        self.empty_detail_label = QLabel("選取左側事件以查看詳情。")
        self.empty_detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_detail_label.setWordWrap(True)
        self.empty_detail_label.setProperty("tanukiRole", "eventEmpty")
        self.detail_stack.addWidget(self.empty_detail_label)

        self.detail_scroll = QScrollArea()
        self.detail_scroll.setWidgetResizable(True)
        self.detail_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.detail_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.detail_scroll.setProperty("tanukiRole", "eventDetailScroll")
        self.detail_content = QWidget()
        self.detail_content.setProperty("tanukiRole", "eventDetail")
        detail_layout = QVBoxLayout(self.detail_content)
        detail_layout.setContentsMargins(
            theme.spacing_md,
            theme.spacing_sm,
            theme.spacing_md,
            theme.spacing_md,
        )
        detail_layout.setSpacing(theme.spacing_sm)

        detail_heading_row = QHBoxLayout()
        self.detail_channel_icon_label = QLabel()
        self.detail_channel_icon_label.setFixedSize(22, 22)
        self.detail_channel_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail_heading_row.addWidget(self.detail_channel_icon_label)
        self.detail_heading_label = QLabel("事件詳情")
        self.detail_heading_label.setProperty("tanukiRole", "eventDetailHeading")
        detail_heading_row.addWidget(self.detail_heading_label)
        detail_heading_row.addStretch(1)
        self.detail_channel_label = QLabel()
        self.detail_channel_label.setProperty("tanukiRole", "eventChannelBadge")
        detail_heading_row.addWidget(self.detail_channel_label)
        detail_layout.addLayout(detail_heading_row)

        self.detail_time_label = QLabel()
        self.detail_time_label.setProperty("tanukiRole", "eventDetailTime")
        detail_time_row = QHBoxLayout()
        detail_time_row.setSpacing(theme.spacing_sm)
        self.detail_time_icon_label = QLabel()
        self.detail_time_icon_label.setPixmap(create_ui_pixmap("time", size=16))
        self.detail_time_icon_label.setFixedSize(18, 18)
        detail_time_row.addWidget(self.detail_time_icon_label)
        detail_time_row.addWidget(self.detail_time_label)
        detail_time_row.addStretch(1)
        detail_layout.addLayout(detail_time_row)

        self.detail_summary_label = QLabel()
        self.detail_summary_label.setWordWrap(True)
        self.detail_summary_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.detail_summary_label.setProperty("tanukiRole", "eventDetailSummary")
        detail_layout.addWidget(self.detail_summary_label)

        self.detail_participant_label = QLabel()
        self.detail_participant_label.setWordWrap(True)
        self.detail_participant_label.setProperty("tanukiRole", "eventParticipants")
        detail_participant_row = QHBoxLayout()
        detail_participant_row.setSpacing(theme.spacing_sm)
        self.detail_participant_icon_label = QLabel()
        self.detail_participant_icon_label.setPixmap(
            create_ui_pixmap("participants", color="#f4df9c", size=17)
        )
        self.detail_participant_icon_label.setFixedSize(19, 19)
        detail_participant_row.addWidget(self.detail_participant_icon_label)
        detail_participant_row.addWidget(self.detail_participant_label, stretch=1)
        detail_layout.addLayout(detail_participant_row)

        self.detail_separator = QFrame()
        self.detail_separator.setFrameShape(QFrame.Shape.HLine)
        self.detail_separator.setProperty("tanukiRole", "eventSeparator")
        detail_layout.addWidget(self.detail_separator)

        self.effects_frame = QFrame()
        self.effects_frame.setProperty("tanukiRole", "eventEffects")
        self.effects_layout = QVBoxLayout(self.effects_frame)
        self.effects_layout.setContentsMargins(0, 0, 0, 0)
        self.effects_layout.setSpacing(theme.spacing_xs)
        detail_layout.addWidget(self.effects_frame)

        self.detail_tags_label = QLabel()
        self.detail_tags_label.setWordWrap(True)
        self.detail_tags_label.setProperty("tanukiRole", "eventTags")
        detail_tags_row = QHBoxLayout()
        detail_tags_row.setSpacing(theme.spacing_sm)
        self.detail_tags_icon_label = QLabel()
        self.detail_tags_icon_label.setPixmap(create_ui_pixmap("tag", size=16))
        self.detail_tags_icon_label.setFixedSize(18, 18)
        detail_tags_row.addWidget(self.detail_tags_icon_label)
        detail_tags_row.addWidget(self.detail_tags_label, stretch=1)
        detail_layout.addLayout(detail_tags_row)

        self.detail_metadata_label = QLabel()
        self.detail_metadata_label.setWordWrap(True)
        self.detail_metadata_label.setProperty("tanukiRole", "eventMetadata")
        detail_metadata_row = QHBoxLayout()
        detail_metadata_row.setSpacing(theme.spacing_sm)
        self.detail_metadata_icon_label = QLabel()
        self.detail_metadata_icon_label.setPixmap(create_ui_pixmap("info", size=16))
        self.detail_metadata_icon_label.setFixedSize(18, 18)
        detail_metadata_row.addWidget(self.detail_metadata_icon_label)
        detail_metadata_row.addWidget(self.detail_metadata_label, stretch=1)
        detail_layout.addLayout(detail_metadata_row)
        detail_layout.addStretch(1)

        self.detail_scroll.setWidget(self.detail_content)
        self.detail_stack.addWidget(self.detail_scroll)

        self.content_splitter.addWidget(self.list_pane)
        self.content_splitter.addWidget(self.detail_pane)
        self.content_splitter.setStretchFactor(0, 3)
        self.content_splitter.setStretchFactor(1, 2)
        self.content_splitter.setSizes((430, 250))

        self.set_binding(binding)

    @property
    def selected_entry(self):
        row = self.event_table.currentRow()
        if 0 <= row < len(self.entries):
            return self.entries[row]
        return None

    def set_binding(self, binding):
        self.binding = binding
        connected = binding is not None
        self.unavailable_label.setVisible(not connected)
        for button in self.filter_buttons.values():
            button.setEnabled(connected)
        if connected:
            self.refresh_from_binding()
        else:
            self.title_label.setText("事件日誌")
            self.entries = ()
            self.event_table.setRowCount(0)
            self.empty_list_label.setText("目前尚無事件資料。")
            self.list_stack.setCurrentWidget(self.empty_list_label)
            self.detail_stack.setCurrentWidget(self.empty_detail_label)
            self._update_filter_controls()

    def set_filter_mode(self, mode):
        normalized_mode = str(mode or "all")
        valid_modes = {option_mode for option_mode, _label in EVENT_LOG_FILTER_OPTIONS}
        self.filter_mode = normalized_mode if normalized_mode in valid_modes else "all"
        self._selected_sequence = None
        self._update_filter_controls()
        self.refresh_from_binding()

    def set_participant_name(self, participant_name):
        if self._applying_presentation:
            return
        self.participant_name = str(participant_name or "")
        if self.filter_mode == "personal":
            self._selected_sequence = None
            self.refresh_from_binding()

    def _handle_participant_index_changed(self, index):
        participant_name = (
            self.participant_combo.itemData(index, Qt.ItemDataRole.UserRole)
            if index >= 0 else
            ""
        )
        self.set_participant_name(participant_name)

    def refresh_from_binding(self):
        if self.binding is None:
            return
        presentation = self.binding.presentation(
            filter_mode=self.filter_mode,
            participant_name=self.participant_name,
        )
        self.apply_presentation(presentation)

    def apply_presentation(self, presentation):
        previous_sequence = self._selected_sequence
        selected_entry = self.selected_entry
        if selected_entry is not None:
            previous_sequence = selected_entry.sequence

        self._applying_presentation = True
        try:
            self.title_label.setText(
                localize_character_names_in_text(presentation.title)
            )
            self.filter_mode = presentation.filter_mode
            self.participant_name = presentation.participant_name
            self._update_filter_controls()

            blocker = QSignalBlocker(self.participant_combo)
            current_names = tuple(
                self.participant_combo.itemData(index, Qt.ItemDataRole.UserRole)
                for index in range(self.participant_combo.count())
            )
            if current_names != presentation.participant_names:
                self.participant_combo.clear()
                for character_name in presentation.participant_names:
                    self.participant_combo.addItem(
                        character_display_name(character_name),
                        character_name,
                    )
            target_index = (
                self.participant_combo.findData(
                    presentation.participant_name,
                    role=Qt.ItemDataRole.UserRole,
                )
                if presentation.filter_mode == "personal" else
                -1
            )
            self.participant_combo.setCurrentIndex(target_index)
            del blocker

            self.entries = tuple(getattr(presentation, "entries", ()) or ())
            table_blocker = QSignalBlocker(self.event_table)
            self.event_table.clearContents()
            self.event_table.setRowCount(len(self.entries))
            for row, entry in enumerate(self.entries):
                self._populate_event_row(row, entry)
            del table_blocker

            if not self.entries:
                self.empty_list_label.setText("目前沒有符合條件的紀錄。")
                self.list_stack.setCurrentWidget(self.empty_list_label)
                self.event_table.clearSelection()
                self.detail_stack.setCurrentWidget(self.empty_detail_label)
                self._selected_sequence = None
                return

            self.list_stack.setCurrentWidget(self.event_table)
            selected_row = next(
                (
                    row for row, entry in enumerate(self.entries)
                    if entry.sequence == previous_sequence
                ),
                0,
            )
            self.event_table.setCurrentCell(selected_row, self.SUMMARY_COLUMN)
            self.event_table.selectRow(selected_row)
            self._show_entry_details(self.entries[selected_row])
        finally:
            self._applying_presentation = False

    def _populate_event_row(self, row, entry):
        actor_name = character_display_name(entry.actor_name)
        target_name = character_display_name(entry.target_name)
        if actor_name and target_name and actor_name != target_name:
            participant_text = f"{actor_name} → {target_name}"
        elif actor_name or target_name:
            participant_text = actor_name or target_name
        else:
            participant_text = "家庭／系統"
        values = (
            entry.timestamp_text,
            entry.channel_label,
            participant_text,
            localize_character_names_in_text(entry.summary),
        )
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setData(Qt.ItemDataRole.UserRole, entry.sequence)
            item.setToolTip(value)
            if column == self.CHANNEL_COLUMN:
                item.setForeground(
                    QColor(EVENT_CHANNEL_COLORS.get(entry.channel, "#e8dcae"))
                )
                item.setIcon(
                    create_ui_icon(
                        entry.channel if entry.channel in EVENT_CHANNEL_COLORS else "info",
                        color=EVENT_CHANNEL_COLORS.get(entry.channel, "#e8dcae"),
                        size=17,
                    )
                )
            self.event_table.setItem(row, column, item)
        self.event_table.setRowHeight(row, 48)

    def _on_current_cell_changed(self, row, _column, _previous_row, _previous_column):
        if self._applying_presentation or not 0 <= row < len(self.entries):
            return
        self._show_entry_details(self.entries[row])

    def _show_entry_details(self, entry):
        self._selected_sequence = entry.sequence
        self.detail_heading_label.setText("事件詳情")
        self.detail_channel_icon_label.setPixmap(
            create_ui_pixmap(
                entry.channel if entry.channel in EVENT_CHANNEL_COLORS else "info",
                color=EVENT_CHANNEL_COLORS.get(entry.channel, "#e8dcae"),
                size=19,
            )
        )
        self.detail_channel_label.setText(entry.channel_label)
        self.detail_channel_label.setProperty("eventChannel", entry.channel)
        self.detail_channel_label.style().unpolish(self.detail_channel_label)
        self.detail_channel_label.style().polish(self.detail_channel_label)
        self.detail_time_label.setText(entry.timestamp_text)
        self.detail_summary_label.setText(
            localize_character_names_in_text(entry.summary)
        )

        actor_name = character_display_name(entry.actor_name)
        target_name = character_display_name(entry.target_name)
        if actor_name and target_name and actor_name != target_name:
            participant_text = f"{actor_name}　→　{target_name}"
        elif actor_name or target_name:
            participant_text = actor_name or target_name
        else:
            participant_text = "家庭／系統事件"
        self.detail_participant_label.setText(participant_text)

        self._replace_effect_rows(entry.effects)
        tags_text = " · ".join(f"#{tag}" for tag in entry.tags) if entry.tags else "沒有標籤"
        self.detail_tags_label.setText(f"標籤　{tags_text}")
        importance_label = EVENT_IMPORTANCE_LABELS.get(
            entry.importance,
            entry.importance or "一般",
        )
        type_parts = [
            part for part in (entry.category, entry.event_type)
            if part
        ]
        type_text = " / ".join(type_parts) if type_parts else "一般事件"
        self.detail_metadata_label.setText(
            f"#{entry.sequence:03d}　{importance_label}　{type_text}"
        )
        self.detail_stack.setCurrentWidget(self.detail_scroll)
        self.detail_scroll.verticalScrollBar().setValue(0)

    def _replace_effect_rows(self, effects):
        while self.effects_layout.count():
            item = self.effects_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.effect_value_labels = {}
        self.effect_icon_labels = {}

        if not effects:
            empty_label = QLabel("本事件沒有數值變化")
            empty_label.setProperty("tanukiRole", "eventNoEffects")
            self.effects_layout.addWidget(empty_label)
            return

        for effect in effects:
            row_widget = QWidget()
            row_widget.setProperty("tanukiRole", "eventEffectRow")
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(self.theme.spacing_sm)
            metric_kind = effect.key.removeprefix("relationship_")
            icon_label = QLabel()
            if effect.key.startswith("relationship_") and metric_kind in METRIC_COLORS:
                icon_label.setPixmap(
                    create_metric_icon(metric_kind, size=18).pixmap(18, 18)
                )
                icon_label.setToolTip(effect.label)
            else:
                icon_label.setPixmap(
                    create_ui_pixmap(
                        metric_kind,
                        color="#f4df9c",
                        size=16,
                    )
                )
            icon_label.setFixedSize(20, 20)
            row_layout.addWidget(icon_label)
            name_label = QLabel(effect.label)
            name_label.setProperty("tanukiRole", "eventEffectLabel")
            row_layout.addWidget(name_label)
            row_layout.addStretch(1)
            value_label = QLabel(effect.value_text)
            value_label.setProperty("tanukiRole", "eventEffectValue")
            value_label.setProperty(
                "deltaTone",
                "positive" if effect.value > 0 else "negative",
            )
            value_label.setProperty(
                "metricKind",
                metric_kind if effect.key.startswith("relationship_") else "",
            )
            row_layout.addWidget(value_label)
            self.effect_icon_labels[effect.key] = icon_label
            self.effect_value_labels[effect.key] = value_label
            self.effects_layout.addWidget(row_widget)

    def _update_filter_controls(self):
        for mode, button in self.filter_buttons.items():
            button.setChecked(mode == self.filter_mode)
        personal_mode = self.filter_mode == "personal" and self.binding is not None
        self.participant_label.setEnabled(personal_mode)
        self.participant_combo.setEnabled(personal_mode)
        self.participant_label.setPixmap(
            create_ui_pixmap(
                "personal",
                color="#fffaf2" if personal_mode else "#587068",
                size=18,
            )
        )
        self.participant_label.setProperty("personalActive", personal_mode)
        self.participant_combo.setProperty("personalActive", personal_mode)
        self.participant_combo.setMinimumWidth(145 if personal_mode else 86)
        self.participant_combo.setMaximumWidth(220 if personal_mode else 104)
        for widget in (self.participant_label, self.participant_combo):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
