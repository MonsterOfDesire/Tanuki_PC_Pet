# 未來開發計畫：成就系統與黃金傳說 2.0.0

本文件記錄目前 Activity 垂直切片完成後的版本邊界、已落地基礎與後續實作規格；未在「目前實作狀態」列為完成的內容，不代表已經進入 Runtime。

## 目前實作狀態

成就核心及第一版 gameplay event 覆蓋已接線，但尚未接入家庭摘要與獎盃櫃 UI：

- `achievement_catalog.py` 驗證單一世界模式 definition、規則類型、重複 id 與跨模式 dependency。
- `achievement_tracker.py` 已支援 event count、distinct value／composite、單次門檻、角色職責、跨事件 all-of、同時狀態門檻及成就 dependency。
- `achievement_eligibility.py` 已建立完整 1x session token、測試來源排除、世界模式／倍速切換後不可恢復的資格守衛；Runtime 已把世界模式及時間倍率切換通知守衛。
- `achievement_state.py` 保存分模式進度、解鎖時間、完成次數及 processed event id；已嵌入 household config persistence，舊存檔沒有此區塊時使用空狀態。
- `achievement_runtime_service.py` 已把競賽、合奏與魯道夫工作接到 live tracker；`achievement_gameplay_bridge.py` 集中處理睡眠／睡眠群、變身、照護、蜂蜜保護、分享食物及同時睡眠 snapshot，`app_runtime.py` 只保留 lifecycle 委派。
- 第一批 catalog 的沙盒 24 項與黃金傳說工作 2 項均已有 live event／snapshot／meta evaluator 來源，可在全程 1x 且非測試操作時實際累積或解鎖。競賽婉拒、合奏中斷、提早喚醒及各類場景取消只結束資格，不推進完成成就。
- 下一批建立 presenter／UI binding、家庭摘要入口、獎盃櫃及解鎖通知；不再新增另一套成就計數。

## 版本邊界

- 成就系統可在黃金傳說完整經濟系統之前開發，第一批以沙盒可正常完成的遊戲行為為主。
- 沙盒與黃金傳說只共用成就引擎及 definition schema；兩者的成就目錄、achievement id、獎盃分配、進度、解鎖時間與事件去重資料均完全分開。
- 黃金傳說的交易式經濟、自主飲食、購物展示及外部事件牌庫，明確延後至 **2.0.0** 開發時才加入。
- 在 2.0.0 之前，不應把目前的週期性帝寶飲料／魯道夫收藏品事件擴充成正式經濟平衡，也不應為尚未完成的經濟內容新增半套存檔契約。
- 2.0.0 的經濟功能不應成為第一版成就 tracker 的依賴。

## 建議開發順序

1. ~~盤點並補齊 sandbox gameplay event 覆蓋與來源分類。~~
2. ~~建立純 Achievement definition／evaluator／progress tracker。~~
3. ~~建立分世界模式 persistence、事件冪等與 migration。~~
4. 接入家庭摘要既有成就插槽、詳細頁與解鎖通知。
5. 推出第一批不依賴經濟的沙盒成就。
6. 擴充黃金傳說目前已有的工作、競賽、合奏等非 2.0.0 經濟成就；進度仍與沙盒分開。
7. 開發 2.0.0 時，再依序建立交易 ledger、自主飲食、購物展示、外部事件牌庫及其專屬成就。

---

# 成就系統規格

## 核心規則

### 1. 世界模式完全隔離

- 每筆進度鍵至少包含 `(world_mode, achievement_id)`。
- 沙盒事件只更新 `sandbox` 進度；黃金傳說事件只更新 `golden_legend` 進度。
- 每份 definition 只隸屬一個世界模式，不建立跨模式共用 definition。
- 兩個模式日後若有相似條件，仍須建立不同 achievement id 並各自分配獎盃；不共用解鎖結果。
- 切換世界模式不複製、不合併也不重置另一模式的進度。
- 第一版不建立跨模式綜合成就；未來若需要，應新增獨立 `meta` scope，而不是讀取或改寫任一模式的原始計數。
- 沙盒成就的獎勵不得改變黃金傳說生活費、家庭壓力、心情或關係。第一版成就建議只提供圖示、名稱、說明與完成紀錄，不提供玩法數值獎勵。

### 2. 只有完整 1x 行為可以計入

- 瞬時事件在結算當下必須為 1x。
- 有開始／結束生命週期的 Activity 或互動，必須從開始到完成全程維持 1x。
- 行為開始時若為 2x／4x／8x，不計入；完成前切回 1x 也不恢復資格。
- 行為開始於 1x，但期間曾切到 2x／4x／8x，即永久取消該次行為的成就資格；之後切回 1x 仍不計入。
- 倍速只影響成就資格，不中止原本的 Activity，也不取消既有事件、心情、關係或經濟結算。
- 世界模式在行為期間改變時，該次行為同樣取消成就資格，避免將一個 session 計入錯誤模式。

實作時應使用正規化後的時間倍率選項判斷 1x，不應用中文按鈕文字或浮點近似猜測。

### 3. 測試功能永不計入

以下來源必須明確標記為 `achievement_eligible=false`：

- 魯道夫工作預覽。
- 魯道夫 vs 帝寶競賽預覽。
- 合奏預覽。
- 沙盒形態手動控制。
- 沙盒指定睡眠／喚醒。
- 其他未來從狀態設定、Debug 面板或測試 API 啟動的行為。

一般遊戲操作不視為測試功能，例如玩家正常拖曳角色、從飲食托盤給予物品、角色自主睡眠、競賽、合奏或變身；這些行為在 1x 且符合個別成就條件時可以計入。

Runtime 不應依 `summary`、按鈕文字或事件中文名稱判斷測試來源。事件／session 必須保存明確的 `source_kind` 或等價欄位：

- `autonomous_gameplay`：可計入。
- `player_gameplay`：可計入。
- `settings_preview`：不可計入。
- `settings_test_control`：不可計入。
- `debug`／`test`：不可計入。

### 4. 冪等與完成邊界

- 使用穩定的 event id／activity event id 防止同一事件重複累積。
- 自然完成與中止必須是不同事件；需要「完成」的成就不得由 interrupted／declined 事件推進。
- 成就解鎖本身可以寫入 UI 通知或系統日誌，但不得再次送回同一 tracker 成為可計數 gameplay event。
- 被拖曳或隱藏而退出多人 Activity 的角色，只能依最終事件 payload 中實際保留的角色判斷參與成就。

## 成就資格守衛

長時間行為應在開始時建立 eligibility token，至少記錄：

- session／activity id。
- 開始時的世界模式。
- 開始時是否為 1x。
- source kind。
- 是否仍符合成就資格。
- 第一個取消資格的原因。

時間倍率離開 1x、世界模式切換或測試來源確認後，token 只能由 eligible 變為 ineligible，不能在同一 session 內恢復。完成事件只攜帶最終結果；Achievement event adapter 依 token 決定是否送入 tracker。

對於沒有長時間 session 的瞬時事件，adapter 應在事件發生當下建立同樣的資格判斷結果。

建議保留不顯示給一般玩家的取消原因，供 Debug 資訊使用：

- `time_scale_not_1x_at_start`
- `time_scale_changed_during_session`
- `world_mode_changed_during_session`
- `test_source`
- `missing_event_id`
- `duplicate_event`

## Definition 格式

成就定義應資料化，至少包含：

- `achievement_id`、definition schema version。
- 繁中名稱與說明。
- 唯一所屬的 world mode；一份 definition 不得同時註冊到兩個模式。
- 監聽的 canonical event name。
- 條件類型與目標值。
- event payload filters。
- 是否隱藏、是否顯示進度。
- 圖示 resource key。

第一版建議只支援可驗證的通用 evaluator：

- `event_count`：符合條件的事件累積次數。
- `distinct_values`：蒐集不同場地、角色或結果。
- `single_event_threshold`：單次事件達到參與人數、時長等門檻。
- `all_of`：數個條件全部完成。

連勝、每日、限時及會倒退的 streak 可延後；這些規則牽涉重啟、時間來源與中斷語意，不應混入第一版。

## Event envelope

成就 tracker 應消費獨立的 gameplay event envelope，而不是解析家庭事件的中文摘要。Envelope 可由現有 Activity／household event adapter 產生，至少包含：

- event schema version、canonical event name、event id。
- world mode、source kind。
- achievement eligible 與 ineligible reason。
- session 開始／結束時間。
- 參與者、角色形態與角色位置。
- outcome、reason。
- Activity-specific typed payload，例如競賽場地、勝者或合奏表演者數量。

家庭事件日誌與成就 tracker 是同一 gameplay event 的不同消費者。沙盒可以不顯示某些正式家庭事件，但仍可把合格的自主 gameplay event 送入沙盒成就進度。

## Persistence

建議的持久化邊界：

```text
achievement_schema_version
progress_by_world_mode
  sandbox
    achievement_id -> progress / unlocked_at / completion_count
  golden_legend
    achievement_id -> progress / unlocked_at / completion_count
processed_event_ids
  sandbox
  golden_legend
```

- 兩個世界模式各自維護事件去重資料。
- Definition 升版時透過 migration 更新 progress，不直接清空玩家資料。
- 第一版事件型成就從 tracker 啟用後開始累積，不回掃容量有限的舊 household log。
- 以目前持久狀態即可判斷的 snapshot 成就，日後可另定義載入時評估規則。

## UI 建議

- 完整版面、素材圖層、響應式欄數及驗收規格詳見 `tanuki_app/docs/ACHIEVEMENT_UI_DESIGN.md`。
- 可重現的 1600×900 視覺基準保存於 `tanuki_app/UI/concepts/viewport_regression/achievement_cabinet_functional.png`，來源腳本為 `tools/render_achievement_cabinet_concept.py`。
- 家庭摘要的成就插槽只顯示目前世界模式的完成數與最近解鎖；不顯示「最接近完成」項目或鎖定成就進度。
- 點擊家庭摘要的成就插槽開啟獨立「獎盃蒐集櫃」視窗，避免在目前已較擁擠的資訊中心頂部再增加常駐分頁。
- 獎盃櫃提供「沙盒／黃金傳說」分頁；切換分頁只切換 presentation，不改變 Runtime 世界模式。
- 櫃內以 G1／G2／G3 次級頁籤分類，一次只呈現一個難度並使用垂直捲動格：G3 為首次完成等入門成就、G2 為累積或多條件成就、G1 為稀有同場或跨系統高難度成就。
- 介面以 `UI/achievement.png` 作固定背景、`UI/achievement_char.gif` 作固定右下前景人物；只有左側主展示框內的獎盃格會捲動。
- 已定義但尚未解鎖的獎盃，以原 PNG alpha 產生黑色輪廓；不額外保存一套黑色 PNG。解鎖後顯示原色圖片。
- 尚未分配成就規則的獎盃素材只顯示空展示座或不建立格子，不應用黑色輪廓假裝已有隱藏成就。
- 未取得獎盃在游標懸停、鍵盤 focus、tooltip 及可存取說明中均不揭露名稱、取得條件或進度；只提供「未取得的 G1／G2／G3 獎盃」通用標示。
- 只有已取得獎盃在游標懸停或鍵盤 focus 時顯示名稱、完整取得方式與取得時間。
- 原始獎盃均為透明背景 256×256；載入後應以 alpha bounding box 在記憶體內正規化可見範圍，再等比例放入卡片，避免細長 G3 圖案因透明留白顯得過小。
- 鎖定卡片只顯示輪廓；已取得卡片才可顯示名稱、說明、圖示與完成時間。
- 解鎖通知應節流；同一批事件同時解鎖多項時合併呈現，避免阻塞角色 Runtime。
- UI 刷新使用 presentation snapshot，不應每秒重建全部卡片。
- 第一批獎盃與條件草案保存於 `UI/trophies/achievement_catalog_draft.json`；`race_achievements.json` 只作素材來源與原賽事對照，不直接作為 Runtime 成就定義。

## 第一批候選成就

實際名稱、獎盃分配、條件、事件契約狀態及保留素材詳見 `UI/trophies/achievement_catalog_draft.json`。目前先涵蓋：

- 完成第一場自主競賽。
- 累積完成指定場數競賽。
- 在 500／720／1100／1500px 四種場地各完成一次競賽。
- 自然完成一場至少三名表演者的合奏。
- 自然完成一場五名角色均在場的合奏。
- 完成首次自主睡眠或首次加入睡眠群；需先接出正式 sleep lifecycle gameplay event。
- 完成首次自主變身；需讓沙盒自主變身送入 gameplay event，但仍不寫黃金傳說家庭事件。
- 完成指定類型照護或蜂蜜保護；需先統一 care／item event envelope。
- 黃金傳說完成指定次數魯道夫工作；只更新黃金傳說進度。

G1 第一批高難度提案包含五人全員表演的同場合奏、四種距離與兩種方向的八種競賽組合、所有可參賽角色／形態各自取勝、五人同時自然睡眠、天狼星由淺眠醒來完成照護，以及跨系統家庭大事記。未分配的 G1／G2／G3 與 course 獎盃繼續保留，不為填滿展示櫃硬加入條件。

素材盤點時，來源 JSON 仍參照尚未存在的 `race/2023.png`、`course/10103.png`、`course/10104.png`、`course/10105.png`；第一版不得分配這四個路徑，UI 資源驗證也應將其列為已知來源缺口，而不是在執行期顯示壞圖。

任何依賴自主飲食、購物、外部帳單、發票中獎或其他經濟牌庫的成就，一律標記為 **2.0.0 才加入**。

## 實作驗證門檻

- 同一 event id 重送不重複增加進度。
- 沙盒事件不影響黃金傳說，反之亦然。
- 1x 完整完成可計入。
- 以倍速開始、期間切換倍速、切回 1x 完成均不計入。
- 所有設定頁預覽與測試控制均不計入。
- 自主 sandbox gameplay 在 1x 可以正常解鎖。
- 重啟後進度、解鎖時間與去重資料保持一致。
- 成就 UI 更新不重建家庭摘要其他成員卡片或事件表。

---

# 黃金傳說 2.0.0 專屬規劃

以下功能只在開發 **2.0.0** 時才加入。此前只保留設計，不建立正式平衡或相容性承諾。

## 1. 交易式家庭經濟

- 所有收入、支出、預留、退款及扣款失敗經由單一 economy service／ledger。
- UI、角色 widget 與 Activity executor 不直接修改 `living_fund`。
- 每筆交易具有唯一 transaction id、原因、actor、金額、提交時間與對應 gameplay event id。
- 動畫或 Activity 無法開始時不得扣款；需要消耗點的 Activity 在到達 commit phase 後才完成交易。
- 明確決定餘額不足政策。第一版建議不允許負餘額：實際支付目前餘額，未支付部分寫入 metadata 並轉換為家庭壓力；若要加入債務，應建立獨立 liability 欄位與還款規則。

## 2. 自主飲食 Activity

- 角色依距離上次進食、心情、家庭壓力、個性及食品偏好累積飲食傾向。
- 工作、睡眠、競賽、照護、合奏與供品互動期間不啟動。
- 形態能力繼續阻止設定為不可進食的變身角色。
- manifest context 規劃提案為 `activity_self_eat`；實作前仍須再次通知並由使用者分類，不在程式指定 GIF 或 action。
- 飲食到達 commit phase 後扣款，套用食品定義中的心情／壓力效果並寫入經濟事件。
- 玩家給予食品與家庭自主購買必須是不同 source。是否讓黃金傳說的玩家供品扣家庭生活費，需在 2.0.0 數值設計階段另行確認。

## 3. 購物展示 Activity

- 取代目前無視覺呈現的固定帝寶飲料／魯道夫收藏品支出事件。
- manifest context 規劃提案為 `activity_purchase_present`；同一張 GIF 可以由使用者同時分類為 `offer_preview` 與購物展示，但 Runtime 不以 `offer_preview` 描述自主購物。
- 依選中動畫的 manifest hotspot 顯示非互動式商品 overlay；商品不落地、不被撿取，也不進入供品 scene lock。
- 商品 catalog 保存 sprite、顯示尺寸、價格、角色偏好、效果與事件文字。
- 食品購買可以在展示後銜接自主飲食；收藏品則在展示完成後結束。

## 4. 外部事件牌庫

- 以資料驅動的事件定義描述電費帳單、發票中獎、梅雨季、家電故障、社區贈禮等情境。
- 每張事件包含唯一 id、權重、冷卻、資格條件、家庭效果、角色效果、summary variants 與 metadata。
- 使用洗牌袋或近期排除避免同一事件短時間重複，不使用無記憶的獨立亂數。
- 全員心情變化應以單一 batch settlement plan 套用，事件日誌只顯示一筆主要事件，不為五名角色複製五筆相同摘要。
- 第一版可只提供被動結果；需要玩家選擇的機會／命運卡片另作後續擴充。

## 5. 2.0.0 專屬成就

- 自主飲食次數、不同食品收藏、家庭收支、外部事件與資金危機相關成就只在上述事件契約穩定後加入。
- 仍遵守沙盒／黃金傳說進度隔離、全程 1x 及測試來源排除。
- 若某項經濟玩法只存在黃金傳說，definition 只允許 `golden_legend`，不得用沙盒 Debug 控制補進度。
