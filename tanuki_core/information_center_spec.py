from dataclasses import dataclass

from .ui_skin_spec import (
    SKIN_EVENT_LOG,
    SKIN_FAMILY_STATUS,
    SKIN_RELATION_SUMMON,
    SKIN_STATUS_SETTINGS,
)


PAGE_RELATION_SUMMON = "relation_summon"
PAGE_EVENT_LOG = "event_log"
PAGE_FAMILY_STATUS = "family_status"
PAGE_STATUS_SETTINGS = "status_settings"
DEFAULT_INFORMATION_CENTER_PAGE = PAGE_FAMILY_STATUS


@dataclass(frozen=True)
class InformationCenterPageSpec:
    page_id: str
    navigation_label: str
    title: str
    placeholder_text: str
    skin_key: str


INFORMATION_CENTER_PAGE_SPECS = (
    InformationCenterPageSpec(
        page_id=PAGE_RELATION_SUMMON,
        navigation_label="角色關係＋召喚",
        title="角色關係＋召喚",
        placeholder_text="人物頭像、召喚控制與雙向關係資料將在此頁接入。",
        skin_key=SKIN_RELATION_SUMMON,
    ),
    InformationCenterPageSpec(
        page_id=PAGE_EVENT_LOG,
        navigation_label="事件日誌",
        title="事件日誌",
        placeholder_text="事件篩選、列表與詳細內容將在此頁接入。",
        skin_key=SKIN_EVENT_LOG,
    ),
    InformationCenterPageSpec(
        page_id=PAGE_FAMILY_STATUS,
        navigation_label="家庭摘要",
        title="家庭狀態摘要",
        placeholder_text="生活費、家庭壓力、成員卡片與近期事件將在此頁接入。",
        skin_key=SKIN_FAMILY_STATUS,
    ),
    InformationCenterPageSpec(
        page_id=PAGE_STATUS_SETTINGS,
        navigation_label="狀態設定",
        title="狀態設定",
        placeholder_text="一般設定、社交冷卻與進階開發工具將在此頁接入。",
        skin_key=SKIN_STATUS_SETTINGS,
    ),
)

INFORMATION_CENTER_PAGE_BY_ID = {
    page_spec.page_id: page_spec
    for page_spec in INFORMATION_CENTER_PAGE_SPECS
}


def get_information_center_page_spec(page_id):
    normalized_page_id = str(page_id or DEFAULT_INFORMATION_CENTER_PAGE)
    try:
        return INFORMATION_CENTER_PAGE_BY_ID[normalized_page_id]
    except KeyError as exc:
        raise ValueError(f"unknown information center page: {normalized_page_id}") from exc
