# 成就介面設計：獎盃蒐集櫃

本文件定義成就介面的視覺配置、資訊揭露規則與 Runtime 邊界。第一批成就核心、live gameplay event、家庭摘要入口、獎盃櫃與解鎖通知已於 2026-08-09 接入 Runtime；本文件同時作為後續擴充的 UI 契約。

目前的 1600×900 功能設計圖位於 `UI/concepts/viewport_regression/achievement_cabinet_functional.png`，可透過 `tools/render_achievement_cabinet_concept.py` 使用正式背景、前景人物及獎盃素材重新產生。該圖是幾何與資訊層級基準，不是 Runtime 截圖。

## 素材與固定圖層

| 用途 | 素材 | 原始尺寸 | 顯示方式 |
|---|---|---:|---|
| 背景 | `UI/achievement.png` | 1600×900 | `contain` 等比例縮放，作為資訊中心成就分頁的固定背景 |
| 前景人物 | `UI/achievement_char.gif` | 500×500、8 幀、每幀 100ms | 疊在背景右下，視窗可見時播放，隱藏時暫停 |
| 獎盃 | `UI/trophies/**/*.png` | 主要為 256×256 透明 PNG | 先依 alpha bounding box 裁掉透明留白，再等比例置中 |

`ui_skin_spec.py` 已依下列規格實作：

```python
SKIN_ACHIEVEMENT_CABINET = "achievement_cabinet"
ASSET_ACHIEVEMENT_BACKGROUND = "achievement_background"
ASSET_ACHIEVEMENT_CHARACTER = "achievement_character"

UiSkinSpec(
    key=SKIN_ACHIEVEMENT_CABINET,
    background_asset_key=ASSET_ACHIEVEMENT_BACKGROUND,
    content_rect=NormalizedRect(0.050, 0.055, 0.680, 0.775),
    minimum_frame_size=(960, 540),
    minimum_window_size=(720, 405),
    minimum_content_size=(650, 360),
    surface_role="achievement_cabinet",
    fit_mode=FIT_CONTAIN,
    foreground_asset_key=ASSET_ACHIEVEMENT_CHARACTER,
    foreground_rect=NormalizedLayerRect(0.690, 0.465, 0.310, 0.525),
)
```

`content_rect` 使用背景左側的主裝飾框；前景人物固定在右下，不屬於內容 layout，也不隨捲動區移動。人物圖層允許覆蓋背景裝飾，但不得攔截內容區的滑鼠事件。

## 資訊中心入口與層級

- 獎盃蒐集櫃是「狸貓資訊中心」的第五個分頁，與角色關係、事件日誌、家庭摘要及狀態設定共用可拖曳的頂部列。
- 從家庭摘要的「成就摘要」插槽進入時，直接切換至資訊中心成就分頁並同步目前 Runtime 世界模式。
- 成就分頁不提供「分離頁面」，避免回到類似飲食餐車的獨立工具視窗；關閉資訊中心不影響成就資料及角色 Runtime。
- 介面切換沙盒／黃金傳說只改變正在查看的成就目錄，不切換遊戲的世界模式。

## 版面

```text
┌──────────────────────────────────────────────────────────────────┐
│  獎盃蒐集櫃        [ 沙盒獎盃 ] [ 黃金傳說獎盃 ]    已取得 4 / 24 │
│                                                                  │
│  [ G1 ] [ G2 ] [ G3 ]                                           │
│  ┌──────────────────── 可垂直捲動的獎盃格 ────────────────────┐  │
│  │  [獎盃]  [鎖定輪廓]  [獎盃]  [鎖定輪廓]  [獎盃]             │  │
│  │  [獎盃]  [鎖定輪廓]  [獎盃]  [鎖定輪廓]  [獎盃]             │  │
│  │  ...                                                        │  │
│  └─────────────────────────────────────────────────────────────┘  │
│  已完成成就詳情：名稱／取得方式／取得時間                         │
└──────────────────────────────────────────────┐                   │
                                               │  前景人物動畫      │
                                               └───────────────────┘
```

### 第一層：世界模式頁籤

- `沙盒獎盃` 與 `黃金傳說獎盃` 是兩個獨立目錄。
- 成就 definition、achievement id、獎盃分配、進度與解鎖時間均不共用。
- 即使兩個模式日後有相似條件，也建立兩個不同 achievement id；不將任何一次解鎖轉移或合併到另一模式。
- 第一批沙盒目錄可顯示目前已規劃的 24 項非經濟成就；黃金傳說目前只分配 2 項魯道夫工作成就，其餘位置保留到 2.0.0 規劃。

### 第二層：G1／G2／G3 頁籤

- 同一時間只顯示一個難度分類，避免一頁塞入全部素材。
- 頁籤順序為 G1、G2、G3；進入頁面時記住上一次查看的分類。
- 每個頁籤可顯示該分類的 `已取得數／已定義總數`；這是分類總覽，不揭露個別鎖定條件或進度。
- 每個分類共用一個 `QScrollArea`，只讓獎盃格垂直捲動；世界模式與難度頁籤維持固定。

### 響應式獎盃格

- 卡片建議最小 148×168；獎盃可見圖形目標區約 104×112。
- 可用內容寬度足夠時每列 5 張，compact 尺寸每列 3 張，窄視窗每列 2 張。
- 重新計算欄數只重排既有卡片，不重新解碼全部 PNG。
- 背景偏明亮，內容面板採深酒紅半透明底、細金色邊框及暖白文字，維持獎盃辨識度。
- 尚未分配成就的素材不建立「神秘成就」卡；如需視覺填空，顯示無特定輪廓的空展示座及「後續追加」。

## 獎盃狀態與資訊揭露

### 未取得

- 以對應獎盃 PNG 的 alpha 產生深色半透明輪廓及 2px 暖白外框，不另存第二套鎖定圖片；外框只改善背景辨識度，不揭露成就內容。
- 卡片不顯示名稱、取得方式、條件文字或進度。
- 游標懸停、鍵盤 focus 與 tooltip 均不得揭露任何上述內容，也不顯示 `3/10` 之類的進度。
- 可存取名稱只使用「未取得的 G1／G2／G3 獎盃」，不包含可推測條件的成就名稱。
- 游標或鍵盤焦點進入未取得卡片時清空底部詳情列，避免殘留上一個已完成成就的內容造成誤解。

### 已取得

- 顯示原色獎盃，可在卡片下方顯示成就名稱。
- 游標懸停或鍵盤 focus 時，底部固定詳情列顯示：成就名稱、完整取得方式、取得日期時間。
- 詳情列優先於浮動 tooltip，避免長文字超出背景內容框；若保留 tooltip，內容必須與詳情列一致。
- 已取得卡片的可存取名稱包含成就名稱，說明包含取得方式及取得時間。

### 解鎖瞬間

- 先原地把黑色輪廓淡入原色，再顯示非阻塞式解鎖通知。
- 同一 gameplay event 解鎖多項時合併通知，不連續彈出多個阻塞視窗。
- 解鎖動畫只改 presentation；不可讓 GIF、通知或重新排版阻塞角色 timer。

## 更新與效能政策

- 獎盃櫃使用 immutable presentation snapshot；不要每秒重建視窗或所有卡片。
- 只在以下事件刷新：視窗開啟、模式頁籤切換、難度頁籤切換、成就解鎖、definition catalog 重新載入。
- `achievement_char.gif` 由單一動畫播放器持有；切換頁籤不得重新載入 GIF。
- 獎盃原圖、深色輪廓、白色外框及 alpha 裁切結果以 resource key 快取。
- 視窗隱藏後停止前景 GIF 與所有純視覺動畫，不啟動背景輪詢。

## Presenter 輸入

UI 不應直接讀取 gameplay event 或自行計算成就。建議 presentation snapshot 至少提供：

```text
AchievementCabinetSnapshot
  selected_catalog_mode
  catalogs
    sandbox
      completed_count
      defined_count
      tiers[G1/G2/G3]
    golden_legend
      completed_count
      defined_count
      tiers[G1/G2/G3]

AchievementCardSnapshot
  achievement_id
  world_mode
  tier
  trophy_resource_key
  unlocked
  title                 # locked 時回傳空字串
  acquisition_method    # locked 時回傳空字串
  unlocked_at           # locked 時回傳 null
```

Presenter 必須在資料邊界就清除鎖定內容，不能只靠 QWidget 隱藏文字。如此可避免 tooltip、accessibility 或 Debug property 意外洩漏未完成成就細節。

## 實作驗收

- 沙盒解鎖後，黃金傳說頁籤同名或相似條件仍完全不變。
- 切換頁籤不改 Runtime 世界模式。
- G1／G2／G3 各自捲動，模式與難度頁籤不隨內容移動。
- 未取得卡片在 hover、focus、tooltip、accessible description 中均不顯示名稱、條件或進度。
- 已取得卡片 hover／focus 正確顯示取得方式及時間。
- 720×405 仍可操作；寬版 5 欄、compact 3 欄、窄版 2 欄不互相覆蓋。
- 前景人物不遮擋主內容、不攔截滑鼠，視窗隱藏時停止播放。
- 成就頁隨資訊中心頂部列正常拖曳，且「分離頁面」在此頁停用。
- 開啟、捲動、切換頁籤及解鎖通知不造成角色移動或動畫卡頓。
