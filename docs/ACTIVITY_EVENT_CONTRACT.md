# Activity Event Contract

本文件定義供 Activity、成就與統計功能共用的 canonical gameplay metadata；它可以附在 household event，也可以只送往 tracker。正式家庭事件仍保留既有 `event_type`，避免破壞事件日誌與舊存檔；新消費者應優先讀取 `activity_event_name`。

## Canonical event names

| Activity | Canonical event name | 家庭事件／玩法接線 | 成就接線 |
|---|---|---|---|
| 魯道夫工作完成 | `activity.work.completed` | 寫入 `rudolf_work_completed` 經濟事件 | live；只更新黃金傳說工作成就 |
| 競賽完成 | `activity.race.completed` | 寫入 `race_completed` 社交事件與戰績 | live；目前只定義沙盒競賽成就 |
| 競賽婉拒 | `activity.race.declined` | 寫入 `race_declined` 社交事件 | live 消費並結束資格 session；不推進完成成就 |
| 合奏完成 | `activity.chorus.completed` | 寫入 `chorus_completed` 社交事件與自然完成收益 | live；目前只定義沙盒合奏成就 |
| 合奏中斷 | `activity.chorus.interrupted` | 寫入 `chorus_interrupted` 社交事件，不套用收益 | live 消費並結束資格 session；不推進完成成就 |
| 睡眠開始 | `activity.sleep.started` | 不寫家庭事件；開始時建立資格 token | live lifecycle；不作為可計數完成事件 |
| 睡眠完成 | `activity.sleep.completed` | gameplay-only，不寫家庭事件 | live；只接受自然完成，提早喚醒不計入 |
| 睡眠中斷 | `activity.sleep.interrupted` | 不寫家庭事件；直接取消資格 token | live lifecycle；不推進完成成就 |
| 加入睡眠群 | `activity.sleep.group_joined` | gameplay-only，不寫家庭事件 | live；資格從觀察／靠近嘗試開始計算 |
| 自主變身完成 | `activity.transformation.completed` | gameplay-only；既有變身故事事件維持原格式 | live；只計入自主進入 transformed 形態 |
| 照護完成 | `interaction.care.completed` | gameplay-only，不新增家庭日誌列 | live；包含照護者、對象、形態與淺眠喚醒旗標 |
| 蜂蜜保護完成 | `interaction.honey_guard.completed` | 沿用 `offer_honey_guarded` 家庭事件 | live；玩家供品互動來源 |
| 分享食物完成 | `interaction.food_share.completed` | 沿用既有分享食物家庭事件 | live；保存 holder、partner、consumer 與 outcome |

沙盒手動工作／競賽／合奏預覽不產生正式 Activity event。沙盒指定睡眠／喚醒只改變既有 Sleep Activity lifecycle，不建立成就 token，也不寫家庭事件；手動變身同樣不計入自主變身成就。

## Stable metadata

所有已接線的 Activity event metadata 具有以下欄位：

- `activity_event_schema_version`：目前為 `1`。
- `activity_event_name`、`activity_event_id`：canonical 名稱與冪等事件鍵。
- `activity_id`、`activity_kind`、`activity_phase`。
- `activity_source`、`activity_execution_mode`、`activity_world_mode`。
- `activity_started_at`、`activity_ended_at`、`activity_elapsed_seconds`。
- `activity_outcome`、`activity_reason`。
- `activity_participants`：`[{"name": ..., "role": ...}]`。

各 Activity 可附加自己的 typed details。競賽包含參賽形態、`race_course_key`、`race_nominal_meters`、實際 pixel 距離、方向、抵達與跑步用時，以及 `race_rewards`；工作包含 settlement key、完成比例與原始 Activity schema version。睡眠包含 trigger、group／anchor 與自然完成旗標；變身包含角色、來源與 target form；照護包含 caregiver／target、照護者形態與是否剛因 child distress 從睡眠醒來；供品互動包含角色職責、item／profile 及 outcome。

新增名稱時必須先加入 `KNOWN_ACTIVITY_EVENT_NAMES`，並補 payload contract 測試。成就 tracker 以 `activity_event_name + activity_event_id` 做事件分類與冪等，不依中文 summary 判斷。

## Live achievement consumption

- `AchievementRuntimeService` 以 Activity／session id 建立 eligibility token；`AchievementGameplayBridge` 負責睡眠、變身、照護、蜂蜜保護與分享食物的 gameplay lifecycle 轉換，避免把規則堆入 `app_runtime.py`。
- household event 寫入後，Runtime 將同一筆 canonical metadata 交給 tracker；家庭日誌文字不是成就輸入。
- token 記錄開始世界模式、來源與倍率。期間離開 1x 或切換世界模式後只會從 eligible 變成 ineligible，切回原值不恢復。
- 正常完成、婉拒或正式中斷事件會完成 token；沒有 canonical completion event 的拖曳、隱藏、提早喚醒、緊急中止、場景清除與 Runtime shutdown 會直接取消 token。
- 五名自然睡眠者的同時狀態使用去重 snapshot；只有五個對應睡眠 session 全都仍符合全程 1x／同世界模式資格時才能解鎖。
- 設定預覽不建立 live token，且既有 adapter 也不產生正式完成事件，因此不能進入 tracker。
- tracker 接受事件後立即更新記憶體狀態並排程 config save；同一世界模式的 `activity_event_id` 重送不重複累積。

成就來源、世界模式隔離、全程 1x 資格及測試功能排除規則，定義於 [FUTURE_DEVELOPMENT_PLAN.md](./FUTURE_DEVELOPMENT_PLAN.md)。家庭事件日誌與成就 tracker 應視為 gameplay event 的不同消費者；某事件未顯示在沙盒 household log，不代表它不能產生符合資格的 sandbox achievement event。
