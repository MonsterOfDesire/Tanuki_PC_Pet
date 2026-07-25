from dataclasses import dataclass

from .ui_icons import METRIC_COLORS


@dataclass(frozen=True)
class UiThemeTokens:
    font_family: str = "Microsoft JhengHei UI"
    text_primary: str = "#2f2924"
    text_inverse: str = "#fffaf2"
    accent: str = "#c76742"
    accent_hover: str = "#dc7b53"
    focus: str = "#e4b75f"
    relation_accent: str = "#4d8fc7"
    event_accent: str = "#28755b"
    family_accent: str = "#69a45d"
    settings_accent: str = "#76559a"
    offer_accent: str = "#d9a928"
    danger: str = "#a34f45"
    border: str = "rgba(54, 44, 36, 170)"
    paper_surface: str = "rgba(255, 253, 247, 244)"
    frosted_surface: str = "rgba(255, 248, 232, 224)"
    glass_surface: str = "rgba(250, 246, 231, 214)"
    chalkboard_surface: str = "rgba(10, 83, 61, 224)"
    dark_surface: str = "rgba(18, 20, 27, 230)"
    radius_small: int = 6
    radius_medium: int = 10
    radius_large: int = 16
    spacing_xs: int = 4
    spacing_sm: int = 8
    spacing_md: int = 12
    spacing_lg: int = 18
    control_height: int = 36
    navigation_height: int = 46


DEFAULT_UI_THEME = UiThemeTokens()


def build_ui_stylesheet(tokens=DEFAULT_UI_THEME):
    return f"""
    QWidget {{
        font-family: "{tokens.font_family}";
        color: {tokens.text_primary};
    }}
    QFrame#tanukiSkinContentSurface {{
        border: 1px solid {tokens.border};
        border-radius: {tokens.radius_large}px;
    }}
    QFrame#tanukiSceneViewport {{
        background: transparent;
        border: none;
    }}
    QFrame#tanukiSkinOcclusionSurface[occlusionRole="whiteboard"] {{
        background: #ffffff;
        border: none;
        border-radius: 0;
    }}
    QFrame#tanukiSkinContentSurface[surfaceRole="paper"] {{
        background: {tokens.paper_surface};
    }}
    QFrame#tanukiSkinContentSurface[surfaceRole="whiteboard_content"] {{
        background: transparent;
        border: none;
        border-radius: 0;
    }}
    QFrame#tanukiSkinContentSurface[surfaceRole="frosted"] {{
        background: {tokens.frosted_surface};
    }}
    QFrame#tanukiSkinContentSurface[surfaceRole="glass"] {{
        background: {tokens.glass_surface};
    }}
    QWidget#tanukiOfferTray {{
        background: #fffdf7;
        border: 1px solid rgba(82, 59, 34, 175);
        border-radius: {tokens.radius_large}px;
    }}
    QFrame#tanukiDietChromeDragZone {{
        background: transparent;
        border: none;
    }}
    QFrame#tanukiWindowChromeControls {{
        background: rgba(39, 33, 29, 185);
        border: 1px solid rgba(245, 221, 172, 105);
        border-radius: {tokens.radius_medium}px;
    }}
    QFrame#tanukiWindowChromeControls[chromeVariant="light"] {{
        background: rgba(255, 225, 60, 220);
        border-color: rgba(79, 62, 21, 155);
    }}
    QToolButton[tanukiRole="chromeButton"] {{
        background: transparent;
        border: 1px solid transparent;
        border-radius: {tokens.radius_small}px;
    }}
    QToolButton[tanukiRole="chromeButton"]:hover {{
        background: rgba(255, 255, 255, 35);
        border-color: rgba(245, 221, 172, 105);
    }}
    QToolButton[tanukiRole="chromeButton"][chromeVariant="light"]:hover {{
        background: rgba(255, 255, 255, 100);
        border-color: rgba(79, 62, 21, 125);
    }}
    QToolButton[tanukiRole="chromeButton"]:checked {{
        background: {tokens.accent};
        border-color: {tokens.focus};
    }}
    QToolButton[tanukiRole="chromeButton"][chromeAction="close"]:hover {{
        background: {tokens.danger};
        border-color: {tokens.focus};
    }}
    QFrame[tanukiRole="offerItemBadge"] {{
        min-width: 54px;
        background: rgba(255, 253, 247, 225);
        border: 1px dashed rgba(145, 103, 52, 115);
        border-radius: {tokens.radius_medium}px;
    }}
    QFrame[tanukiRole="offerItemBadge"]:hover {{
        background: rgba(255, 244, 196, 242);
        border-color: {tokens.offer_accent};
    }}
    QLabel[tanukiRole="offerItemName"] {{
        color: #271d16;
        font-size: 13px;
        font-weight: 800;
    }}
    QLabel[tanukiRole="offerInstruction"] {{
        color: #fffaf2;
        background: rgba(126, 92, 24, 226);
        border: 1px solid {tokens.offer_accent};
        border-radius: {tokens.radius_medium}px;
        padding: {tokens.spacing_xs}px {tokens.spacing_md}px;
        font-size: 13px;
        font-weight: 800;
    }}
    QFrame#tanukiSkinContentSurface[surfaceRole="chalkboard"] {{
        background: {tokens.chalkboard_surface};
        color: {tokens.text_inverse};
        border-color: rgba(236, 223, 185, 190);
    }}
    QFrame#tanukiSkinContentSurface[surfaceRole="dark"] {{
        background: {tokens.dark_surface};
        color: {tokens.text_inverse};
        border-color: rgba(245, 221, 172, 180);
    }}
    QWidget#tanukiInformationCenter {{
        background: #211d1a;
        border: 1px solid rgba(245, 221, 172, 115);
        border-radius: {tokens.radius_medium}px;
    }}
    QFrame#tanukiInformationNavigation {{
        min-height: {tokens.navigation_height}px;
        background: rgba(33, 29, 26, 248);
        border-bottom: 1px solid rgba(245, 221, 172, 120);
        border-top-left-radius: {tokens.radius_medium}px;
        border-top-right-radius: {tokens.radius_medium}px;
    }}
    QLabel[tanukiRole="navigationTitle"] {{
        color: {tokens.text_inverse};
        font-size: 16px;
        font-weight: 700;
    }}
    QPushButton[tanukiRole="navigation"] {{
        min-height: {tokens.control_height}px;
        padding: 0 {tokens.spacing_md}px;
        color: rgba(255, 250, 242, 210);
        background: transparent;
        border: 1px solid transparent;
        border-radius: {tokens.radius_medium}px;
    }}
    QPushButton[tanukiRole="navigation"]:hover {{
        background: rgba(255, 255, 255, 22);
        border-color: rgba(245, 221, 172, 90);
    }}
    QPushButton[tanukiRole="navigation"]:checked {{
        color: {tokens.text_inverse};
        background: {tokens.accent};
        border-color: {tokens.focus};
        font-weight: 700;
    }}
    QPushButton[tanukiRole="navigation"][pageAccent="relation_summon"]:checked {{
        background: #376f9e;
        border-color: {tokens.relation_accent};
    }}
    QPushButton[tanukiRole="navigation"][pageAccent="event_log"]:checked {{
        background: {tokens.event_accent};
        border-color: #68b99a;
    }}
    QPushButton[tanukiRole="navigation"][pageAccent="family_status"]:checked {{
        background: #4f8449;
        border-color: {tokens.family_accent};
    }}
    QPushButton[tanukiRole="navigation"][pageAccent="status_settings"]:checked {{
        background: {tokens.settings_accent};
        border-color: #b59bd0;
    }}
    QToolButton[tanukiRole="windowSize"],
    QToolButton[tanukiRole="windowAction"] {{
        min-height: {tokens.control_height}px;
        padding: 0 {tokens.spacing_md}px;
        color: rgba(255, 250, 242, 220);
        background: rgba(255, 255, 255, 14);
        border: 1px solid rgba(245, 221, 172, 90);
        border-radius: {tokens.radius_medium}px;
    }}
    QToolButton[tanukiRole="windowSize"]:hover,
    QToolButton[tanukiRole="windowSize"]:open,
    QToolButton[tanukiRole="windowAction"]:hover {{
        background: rgba(255, 255, 255, 28);
        border-color: {tokens.focus};
    }}
    QToolButton[tanukiRole="windowAction"]:disabled {{
        color: rgba(255, 250, 242, 95);
        background: rgba(255, 255, 255, 7);
        border-color: rgba(245, 221, 172, 35);
    }}
    QPushButton[tanukiRole="navigation"][detached="true"] {{
        color: {tokens.focus};
        border-color: rgba(245, 221, 172, 110);
    }}
    QMenu {{
        color: {tokens.text_inverse};
        background: rgba(33, 29, 26, 252);
        border: 1px solid rgba(245, 221, 172, 120);
        padding: {tokens.spacing_xs}px;
    }}
    QMenu::item {{
        padding: {tokens.spacing_sm}px {tokens.spacing_lg}px;
        border-radius: {tokens.radius_small}px;
    }}
    QMenu::item:selected {{
        background: {tokens.accent};
    }}
    QScrollBar:vertical {{
        width: 7px;
        margin: 1px;
        background: transparent;
        border: none;
    }}
    QScrollBar:horizontal {{
        height: 7px;
        margin: 1px;
        background: transparent;
        border: none;
    }}
    QScrollBar::handle:vertical,
    QScrollBar::handle:horizontal {{
        min-height: 22px;
        min-width: 22px;
        background: rgba(126, 104, 86, 78);
        border-radius: 3px;
    }}
    QScrollBar::handle:vertical:hover,
    QScrollBar::handle:horizontal:hover {{
        background: rgba(126, 104, 86, 135);
    }}
    QScrollBar::add-line,
    QScrollBar::sub-line {{
        width: 0;
        height: 0;
        background: transparent;
        border: none;
    }}
    QScrollBar::add-page,
    QScrollBar::sub-page {{
        background: transparent;
    }}
    QLabel[tanukiRole="pageHeading"] {{
        font-size: 22px;
        font-weight: 700;
    }}
    QLabel[tanukiRole="pagePlaceholder"] {{
        font-size: 14px;
    }}
    QLabel[tanukiRole="settingsNotice"],
    QLabel[tanukiRole="settingsLabel"] {{
        color: {tokens.text_inverse};
    }}
    QGroupBox[tanukiRole="settingsGroup"] {{
        color: {tokens.text_inverse};
        font-weight: 700;
        border: 1px solid rgba(181, 155, 208, 115);
        border-radius: {tokens.radius_medium}px;
        margin-top: {tokens.spacing_sm}px;
        padding: {tokens.spacing_sm}px;
        background: rgba(0, 0, 0, 45);
    }}
    QGroupBox[tanukiRole="settingsGroup"]::title {{
        subcontrol-origin: margin;
        left: {tokens.spacing_md}px;
        padding: 0 {tokens.spacing_xs}px;
    }}
    QPushButton[tanukiRole="settingsOption"] {{
        min-width: 38px;
        min-height: 28px;
        padding: 0 {tokens.spacing_sm}px;
        color: rgba(255, 250, 242, 220);
        background: rgba(255, 255, 255, 18);
        border: 1px solid rgba(181, 155, 208, 90);
        border-radius: {tokens.radius_small}px;
    }}
    QPushButton[tanukiRole="settingsOption"][compact="true"] {{
        min-width: 28px;
        padding: 0 {tokens.spacing_xs}px;
    }}
    QPushButton[tanukiRole="settingsOption"]:checked {{
        color: {tokens.text_inverse};
        background: {tokens.settings_accent};
        border-color: #b59bd0;
        font-weight: 700;
    }}
    QPushButton[tanukiRole="settingsAction"] {{
        min-height: 30px;
        padding: 0 {tokens.spacing_md}px;
        color: {tokens.text_inverse};
        background: rgba(255, 255, 255, 18);
        border: 1px solid rgba(181, 155, 208, 115);
        border-radius: {tokens.radius_small}px;
    }}
    QPushButton[tanukiRole="settingsAction"]:hover {{
        background: {tokens.settings_accent};
        border-color: #b59bd0;
    }}
    QCheckBox[tanukiRole="settingsToggle"] {{
        color: {tokens.text_inverse};
        spacing: {tokens.spacing_sm}px;
    }}
    QLabel[tanukiRole="settingsToggleLabel"] {{
        color: {tokens.text_inverse};
        font-weight: 650;
    }}
    QFrame[tanukiRole="launcherSurface"] {{
        color: {tokens.text_inverse};
        background: rgba(33, 29, 26, 249);
        border: 2px solid rgba(228, 183, 95, 215);
        border-radius: 22px;
    }}
    QLabel[tanukiRole="launcherTitle"] {{
        color: {tokens.text_inverse};
        font-size: 18px;
        font-weight: 800;
    }}
    QLabel[tanukiRole="launcherSubtitle"] {{
        color: rgba(255, 250, 242, 145);
        font-size: 11px;
        font-weight: 600;
    }}
    QLabel[tanukiRole="launcherSection"] {{
        color: rgba(229, 215, 194, 210);
        font-size: 11px;
        font-weight: 800;
    }}
    QToolButton[tanukiRole="launcherChrome"] {{
        min-width: 28px;
        min-height: 28px;
        color: rgba(255, 250, 242, 210);
        background: transparent;
        border: 1px solid transparent;
        border-radius: {tokens.radius_small}px;
        font-size: 20px;
        font-weight: 800;
    }}
    QToolButton[tanukiRole="launcherChrome"]:hover,
    QToolButton[tanukiRole="launcherChrome"]:checked {{
        color: {tokens.focus};
        background: rgba(255, 255, 255, 24);
        border-color: rgba(242, 191, 93, 100);
    }}
    QToolButton[tanukiRole="launcherTile"] {{
        padding: {tokens.spacing_sm}px;
        color: {tokens.text_inverse};
        background: rgba(255, 255, 255, 22);
        border: 1px solid rgba(245, 221, 172, 100);
        border-radius: {tokens.radius_large}px;
        font-size: 14px;
        font-weight: 800;
    }}
    QToolButton[tanukiRole="launcherTile"]:hover {{
        background: rgba(255, 255, 255, 38);
        border-color: {tokens.focus};
    }}
    QToolButton[tanukiRole="launcherTile"][primary="true"] {{
        background: {tokens.accent};
        border: 2px solid {tokens.focus};
    }}
    QToolButton[tanukiRole="launcherTile"][primary="true"]:hover {{
        background: {tokens.accent_hover};
    }}
    QFrame[tanukiRole="launcherStatusPanel"] {{
        background: rgba(10, 9, 8, 150);
        border: 1px solid rgba(245, 221, 172, 70);
        border-radius: {tokens.radius_medium}px;
    }}
    QLabel[tanukiRole="launcherStatusChip"] {{
        min-height: 30px;
        padding: 0 {tokens.spacing_xs}px;
        color: rgba(255, 250, 242, 220);
        background: rgba(88, 72, 58, 210);
        border: 1px solid transparent;
        border-radius: 15px;
        font-size: 11px;
        font-weight: 700;
    }}
    QLabel[tanukiRole="launcherStatusChip"][statusState="world"] {{
        color: #fff1cc;
    }}
    QLabel[tanukiRole="launcherStatusChip"][statusState="enabled"] {{
        color: #dff6d8;
        background: rgba(55, 83, 53, 220);
    }}
    QLabel[tanukiRole="launcherStatusChip"][statusState="disabled"] {{
        color: rgba(255, 250, 242, 145);
        background: rgba(77, 69, 62, 210);
    }}
    QPushButton[tanukiRole="launcherAction"],
    QPushButton[tanukiRole="launcherShutdown"] {{
        min-height: 48px;
        padding: 0 {tokens.spacing_md}px;
        color: {tokens.text_inverse};
        background: rgba(255, 255, 255, 18);
        border: 1px solid rgba(245, 221, 172, 95);
        border-radius: {tokens.radius_medium}px;
        font-size: 14px;
        font-weight: 800;
        text-align: left;
    }}
    QPushButton[tanukiRole="launcherAction"]:hover {{
        background: rgba(255, 255, 255, 34);
        border-color: {tokens.focus};
    }}
    QPushButton[tanukiRole="launcherShutdown"] {{
        background: rgba(28, 25, 22, 225);
    }}
    QPushButton[tanukiRole="launcherShutdown"]:hover {{
        background: {tokens.danger};
        border-color: {tokens.focus};
    }}
    QToolButton[tanukiRole="launcherRailAction"] {{
        color: {tokens.text_inverse};
        background: rgba(255, 255, 255, 18);
        border: 1px solid rgba(245, 221, 172, 85);
        border-radius: {tokens.radius_medium}px;
        font-size: 26px;
        font-weight: 800;
    }}
    QToolButton[tanukiRole="launcherRailAction"]:hover {{
        background: rgba(255, 255, 255, 36);
        border-color: {tokens.focus};
    }}
    QToolButton[tanukiRole="launcherRailAction"][primary="true"] {{
        background: {tokens.accent};
        border-color: {tokens.focus};
    }}
    QLabel[tanukiRole="launcherRailStatus"] {{
        min-height: 58px;
        color: rgba(255, 250, 242, 200);
        background: transparent;
        font-size: 11px;
    }}
    QLabel[tanukiRole="launcherNotice"] {{
        padding: {tokens.spacing_sm}px;
        color: #fff1cc;
        background: rgba(91, 69, 42, 205);
        border: 1px solid rgba(242, 191, 93, 105);
        border-radius: {tokens.radius_small}px;
        font-size: 12px;
        font-weight: 700;
    }}
    QLabel[tanukiRole="familyHeading"] {{
        color: {tokens.text_primary};
        font-size: 20px;
        font-weight: 700;
    }}
    QLabel[tanukiRole="familyNotice"],
    QLabel[tanukiRole="familyCaption"],
    QLabel[tanukiRole="familySection"] {{
        color: {tokens.text_primary};
        font-weight: 700;
    }}
    QLabel[tanukiRole="familyValue"] {{
        color: #477d3e;
        font-size: 20px;
        font-weight: 700;
    }}
    QPushButton[tanukiRole="familyAction"] {{
        min-height: 28px;
        padding: 0 {tokens.spacing_sm}px;
        color: {tokens.text_primary};
        background: rgba(224, 242, 211, 210);
        border: 1px solid rgba(105, 164, 93, 135);
        border-radius: {tokens.radius_small}px;
        font-weight: 800;
    }}
    QPushButton[tanukiRole="familyAction"]:hover {{
        background: rgba(205, 233, 187, 235);
        border-color: {tokens.family_accent};
    }}
    QPushButton[tanukiRole="familyAction"]:disabled {{
        color: rgba(47, 41, 36, 90);
        background: rgba(92, 72, 55, 25);
        border-color: rgba(92, 72, 55, 45);
    }}
    QFrame[tanukiRole="familyCard"] {{
        background: rgba(255, 253, 247, 205);
        border: 1px solid rgba(92, 72, 55, 100);
        border-radius: {tokens.radius_medium}px;
    }}
    QLabel[tanukiRole="familyMetricHint"],
    QLabel[tanukiRole="familySectionCount"] {{
        color: rgba(47, 41, 36, 155);
        font-size: 11px;
        font-weight: 700;
    }}
    QProgressBar[tanukiRole="familyPressure"] {{
        min-height: 10px;
        max-height: 10px;
        background: rgba(69, 57, 47, 45);
        border: none;
        border-radius: 5px;
    }}
    QProgressBar[tanukiRole="familyPressure"]::chunk {{
        background: {tokens.family_accent};
        border-radius: 5px;
    }}
    QPlainTextEdit[tanukiRole="familyLog"] {{
        color: {tokens.text_primary};
        background: rgba(255, 253, 247, 220);
        border: 1px solid rgba(92, 72, 55, 100);
        border-radius: {tokens.radius_medium}px;
        padding: {tokens.spacing_sm}px;
    }}
    QFrame[tanukiRole="familySectionCard"] {{
        background: rgba(255, 253, 247, 195);
        border: 1px solid rgba(92, 72, 55, 85);
        border-radius: {tokens.radius_medium}px;
    }}
    QScrollArea[tanukiRole="familyMembersScroll"],
    QScrollArea[tanukiRole="familyMembersScroll"] > QWidget > QWidget,
    QWidget[tanukiRole="familyMembersContent"] {{
        background: transparent;
        border: none;
    }}
    QFrame[tanukiRole="familyMemberCard"] {{
        background: rgba(255, 253, 247, 212);
        border: 1px solid rgba(92, 72, 55, 78);
        border-radius: {tokens.radius_medium}px;
    }}
    QFrame[tanukiRole="familyMemberCard"][summoned="true"] {{
        background: rgba(239, 250, 231, 224);
        border-color: {tokens.family_accent};
    }}
    QLabel[tanukiRole="familyAvatar"] {{
        background: rgba(255, 255, 255, 165);
        border: 1px solid rgba(105, 164, 93, 105);
        border-radius: 25px;
    }}
    QLabel[tanukiRole="familyMemberName"] {{
        color: {tokens.text_primary};
        font-size: 11px;
        font-weight: 800;
    }}
    QProgressBar[tanukiRole="familyMood"] {{
        min-height: 6px;
        max-height: 6px;
        background: rgba(92, 72, 55, 35);
        border: none;
        border-radius: 3px;
    }}
    QProgressBar[tanukiRole="familyMood"]::chunk {{
        background: #8a938c;
        border-radius: 3px;
    }}
    QProgressBar[tanukiRole="familyMood"][moodBand="normal"]::chunk {{
        background: #4eaa65;
    }}
    QProgressBar[tanukiRole="familyMood"][moodBand="unhappy"]::chunk {{
        background: #dfa72d;
    }}
    QProgressBar[tanukiRole="familyMood"][moodBand="depressed"]::chunk {{
        background: #4f83b7;
    }}
    QLabel[tanukiRole="familyMoodValue"] {{
        color: rgba(47, 41, 36, 185);
        font-size: 10px;
        font-weight: 800;
    }}
    QLabel[tanukiRole="familySummonStatus"] {{
        color: rgba(92, 72, 55, 165);
        font-size: 10px;
        font-weight: 700;
    }}
    QLabel[tanukiRole="familySummonStatus"][summoned="true"] {{
        color: #477d3e;
    }}
    QTableWidget[tanukiRole="familyEvents"] {{
        color: {tokens.text_primary};
        background: transparent;
        border: none;
        outline: none;
        font-size: 11px;
    }}
    QTableWidget[tanukiRole="familyEvents"]::item {{
        background: rgba(255, 255, 255, 85);
        border: none;
        border-bottom: 1px solid rgba(92, 72, 55, 40);
        padding: {tokens.spacing_xs}px;
    }}
    QLabel[tanukiRole="familyEmpty"] {{
        color: rgba(47, 41, 36, 145);
        padding: {tokens.spacing_sm}px;
    }}
    QFrame[tanukiRole="familyStats"] {{
        background: rgba(255, 253, 247, 205);
        border: 1px solid rgba(92, 72, 55, 78);
        border-radius: {tokens.radius_medium}px;
    }}
    QWidget[tanukiRole="familyStat"] {{
        background: transparent;
        border: none;
    }}
    QLabel[tanukiRole="familyStatCaption"] {{
        color: rgba(47, 41, 36, 145);
        font-size: 10px;
        font-weight: 700;
    }}
    QLabel[tanukiRole="familyStatValue"] {{
        color: #477d3e;
        font-size: 12px;
        font-weight: 800;
    }}
    QFrame#tanukiAchievementSummarySlot {{
        background: transparent;
        border: none;
    }}
    QLabel[tanukiRole="familyAchievementStatus"] {{
        color: rgba(92, 72, 55, 125);
        font-size: 11px;
        font-weight: 700;
    }}
    QLabel[tanukiRole="eventHeading"] {{
        color: {tokens.text_inverse};
        font-size: 20px;
        font-weight: 700;
    }}
    QLabel[tanukiRole="eventNotice"],
    QLabel[tanukiRole="eventLabel"] {{
        color: {tokens.text_inverse};
        font-weight: 700;
    }}
    QPushButton[tanukiRole="eventFilter"] {{
        min-width: 44px;
        min-height: 28px;
        padding: 0 {tokens.spacing_sm}px;
        color: rgba(255, 250, 242, 220);
        background: rgba(0, 0, 0, 30);
        border: 1px solid rgba(236, 223, 185, 130);
        border-radius: {tokens.radius_small}px;
    }}
    QPushButton[tanukiRole="eventFilter"]:checked {{
        color: {tokens.text_inverse};
        background: #3b8f70;
        border-color: #76c7a7;
        font-weight: 700;
    }}
    QComboBox[tanukiRole="eventParticipant"] {{
        min-height: 28px;
        color: {tokens.text_inverse};
        background: rgba(0, 0, 0, 55);
        border: 1px solid rgba(236, 223, 185, 130);
        border-radius: {tokens.radius_small}px;
        padding: 0 {tokens.spacing_sm}px;
    }}
    QComboBox[tanukiRole="eventParticipant"][personalActive="false"] {{
        color: rgba(255, 250, 242, 55);
        background: rgba(0, 0, 0, 12);
        border-color: rgba(236, 223, 185, 35);
    }}
    QComboBox[tanukiRole="eventParticipant"][personalActive="false"]::drop-down {{
        width: 14px;
        border: none;
        background: transparent;
    }}
    QLabel[tanukiRole="eventLabel"][personalActive="false"] {{
        background: transparent;
        border: none;
    }}
    QPlainTextEdit[tanukiRole="eventLog"] {{
        color: {tokens.text_inverse};
        background: rgba(3, 35, 27, 205);
        border: 1px solid rgba(236, 223, 185, 155);
        border-radius: {tokens.radius_medium}px;
        padding: {tokens.spacing_sm}px;
    }}
    QSplitter#tanukiEventSplitter::handle {{
        background: rgba(236, 223, 185, 75);
        border-radius: 2px;
        margin: {tokens.spacing_sm}px 1px;
    }}
    QFrame[tanukiRole="eventPane"] {{
        background: rgba(3, 45, 34, 165);
        border: 1px solid rgba(236, 223, 185, 125);
        border-radius: {tokens.radius_medium}px;
    }}
    QTableWidget[tanukiRole="eventList"] {{
        color: {tokens.text_inverse};
        background: transparent;
        alternate-background-color: transparent;
        gridline-color: rgba(236, 223, 185, 42);
        border: none;
        border-radius: {tokens.radius_medium}px;
        outline: none;
        font-size: 13px;
    }}
    QTableWidget[tanukiRole="eventList"]::item {{
        border: none;
        padding: {tokens.spacing_xs}px {tokens.spacing_sm}px;
    }}
    QTableWidget[tanukiRole="eventList"]::item:hover {{
        background: rgba(255, 255, 255, 22);
    }}
    QTableWidget[tanukiRole="eventList"]::item:selected {{
        color: {tokens.text_inverse};
        background: rgba(40, 117, 91, 205);
    }}
    QLabel[tanukiRole="eventEmpty"] {{
        color: rgba(255, 250, 242, 165);
        padding: {tokens.spacing_lg}px;
    }}
    QScrollArea[tanukiRole="eventDetailScroll"],
    QScrollArea[tanukiRole="eventDetailScroll"] > QWidget > QWidget,
    QWidget[tanukiRole="eventDetail"] {{
        background: transparent;
        border: none;
    }}
    QLabel[tanukiRole="eventDetailHeading"] {{
        color: {tokens.text_inverse};
        font-size: 18px;
        font-weight: 800;
    }}
    QLabel[tanukiRole="eventDetailTime"] {{
        color: rgba(255, 250, 242, 170);
        font-size: 13px;
        font-weight: 700;
    }}
    QLabel[tanukiRole="eventDetailSummary"] {{
        color: {tokens.text_inverse};
        font-size: 15px;
        font-weight: 700;
    }}
    QLabel[tanukiRole="eventParticipants"] {{
        color: #f4df9c;
        font-size: 14px;
        font-weight: 800;
        padding: {tokens.spacing_xs}px 0;
    }}
    QLabel[tanukiRole="eventChannelBadge"] {{
        color: #13251f;
        background: #e8dcae;
        border-radius: {tokens.radius_small}px;
        padding: 2px {tokens.spacing_sm}px;
        font-weight: 800;
    }}
    QLabel[tanukiRole="eventChannelBadge"][eventChannel="social"] {{
        background: #a8d47a;
    }}
    QLabel[tanukiRole="eventChannelBadge"][eventChannel="economy"] {{
        background: #75bcea;
    }}
    QLabel[tanukiRole="eventChannelBadge"][eventChannel="item"] {{
        background: #b89aea;
    }}
    QLabel[tanukiRole="eventChannelBadge"][eventChannel="story"] {{
        background: #e8b765;
    }}
    QLabel[tanukiRole="eventChannelBadge"][eventChannel="system"] {{
        background: #b8c9c3;
    }}
    QFrame[tanukiRole="eventSeparator"] {{
        color: rgba(236, 223, 185, 80);
        max-height: 1px;
    }}
    QFrame[tanukiRole="eventEffects"] {{
        background: rgba(0, 0, 0, 25);
        border: none;
        border-radius: {tokens.radius_small}px;
        padding: {tokens.spacing_sm}px;
    }}
    QLabel[tanukiRole="eventEffectLabel"] {{
        color: rgba(255, 250, 242, 205);
        font-weight: 700;
    }}
    QLabel[tanukiRole="eventEffectValue"] {{
        color: #f4df9c;
        font-weight: 800;
    }}
    QLabel[tanukiRole="eventEffectValue"][deltaTone="positive"] {{
        color: #a8d47a;
    }}
    QLabel[tanukiRole="eventEffectValue"][deltaTone="negative"] {{
        color: #f2a16f;
    }}
    QLabel[tanukiRole="eventEffectValue"][metricKind="familiarity"] {{
        color: {METRIC_COLORS["familiarity"]};
    }}
    QLabel[tanukiRole="eventEffectValue"][metricKind="trust"] {{
        color: {METRIC_COLORS["trust"]};
    }}
    QLabel[tanukiRole="eventEffectValue"][metricKind="attachment"] {{
        color: {METRIC_COLORS["attachment"]};
    }}
    QLabel[tanukiRole="eventEffectValue"][metricKind="tension"] {{
        color: {METRIC_COLORS["tension"]};
    }}
    QLabel[tanukiRole="eventNoEffects"],
    QLabel[tanukiRole="eventTags"],
    QLabel[tanukiRole="eventMetadata"] {{
        color: rgba(255, 250, 242, 165);
        font-size: 12px;
    }}
    QLabel[tanukiRole="relationNotice"] {{
        color: {tokens.text_primary};
        font-weight: 700;
    }}
    QFrame[tanukiRole="relationRoster"] {{
        background: rgba(255, 253, 247, 188);
        border: 1px solid rgba(92, 72, 55, 58);
        border-radius: {tokens.radius_medium}px;
    }}
    QFrame[tanukiRole="relationMemberRow"] {{
        background: transparent;
        border: none;
        border-bottom: 1px solid rgba(92, 72, 55, 35);
    }}
    QToolButton[tanukiRole="relationRosterAvatar"] {{
        background: rgba(255, 255, 255, 175);
        border: 1px solid rgba(92, 72, 55, 60);
        border-radius: 8px;
    }}
    QToolButton[tanukiRole="relationRosterAvatar"]:hover {{
        background: rgba(77, 143, 199, 72);
        border-color: rgba(77, 143, 199, 145);
    }}
    QToolButton[tanukiRole="relationRosterAvatar"]:checked {{
        background: rgba(77, 143, 199, 110);
        border: 2px solid {tokens.relation_accent};
    }}
    QLabel[tanukiRole="relationLegend"] {{
        color: rgba(47, 41, 36, 205);
        font-size: 17px;
        font-weight: 700;
    }}
    QLabel[tanukiRole="relationFormula"] {{
        color: #17120f;
        font-size: 12px;
        font-weight: 800;
    }}
    QListWidget[tanukiRole="relationList"] {{
        color: {tokens.text_primary};
        background: transparent;
        border: none;
        padding: 0;
    }}
    QListWidget[tanukiRole="relationList"]::item {{
        background: transparent;
        border: none;
        padding: 0;
    }}
    QFrame[tanukiRole="relationRowCard"] {{
        background: rgba(255, 253, 247, 218);
        border: 1px solid rgba(92, 72, 55, 68);
        border-radius: {tokens.radius_medium}px;
    }}
    QLabel[tanukiRole="relationMetricValue"] {{
        color: rgba(47, 41, 36, 185);
        font-size: 10px;
    }}
    QLabel[tanukiRole="relationAffinityValue"] {{
        color: #356f9e;
        font-size: 11px;
        font-weight: 800;
    }}
    QLabel[tanukiRole="relationEventCount"] {{
        color: #514842;
        font-size: 11px;
        font-weight: 800;
    }}
    QProgressBar[tanukiRole="relationMetric"] {{
        min-height: 5px;
        max-height: 5px;
        background: rgba(92, 72, 55, 35);
        border: none;
        border-radius: 2px;
    }}
    QProgressBar[tanukiRole="relationMetric"]::chunk {{
        border-radius: 2px;
    }}
    QProgressBar[tanukiRole="relationMetric"][metricKind="familiarity"]::chunk {{
        background: {METRIC_COLORS["familiarity"]};
    }}
    QProgressBar[tanukiRole="relationMetric"][metricKind="trust"]::chunk {{
        background: {METRIC_COLORS["trust"]};
    }}
    QProgressBar[tanukiRole="relationMetric"][metricKind="attachment"]::chunk {{
        background: {METRIC_COLORS["attachment"]};
    }}
    QProgressBar[tanukiRole="relationMetric"][metricKind="tension"]::chunk {{
        background: {METRIC_COLORS["tension"]};
    }}
    QFrame#tanukiSkinContentSurface[surfaceRole="chalkboard"] QLabel,
    QFrame#tanukiSkinContentSurface[surfaceRole="dark"] QLabel {{
        color: {tokens.text_inverse};
    }}
    QPushButton[tanukiRole="primary"] {{
        min-height: {tokens.control_height}px;
        padding: 0 {tokens.spacing_md}px;
        color: {tokens.text_inverse};
        background: {tokens.accent};
        border: 1px solid {tokens.border};
        border-radius: {tokens.radius_medium}px;
    }}
    QPushButton[tanukiRole="primary"]:hover {{
        background: {tokens.accent_hover};
    }}
    QPushButton:focus {{
        border: 2px solid {tokens.focus};
    }}
    """.strip()
