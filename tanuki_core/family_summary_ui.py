from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QColor, QIcon
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .ui_icons import EVENT_CHANNEL_COLORS, create_ui_icon, create_ui_pixmap
from .ui_localization import (
    character_display_name,
    localize_character_names_in_text,
)
from .ui_theme import DEFAULT_UI_THEME


MOOD_BAND_COLORS = {
    "normal": "#4eaa65",
    "unhappy": "#dfa72d",
    "depressed": "#4f83b7",
    "unknown": "#8a938c",
}


class FamilyMemberCard(QFrame):
    def __init__(self, member, avatar_pixmap=None, parent=None):
        super().__init__(parent)
        self.member = member
        self.setProperty("tanukiRole", "familyMemberCard")
        self.setProperty("summoned", bool(member.summoned))
        self.setFixedWidth(116)
        self.setMinimumHeight(194)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(7, 7, 7, 7)
        layout.setSpacing(3)

        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(52, 52)
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_label.setProperty("tanukiRole", "familyAvatar")
        if avatar_pixmap is not None and not avatar_pixmap.isNull():
            self.avatar_label.setPixmap(QIcon(avatar_pixmap).pixmap(50, 50))
        else:
            self.avatar_label.setPixmap(
                create_ui_pixmap("personal", color="#4eaa65", size=42)
            )
        layout.addWidget(
            self.avatar_label,
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )

        display_name = character_display_name(member.character_name)
        self.name_label = QLabel(display_name)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setFixedHeight(30)
        self.name_label.setToolTip(display_name)
        self.name_label.setProperty("tanukiRole", "familyMemberName")
        layout.addWidget(self.name_label)

        mood_row = QHBoxLayout()
        mood_row.setSpacing(4)
        mood_band = member.mood_state if member.mood_state in MOOD_BAND_COLORS else "unknown"
        mood_icon = QLabel()
        mood_icon.setPixmap(
            create_ui_pixmap(
                "mood",
                color=MOOD_BAND_COLORS[mood_band],
                size=15,
            )
        )
        mood_icon.setFixedSize(17, 17)
        mood_icon.setToolTip(f"心情：{member.mood_label}")
        self.mood_icon = mood_icon
        mood_row.addWidget(mood_icon)
        self.mood_bar = QProgressBar()
        self.mood_bar.setRange(0, 100)
        self.mood_bar.setValue(
            0 if member.mood_score is None else int(round(member.mood_score))
        )
        self.mood_bar.setTextVisible(False)
        self.mood_bar.setProperty("tanukiRole", "familyMood")
        self.mood_bar.setProperty("moodBand", mood_band)
        self.mood_bar.setToolTip(
            f"{member.mood_label}"
            if member.mood_score is None else
            f"{member.mood_label}（{member.mood_score:.0f}/100）"
        )
        mood_row.addWidget(self.mood_bar, stretch=1)
        self.mood_value_label = QLabel(
            "--" if member.mood_score is None else f"{member.mood_score:.0f}"
        )
        self.mood_value_label.setFixedWidth(22)
        self.mood_value_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.mood_value_label.setProperty("tanukiRole", "familyMoodValue")
        mood_row.addWidget(self.mood_value_label)
        layout.addLayout(mood_row)

        self.form_status_label = QLabel(
            "✦ 變身形態"
            if member.form_key == "transformed"
            else "◇ 普通形態"
        )
        self.form_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.form_status_label.setProperty(
            "tanukiRole",
            "familyFormStatus",
        )
        self.form_status_label.setProperty(
            "transformed",
            member.form_key == "transformed",
        )
        layout.addWidget(self.form_status_label)

        self.sleep_rhythm_label = QLabel(member.sleep_rhythm_text)
        self.sleep_rhythm_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sleep_rhythm_label.setProperty(
            "tanukiRole",
            "familyRhythmStatus",
        )
        self.sleep_rhythm_label.setVisible(bool(member.sleep_rhythm_text))
        layout.addWidget(self.sleep_rhythm_label)

        self.transformation_rhythm_label = QLabel(
            member.transformation_rhythm_text
        )
        self.transformation_rhythm_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.transformation_rhythm_label.setWordWrap(True)
        self.transformation_rhythm_label.setProperty(
            "tanukiRole",
            "familyRhythmStatus",
        )
        self.transformation_rhythm_label.setVisible(
            bool(member.transformation_rhythm_text)
        )
        layout.addWidget(self.transformation_rhythm_label)

        self.summon_status_label = QLabel(
            "● 召喚中" if member.summoned else "○ 待命"
        )
        self.summon_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.summon_status_label.setProperty("tanukiRole", "familySummonStatus")
        self.summon_status_label.setProperty("summoned", bool(member.summoned))
        layout.addWidget(self.summon_status_label)
        self._apply_tooltip(member)

    def apply_live_member(self, member):
        """Update mutable labels without rebuilding the card or its layout."""
        if member.character_name != self.member.character_name:
            return False
        self.member = member
        summoned = bool(member.summoned)
        if bool(self.property("summoned")) != summoned:
            self.setProperty("summoned", summoned)
            self._refresh_dynamic_style(self)

        mood_band = (
            member.mood_state
            if member.mood_state in MOOD_BAND_COLORS else
            "unknown"
        )
        if self.mood_bar.property("moodBand") != mood_band:
            self.mood_bar.setProperty("moodBand", mood_band)
            self._refresh_dynamic_style(self.mood_bar)
            self.mood_icon.setPixmap(
                create_ui_pixmap(
                    "mood",
                    color=MOOD_BAND_COLORS[mood_band],
                    size=15,
                )
            )
        self.mood_icon.setToolTip(f"心情：{member.mood_label}")
        mood_value = (
            0
            if member.mood_score is None else
            int(round(member.mood_score))
        )
        if self.mood_bar.value() != mood_value:
            self.mood_bar.setValue(mood_value)
        mood_value_text = (
            "--"
            if member.mood_score is None else
            f"{member.mood_score:.0f}"
        )
        self._set_label_text(self.mood_value_label, mood_value_text)
        self.mood_bar.setToolTip(
            f"{member.mood_label}"
            if member.mood_score is None else
            f"{member.mood_label}（{member.mood_score:.0f}/100）"
        )

        transformed = member.form_key == "transformed"
        self._set_label_text(
            self.form_status_label,
            "✦ 變身形態" if transformed else "◇ 普通形態",
        )
        if bool(self.form_status_label.property("transformed")) != transformed:
            self.form_status_label.setProperty("transformed", transformed)
            self._refresh_dynamic_style(self.form_status_label)

        self._set_optional_label_text(
            self.sleep_rhythm_label,
            member.sleep_rhythm_text,
        )
        self._set_optional_label_text(
            self.transformation_rhythm_label,
            member.transformation_rhythm_text,
        )

        self._set_label_text(
            self.summon_status_label,
            "● 召喚中" if summoned else "○ 待命",
        )
        if (
            bool(self.summon_status_label.property("summoned"))
            != summoned
        ):
            self.summon_status_label.setProperty("summoned", summoned)
            self._refresh_dynamic_style(self.summon_status_label)
        self._apply_tooltip(member)
        return True

    def _apply_tooltip(self, member):
        display_name = character_display_name(member.character_name)
        self.setToolTip(
            f"{display_name}\n"
            f"心情：{member.mood_label}"
            + (
                "" if member.mood_score is None else
                f"（{member.mood_score:.0f}/100）"
            )
            + f"\n形態：{member.form_label}"
            + (
                f"\n{member.sleep_rhythm_text}"
                if member.sleep_rhythm_text else
                ""
            )
            + (
                f"\n{member.transformation_rhythm_text}"
                if member.transformation_rhythm_text else
                ""
            )
            + f"\n{'目前已召喚' if member.summoned else '目前待命'}"
        )

    @staticmethod
    def _set_label_text(label, text):
        text = str(text or "")
        if label.text() != text:
            label.setText(text)

    @classmethod
    def _set_optional_label_text(cls, label, text):
        text = str(text or "")
        cls._set_label_text(label, text)
        visible = bool(text)
        if label.isVisible() != visible:
            label.setVisible(visible)

    @staticmethod
    def _refresh_dynamic_style(widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()


class FamilySummaryPanel(QWidget):
    def __init__(
        self,
        binding=None,
        parent=None,
        theme=DEFAULT_UI_THEME,
        assets=None,
    ):
        super().__init__(parent)
        self.binding = None
        self.theme = theme
        self.assets = assets
        self.member_cards = {}
        self.avatar_pixmaps = self._load_avatar_pixmaps(assets)
        self.rhythm_refresh_timer = QTimer(self)
        self.rhythm_refresh_timer.setInterval(1000)
        self.rhythm_refresh_timer.timeout.connect(
            self.refresh_rhythm_from_binding
        )

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(theme.spacing_sm)

        heading_row = QHBoxLayout()
        heading_icon = QLabel()
        heading_icon.setPixmap(create_ui_pixmap("all", color="#2b8b4b", size=20))
        heading_row.addWidget(heading_icon)
        self.title_label = QLabel("家庭狀態")
        self.title_label.setProperty("tanukiRole", "familyHeading")
        heading_row.addWidget(self.title_label)
        heading_row.addStretch(1)
        self.race_rhythm_label = QLabel("")
        self.race_rhythm_label.setProperty(
            "tanukiRole",
            "familyRhythmStatus",
        )
        self.race_rhythm_label.setToolTip(
            "顯示下一次自主競賽提案的排程；實際開始仍需通過資格與距離判定。"
        )
        heading_row.addWidget(self.race_rhythm_label)
        root_layout.addLayout(heading_row)

        self.unavailable_label = QLabel("家庭資料尚未連接執行中的 Dashboard。")
        self.unavailable_label.setProperty("tanukiRole", "familyNotice")
        self.unavailable_label.setWordWrap(True)
        root_layout.addWidget(self.unavailable_label)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(theme.spacing_sm)
        fund_card, fund_layout = self._create_metric_card("economy", "生活費")
        fund_value_row = QHBoxLayout()
        fund_value_row.setSpacing(theme.spacing_xs)
        self.fund_value_label = QLabel("--")
        self.fund_value_label.setProperty("tanukiRole", "familyValue")
        fund_value_row.addWidget(self.fund_value_label)
        fund_value_row.addStretch(1)
        self.donate_button = QPushButton("＋100")
        self.donate_button.setIcon(
            create_ui_icon("economy", color="#2b8b4b", size=16)
        )
        self.donate_button.setIconSize(QSize(16, 16))
        self.donate_button.setProperty("tanukiRole", "familyAction")
        self.donate_button.setAccessibleName("捐生活費 100 元")
        self.donate_button.clicked.connect(self._handle_donate)
        fund_value_row.addWidget(self.donate_button)
        fund_layout.addLayout(fund_value_row)

        pressure_card, pressure_layout = self._create_metric_card(
            "household_pressure",
            "家庭壓力",
        )
        pressure_value_row = QHBoxLayout()
        self.pressure_value_label = QLabel("--")
        self.pressure_value_label.setProperty("tanukiRole", "familyValue")
        pressure_value_row.addWidget(self.pressure_value_label)
        pressure_value_row.addStretch(1)
        self.pressure_level_label = QLabel("--")
        self.pressure_level_label.setProperty("tanukiRole", "familyMetricHint")
        pressure_value_row.addWidget(self.pressure_level_label)
        pressure_layout.addLayout(pressure_value_row)
        self.pressure_bar = QProgressBar()
        self.pressure_bar.setRange(0, 100)
        self.pressure_bar.setTextVisible(False)
        self.pressure_bar.setProperty("tanukiRole", "familyPressure")
        pressure_layout.addWidget(self.pressure_bar)

        summon_card, summon_layout = self._create_metric_card(
            "personal",
            "目前召喚",
        )
        self.summon_value_label = QLabel("0 / 0")
        self.summon_value_label.setProperty("tanukiRole", "familyValue")
        summon_layout.addWidget(self.summon_value_label)
        self.summon_hint_label = QLabel("尚無成員")
        self.summon_hint_label.setProperty("tanukiRole", "familyMetricHint")
        summon_layout.addWidget(self.summon_hint_label)

        cards_row.addWidget(fund_card, stretch=1)
        cards_row.addWidget(pressure_card, stretch=2)
        cards_row.addWidget(summon_card, stretch=1)
        root_layout.addLayout(cards_row)

        body_row = QHBoxLayout()
        body_row.setSpacing(theme.spacing_sm)

        members_frame = QFrame()
        members_frame.setProperty("tanukiRole", "familySectionCard")
        members_layout = QVBoxLayout(members_frame)
        members_layout.setContentsMargins(
            theme.spacing_sm,
            theme.spacing_sm,
            theme.spacing_sm,
            theme.spacing_sm,
        )
        members_layout.setSpacing(theme.spacing_xs)
        members_header = QHBoxLayout()
        members_icon = QLabel()
        members_icon.setPixmap(create_ui_pixmap("social", color="#2b8b4b", size=18))
        members_header.addWidget(members_icon)
        members_label = QLabel("家庭成員")
        members_label.setProperty("tanukiRole", "familySection")
        members_header.addWidget(members_label)
        members_header.addStretch(1)
        self.member_count_label = QLabel("0 人")
        self.member_count_label.setProperty("tanukiRole", "familySectionCount")
        members_header.addWidget(self.member_count_label)
        members_layout.addLayout(members_header)

        self.members_stack = QStackedWidget()
        self.members_scroll = QScrollArea()
        self.members_scroll.setWidgetResizable(True)
        self.members_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.members_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.members_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.members_scroll.setProperty("tanukiRole", "familyMembersScroll")
        self.members_content = QWidget()
        self.members_content.setProperty("tanukiRole", "familyMembersContent")
        self.members_row = QHBoxLayout(self.members_content)
        self.members_row.setContentsMargins(0, 0, 0, 0)
        self.members_row.setSpacing(theme.spacing_sm)
        self.members_row.addStretch(1)
        self.members_scroll.setWidget(self.members_content)
        self.members_stack.addWidget(self.members_scroll)
        self.members_empty_label = QLabel("目前沒有角色 runtime 資料。")
        self.members_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.members_empty_label.setWordWrap(True)
        self.members_empty_label.setProperty("tanukiRole", "familyEmpty")
        self.members_stack.addWidget(self.members_empty_label)
        members_layout.addWidget(self.members_stack, stretch=1)

        events_frame = QFrame()
        events_frame.setProperty("tanukiRole", "familySectionCard")
        events_layout = QVBoxLayout(events_frame)
        events_layout.setContentsMargins(
            theme.spacing_sm,
            theme.spacing_sm,
            theme.spacing_sm,
            theme.spacing_sm,
        )
        events_layout.setSpacing(theme.spacing_xs)
        events_header = QHBoxLayout()
        events_icon = QLabel()
        events_icon.setPixmap(create_ui_pixmap("story", color="#2b8b4b", size=18))
        events_header.addWidget(events_icon)
        events_label = QLabel("近期事件")
        events_label.setProperty("tanukiRole", "familySection")
        events_header.addWidget(events_label)
        events_header.addStretch(1)
        events_layout.addLayout(events_header)

        self.recent_event_table = QTableWidget(0, 3)
        self.recent_event_table.setProperty("tanukiRole", "familyEvents")
        self.recent_event_table.setAccessibleName("家庭近期事件")
        self.recent_event_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.recent_event_table.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        self.recent_event_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.recent_event_table.setShowGrid(False)
        self.recent_event_table.setWordWrap(True)
        self.recent_event_table.setIconSize(QSize(16, 16))
        self.recent_event_table.verticalHeader().hide()
        self.recent_event_table.horizontalHeader().hide()
        self.recent_event_table.setColumnWidth(0, 82)
        self.recent_event_table.setColumnWidth(1, 72)
        event_header = self.recent_event_table.horizontalHeader()
        event_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        event_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        event_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        events_layout.addWidget(self.recent_event_table, stretch=1)
        self.events_empty_label = QLabel("目前尚無家庭重點事件。")
        self.events_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.events_empty_label.setWordWrap(True)
        self.events_empty_label.setProperty("tanukiRole", "familyEmpty")
        events_layout.addWidget(self.events_empty_label, stretch=1)

        body_row.addWidget(members_frame, stretch=3)
        body_row.addWidget(events_frame, stretch=2)
        root_layout.addLayout(body_row, stretch=1)

        self.stats_frame = QFrame()
        self.stats_frame.setProperty("tanukiRole", "familyStats")
        stats_layout = QHBoxLayout(self.stats_frame)
        stats_layout.setContentsMargins(
            theme.spacing_sm,
            theme.spacing_xs,
            theme.spacing_sm,
            theme.spacing_xs,
        )
        stats_layout.setSpacing(theme.spacing_sm)
        self.stat_value_labels = {}
        for key, icon_name, label in (
            ("average_mood", "mood", "平均心情"),
            ("fund_delta", "economy", "近期收支"),
            ("pressure_delta", "household_pressure", "壓力變化"),
            ("event_count", "all", "事件數"),
        ):
            stat_widget = QWidget()
            stat_widget.setProperty("tanukiRole", "familyStat")
            stat_layout = QHBoxLayout(stat_widget)
            stat_layout.setContentsMargins(0, 0, 0, 0)
            stat_layout.setSpacing(theme.spacing_xs)
            icon_label = QLabel()
            icon_label.setPixmap(create_ui_pixmap(icon_name, color="#2b8b4b", size=17))
            stat_layout.addWidget(icon_label)
            text_column = QVBoxLayout()
            text_column.setContentsMargins(0, 0, 0, 0)
            text_column.setSpacing(0)
            caption = QLabel(label)
            caption.setProperty("tanukiRole", "familyStatCaption")
            text_column.addWidget(caption)
            value_label = QLabel("--")
            value_label.setProperty("tanukiRole", "familyStatValue")
            text_column.addWidget(value_label)
            stat_layout.addLayout(text_column)
            stats_layout.addWidget(stat_widget, stretch=1)
            self.stat_value_labels[key] = value_label

        self.achievement_slot = QFrame()
        self.achievement_slot.setObjectName("tanukiAchievementSummarySlot")
        self.achievement_slot.setProperty("tanukiRole", "familyAchievementSlot")
        self.achievement_slot.setAccessibleName("成就摘要；尚未啟用")
        self.achievement_slot.setToolTip(
            "成就規則與資料格式確定後，將由此區塊顯示正式摘要。"
        )
        self.achievement_slot.setEnabled(False)
        achievement_layout = QHBoxLayout(self.achievement_slot)
        achievement_layout.setContentsMargins(0, 0, 0, 0)
        achievement_layout.setSpacing(theme.spacing_xs)
        self.achievement_icon_label = QLabel()
        self.achievement_icon_label.setPixmap(
            create_ui_pixmap("achievement", color="#8d8a78", size=18)
        )
        achievement_layout.addWidget(self.achievement_icon_label)
        achievement_text_column = QVBoxLayout()
        achievement_text_column.setContentsMargins(0, 0, 0, 0)
        achievement_text_column.setSpacing(0)
        achievement_caption = QLabel("成就摘要")
        achievement_caption.setProperty("tanukiRole", "familyStatCaption")
        achievement_text_column.addWidget(achievement_caption)
        self.achievement_status_label = QLabel("尚未啟用")
        self.achievement_status_label.setProperty(
            "tanukiRole",
            "familyAchievementStatus",
        )
        achievement_text_column.addWidget(self.achievement_status_label)
        achievement_layout.addLayout(achievement_text_column)
        stats_layout.addWidget(self.achievement_slot, stretch=1)

        # The family character deliberately occupies the lower-right scene area.
        # Keep live statistics inside the unobstructed portion of the panel.
        stats_layout.addSpacing(210)
        root_layout.addWidget(self.stats_frame)

        self.set_binding(binding)

    def set_binding(self, binding):
        self.binding = binding
        connected = binding is not None
        self.unavailable_label.setVisible(not connected)
        if connected:
            self.refresh_from_binding()
        else:
            self.apply_presentation(None)
        self._update_donation_state()

    def showEvent(self, event):
        super().showEvent(event)
        if self.binding is not None:
            self.rhythm_refresh_timer.start()
            self.refresh_from_binding()

    def hideEvent(self, event):
        self.rhythm_refresh_timer.stop()
        super().hideEvent(event)

    def refresh_from_binding(self):
        if self.binding is None:
            return
        self.apply_presentation(self.binding.presentation())

    def refresh_rhythm_from_binding(self):
        if self.binding is None:
            return
        provider = getattr(self.binding, "rhythm_presentation", None)
        presentation = (
            provider()
            if callable(provider) else
            self.binding.presentation()
        )
        self.apply_rhythm_presentation(presentation)

    def apply_rhythm_presentation(self, presentation):
        if presentation is None:
            return
        members = tuple(getattr(presentation, "members", ()) or ())
        member_names = {
            str(member.character_name or "")
            for member in members
        }
        if member_names != set(self.member_cards):
            # Character roster changes are rare and do require a structural
            # refresh. Ordinary one-second ticks never enter this path.
            self.refresh_from_binding()
            return
        race_text = str(
            getattr(presentation, "race_rhythm_text", "") or ""
        )
        if self.race_rhythm_label.text() != race_text:
            self.race_rhythm_label.setText(race_text)
        for member in members:
            card = self.member_cards.get(member.character_name)
            if card is not None:
                card.apply_live_member(member)

    def apply_presentation(self, presentation):
        if presentation is None:
            self.title_label.setText("家庭狀態")
            self.race_rhythm_label.setText("")
            self.fund_value_label.setText("--")
            self.pressure_value_label.setText("--")
            self.pressure_level_label.setText("--")
            self.pressure_bar.setValue(0)
            self.summon_value_label.setText("0 / 0")
            self.summon_hint_label.setText("尚無成員")
            self._replace_member_cards(())
            self._populate_recent_events(())
            self._apply_stats(None)
            self._update_donation_state()
            return

        self.title_label.setText(presentation.title or "家庭狀態")
        self.race_rhythm_label.setText(
            getattr(presentation, "race_rhythm_text", "") or ""
        )
        living_fund = presentation.living_fund
        pressure = presentation.household_pressure
        self.fund_value_label.setText(
            f"{living_fund:,} 元" if living_fund is not None else "--"
        )
        if pressure is None:
            self.pressure_value_label.setText("--")
            self.pressure_level_label.setText("--")
            self.pressure_bar.setValue(0)
        else:
            pressure_value = max(0, min(100, int(round(pressure))))
            self.pressure_value_label.setText(f"{pressure_value}%")
            self.pressure_level_label.setText(self._pressure_label(pressure_value))
            self.pressure_bar.setValue(pressure_value)

        self.summon_value_label.setText(
            f"{presentation.summoned_count} / {presentation.member_count}"
        )
        standby_count = max(
            0,
            presentation.member_count - presentation.summoned_count,
        )
        self.summon_hint_label.setText(
            f"待命 {standby_count} 人"
            if presentation.member_count else
            "尚無成員"
        )
        self.member_count_label.setText(f"{presentation.member_count} 人")
        self._sync_member_cards(presentation.members)
        self._populate_recent_events(presentation.recent_events)
        self._apply_stats(presentation)
        self._update_donation_state()

    def _handle_donate(self):
        if self.binding is None:
            return
        donate = getattr(self.binding, "donate_fund", None)
        if not callable(donate):
            return
        donate(100)
        self.refresh_from_binding()

    def _update_donation_state(self):
        can_donate = False
        if self.binding is not None:
            capability = getattr(
                self.binding,
                "can_donate_fund",
                None,
            )
            can_donate = bool(capability()) if callable(capability) else False
        self.donate_button.setEnabled(can_donate)
        self.donate_button.setToolTip(
            "捐入 100 元生活費"
            if can_donate
            else "只有黃金傳說模式可以捐生活費"
        )

    def _replace_member_cards(self, members):
        while self.members_row.count():
            item = self.members_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.member_cards = {}
        if not members:
            self.members_stack.setCurrentWidget(self.members_empty_label)
            return

        for member in members:
            card = FamilyMemberCard(
                member,
                avatar_pixmap=self.avatar_pixmaps.get(member.character_name),
            )
            self.members_row.addWidget(card)
            self.member_cards[member.character_name] = card
        self.members_row.addStretch(1)
        self.members_stack.setCurrentWidget(self.members_scroll)

    def _sync_member_cards(self, members):
        members = tuple(members or ())
        member_names = {
            str(member.character_name or "")
            for member in members
        }
        if member_names != set(self.member_cards):
            self._replace_member_cards(members)
            return
        for member in members:
            card = self.member_cards.get(member.character_name)
            if card is not None:
                card.apply_live_member(member)

    def _populate_recent_events(self, events):
        events = tuple(events or ())
        self.recent_event_table.clearContents()
        self.recent_event_table.setRowCount(len(events))
        for row, event in enumerate(events):
            values = (
                event.timestamp_text,
                event.channel_label,
                localize_character_names_in_text(event.summary)
                + (f"\n{event.delta_text}" if event.delta_text else ""),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                if column == 1:
                    color = EVENT_CHANNEL_COLORS.get(event.channel, "#2b8b4b")
                    item.setForeground(QColor(color))
                    item.setIcon(
                        create_ui_icon(
                            event.channel if event.channel in EVENT_CHANNEL_COLORS else "info",
                            color=color,
                            size=16,
                        )
                    )
                self.recent_event_table.setItem(row, column, item)
            self.recent_event_table.setRowHeight(row, 50)
        has_events = bool(events)
        self.recent_event_table.setVisible(has_events)
        self.events_empty_label.setVisible(not has_events)

    def _apply_stats(self, presentation):
        if presentation is None:
            values = {
                "average_mood": "--",
                "fund_delta": "--",
                "pressure_delta": "--",
                "event_count": "--",
            }
        else:
            values = {
                "average_mood": (
                    "--" if presentation.average_mood is None else
                    f"{presentation.average_mood:.0f} / 100"
                ),
                "fund_delta": f"{presentation.recent_fund_delta:+,d} 元",
                "pressure_delta": f"{presentation.recent_pressure_delta:+.1f}",
                "event_count": f"{presentation.recent_event_count} 件",
            }
        for key, value in values.items():
            self.stat_value_labels[key].setText(value)

    def _create_metric_card(self, icon_name, caption_text):
        card = QFrame()
        card.setProperty("tanukiRole", "familyCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(
            self.theme.spacing_md,
            self.theme.spacing_sm,
            self.theme.spacing_md,
            self.theme.spacing_sm,
        )
        layout.setSpacing(2)
        caption_row = QHBoxLayout()
        caption_row.setSpacing(self.theme.spacing_xs)
        icon_label = QLabel()
        icon_label.setPixmap(create_ui_pixmap(icon_name, color="#2b8b4b", size=18))
        caption_row.addWidget(icon_label)
        caption = QLabel(caption_text)
        caption.setProperty("tanukiRole", "familyCaption")
        caption_row.addWidget(caption)
        caption_row.addStretch(1)
        layout.addLayout(caption_row)
        return card, layout

    def _load_avatar_pixmaps(self, assets):
        if assets is None:
            return {}
        pixmaps = {}
        for avatar_spec in assets.avatar_specs:
            try:
                pixmaps[avatar_spec.character_name] = assets.load_avatar_pixmap(
                    avatar_spec
                )
            except (OSError, RuntimeError):
                continue
        return pixmaps

    @staticmethod
    def _pressure_label(value):
        if value >= 75:
            return "高度壓力"
        if value >= 40:
            return "中度壓力"
        return "低度壓力"
