# Manifest Context Catalog

這份清單記錄 `manifest_edit.xlsx`／`manifest_edit.json` 目前允許的全部 contexts，以及它們在程式中的實際語意。

重要原則：

- context 本身不會啟動行為，也不會直接改變心情、關係、生活費或家庭壓力；它只讓素材在指定情境下可被選取。實際結果由對應的 runtime／Activity 規則處理。
- 一張 GIF 可以同時屬於多個 contexts；`purpose`、action、mood tag 與 band 仍由檔名及 manifest 其他欄位決定。
- 下列核取方塊代表「已登記在 converter 的 context 目錄」，不代表每位角色都必須配置，也不代表功能已啟用。
- `future_*` 是保留原始分類字串（空白改成底線），不是「未來一定會實作」的承諾。只有 `future_*`／`disabled` 的素材不會載入 runtime。

狀態用語：

- **Runtime 選圖**：目前流程會把此 context 傳給 manifest resolver／AssetManager。
- **已註冊、未啟用**：格式及素材能力已預留，但目前沒有正式流程會進入。
- **分類輔助**：描述素材適用語意；目前流程主要仍由 action／mood 候選挑圖，未把此 context 當成嚴格篩選條件。
- **狀態語意**：行為／意圖會使用這個名稱，但目前不直接以它查詢 manifest。
- **保留、非 runtime**：只做素材整理；單獨使用時不會被 runtime 載入。

目前共 87 個 contexts；73 個已出現在五名角色與變身形態的 manifests，14 個尚未配置或屬於保留／狀態分類。

## Activity：自主合奏

- [x] `activity_chorus_approach` — **情境**：角色注意到正在進行的演奏，決定成為表演者或觀眾後前往現場；**對象**：反應角色 → 合奏 session 的固定中心與空閒 slot；**效果**：顯示靠近移動動畫，抵達前不延長合奏；拖曳、隱藏或超時只移除該角色；**狀態**：Runtime 選圖。
- [x] `activity_chorus_finish` — **情境**：合奏自然到期後，留在現場的表演者與觀眾同步收尾；**對象**：該場 session 的所有剩餘角色；**效果**：當前 band 有素材時顯示短暫收尾，缺少時直接釋放該角色，不跨 band 替代也不阻擋整場結束；**狀態**：Runtime 選圖。
- [x] `activity_chorus_observe` — **情境**：角色靠近演奏現場後選擇當觀眾；**對象**：觀眾 → 現場表演者；**效果**：顯示觀看／欣賞動畫直到全場同步結束；觀眾與表演者具有相同的個別退出規則；**狀態**：Runtime 選圖。
- [x] `activity_chorus_perform` — **情境**：符合資格的角色自主開始唱歌／演奏，或注意到現場後加入合奏；**對象**：表演者 ↔ 同場其他表演者與觀眾；**效果**：加入時由 manifest 隨機選取一次演奏素材，整場固定使用同一動畫；每位抵達的新增表演者延長演奏時間但不超過總上限；**狀態**：Runtime 選圖。

## Activity：賽跑競賽

- [x] `activity_race_accept` — **情境**：被挑戰者決定接受競賽；**對象**：被挑戰者 → 發出挑戰的角色；**效果**：顯示接受回應，完成後兩名參賽者前往起跑位置；**狀態**：Runtime 選圖。
- [x] `activity_race_challenge` — **情境**：自主競賽或沙盒預覽開始時，兩名角色已在水平中心距離 420px 內才發出挑戰；**對象**：挑戰者 → 被挑戰者；**效果**：顯示挑戰開場並由 Activity 同時鎖定兩名參賽者，避免遠距離隔空對話；**狀態**：Runtime 選圖。
- [x] `activity_race_consider` — **情境**：挑戰者播放挑戰動畫、被挑戰者尚未表態的等待期間；**對象**：被挑戰者 → 挑戰者；**效果**：同步顯示原地思考或觀察動畫，直到切換為接受或拒絕，避免被鎖定的移動素材原地踏步；**狀態**：Runtime 選圖。
- [x] `activity_race_decline` — **情境**：被挑戰者依心情與接受機率拒絕競賽；**對象**：被挑戰者 → 挑戰者；**效果**：顯示拒絕回應後提早結束競賽 Activity；normal 帝寶符合資格時固定接受，因此不要求 normal 拒絕素材；**狀態**：Runtime 選圖。
- [x] `activity_race_finish_lose` — **情境**：勝者到達且敗者已追到 150px 內後，敗者確認賽果；**對象**：敗者 → 勝者／終點；**效果**：大人輸給普通帝寶時使用 normal band 表現欣慰；大人互比或帝寶輸給大人時使用 low band 表現難過；變身魯道夫依形態契約維持 normal。素材 purpose 不會使角色在完賽階段繼續位移；**狀態**：Runtime 選圖。
- [x] `activity_race_finish_win` — **情境**：勝者率先抵達終點；**對象**：勝者 → 仍在接近的敗者；**效果**：立即停止勝者移動、強制以 normal band 顯示勝利表現並轉向面對敗者，不必等整體 Activity 進入 finish，也不直接改寫永久心情數值；**狀態**：Runtime 選圖。
- [x] `activity_race_ready` — **情境**：兩名參賽者抵達錯位的起跑位置後等待出發；**對象**：參賽者自身／跑道起點與終點；**效果**：顯示短暫預備動畫並鎖定座標，同時預先朝向實際跑動方向；帝寶可由 context 選到視覺上原地踏步的 move 素材；**狀態**：Runtime 選圖。
- [x] `activity_race_recovery` — **情境**：勝負動畫結束後的賽後恢復；**對象**：兩名參賽者自身；**效果**：依角色當前實際 mood band 顯示喘氣或休息，完成後釋放 Activity ownership；**狀態**：Runtime 選圖。
- [x] `activity_race_running` — **情境**：正式從起點跑向最長 1100px 外的終點；**對象**：參賽者 ↔ 競賽對手／終點；**效果**：顯示通用跑步動畫；座標速度由角色／形態基礎值、以 50 分為中心的連續心情調整及最多 ±0.15 隨機差組成，不再以 normal／low band 切換速度。勝者抵達後改播勝利動畫，敗者繼續接近至約 120–150px 間距；**狀態**：Runtime 選圖。
- [x] `activity_race_running_teio` — **情境**：天狼星與普通形態帝寶競賽時的專用跑步；**對象**：天狼星 → 普通形態帝寶；**效果**：只替代天狼星的 running 動畫；對其他對手仍使用 `activity_race_running`；**狀態**：Runtime 選圖。
- [x] `activity_race_to_start` — **情境**：接受挑戰後前往靠近兩人目前位置的跑道起點；**對象**：兩名參賽者 → 各自起跑位置；**效果**：executor 依螢幕左右可用空間選擇跑動方向，建立 84–160px 錯位起點並控制水平座標，抵達後才進入 ready；**狀態**：Runtime 選圖。

## Activity：睡眠

- [x] `activity_sleep_join_approach` — **情境**：角色受睡眠者影響並走向既有睡眠位置；**對象**：睡眠中的角色／睡眠群 anchor；**效果**：顯示加入者的靠近移動動畫，抵達前尚未成為 Sleep Activity；**狀態**：Runtime 選圖。
- [x] `activity_sleep_join_settling` — **情境**：加入者抵達睡眠群後準備躺下；**對象**：既有睡眠群與相鄰 slot；**效果**：顯示加入群組專用安頓過場，缺少時可回退 `activity_sleep_settling`；**狀態**：Runtime 選圖。
- [x] `activity_sleep_observing` — **情境**：清醒角色先觀察正在睡覺的角色；**對象**：睡眠中的候選對象；**效果**：顯示觀察階段動畫，之後才依睡意、距離與關係決定是否加入；**狀態**：Runtime 選圖。
- [x] `activity_sleep_settling` — **情境**：自主入睡或加入群組時的睡前安頓；**對象**：角色自身目前的合法地面位置；**效果**：顯示約三秒的睡前過場，完成後進入 sleeping；**狀態**：Runtime 選圖。
- [x] `activity_sleep_waking` — **情境**：自然醒、使用者喚醒或照護需求提前喚醒；**對象**：睡眠角色自身，照護早醒時另有需要照護的小孩；**效果**：顯示約三秒醒來過場，結束後釋放 Sleep Activity；**狀態**：Runtime 選圖。
- [x] `activity_sleeping` — **情境**：角色已完成安頓並正式睡眠；**對象**：角色自身，可為獨立睡眠者或睡眠群成員；**效果**：在主要睡眠階段持續顯示睡眠動畫；**狀態**：Runtime 選圖。

## Activity：魯道夫工作

- [x] `activity_work_rest` — **情境**：魯道夫完成工作後休息；**對象**：魯道夫自身；**效果**：工作結算後顯示約三秒疲憊休息，現行 profile 會忽略 mood band；**狀態**：Runtime 選圖。
- [x] `activity_work_stationary` — **情境**：魯道夫在原地執行工作；**對象**：魯道夫自身／家庭經濟需求；**效果**：顯示正式八秒工作階段，完成後才結算生活費、家庭壓力與本人心情；**狀態**：Runtime 選圖。
- [x] `activity_work_transport` — **情境**：需要移動的工作型態；**對象**：魯道夫自身與工作目的地；**效果**：已建立動畫 binding 與素材能力名稱，但第一版 work profile 沒有啟用 transport mode；**狀態**：已註冊、未啟用。

## 奶瓶與蜂蜜保護

- [x] `bottle_feed_child_approach` — **情境**：成人拿著奶瓶等待，鶴寶走向持有者；**對象**：鶴寶 → 奶瓶持有者；**效果**：顯示小孩靠近移動，抵達後切換喝奶階段；**狀態**：Runtime 選圖。
- [x] `bottle_feed_child_drink` — **情境**：奶瓶轉交後的小孩喝奶；**對象**：鶴寶與奶瓶；**效果**：顯示喝奶階段動畫，場景完成後套用供品結果並寫入事件；**狀態**：Runtime 選圖。
- [x] `bottle_feed_hold` — **情境**：成人持有奶瓶並等待小孩靠近；**對象**：奶瓶持有者 → 鶴寶；**效果**：讓持有者保持拿著奶瓶的等待姿勢；**狀態**：Runtime 選圖。
- [x] `bottle_feed_watch` — **情境**：小孩喝奶時成人在旁陪伴；**對象**：奶瓶持有者 → 正在喝奶的鶴寶；**效果**：顯示成人觀看／陪伴動畫直到餵奶場景完成；**狀態**：Runtime 選圖。
- [x] `honey_guard_move` — **情境**：鶴寶拿到不能食用的蜂蜜，照護者趕去阻止；**對象**：保護者 → 拿著蜂蜜的鶴寶；**效果**：顯示保護者快速靠近的移動動畫；**狀態**：Runtime 選圖。
- [x] `honey_guard_take` — **情境**：保護者抵達並拿走蜂蜜；**對象**：保護者 ↔ 鶴寶／蜂蜜；**效果**：顯示保護者取走蜂蜜的反應，之後由場景邏輯處理心情與事件；**狀態**：Runtime 選圖。

## 直接供品與 hover 反應

- [x] `offer_accept_honey` — **情境**：可食用蜂蜜的角色接受蜂蜜；**對象**：玩家或地面蜂蜜 → 角色；**效果**：顯示接受／食用蜂蜜動畫，實際獎勵由供品流程結算；**狀態**：Runtime 選圖。
- [x] `offer_accept_lollipop` — **情境**：角色接受棒棒糖；**對象**：玩家或地面棒棒糖 → 角色；**效果**：顯示接受／食用棒棒糖動畫；**狀態**：Runtime 選圖。
- [x] `offer_accept_milk` — **情境**：角色直接接過奶瓶，或成為後續餵奶場景的持有者；**對象**：玩家或地面奶瓶 → 角色；**效果**：顯示拿取奶瓶動畫，若存在合適小孩可再轉入 bottle-feed scene；**狀態**：Runtime 選圖。
- [x] `offer_accept_ramen` — **情境**：角色接受拉麵；**對象**：玩家或地面拉麵 → 角色；**效果**：顯示接受／食用拉麵動畫，也可能成為共享拉麵場景的持有者；**狀態**：Runtime 選圖。
- [x] `offer_accept_tea` — **情境**：角色接受茶；**對象**：玩家或地面茶 → 角色；**效果**：顯示接受／飲用茶動畫，也可能成為茶會共享場景的持有者；**狀態**：Runtime 選圖。
- [x] `offer_denied` — **情境**：角色被阻止取得不適合的供品，目前主要為鶴寶的蜂蜜；**對象**：被拒絕的角色 ↔ 供品／保護者；**效果**：顯示失望或哭泣反應，結果由 honey-guard 流程處理；**狀態**：Runtime 選圖。
- [x] `offer_preview` — **情境**：供品停留在角色可接受熱區、尚未正式放下；**對象**：玩家游標上的供品 → 預覽目標角色；**效果**：顯示伸手、注意或期待等預覽動畫；**狀態**：Runtime 選圖。
- [x] `offer_timeout_route_a_step1` — **情境**：供品 hover 超時後的 A 路線第一段；**對象**：等待供品的角色 ↔ 玩家游標／供品；**效果**：開始三段式不滿反應，A 路線會迴避游標；**狀態**：Runtime 選圖。
- [x] `offer_timeout_route_a_step2` — **情境**：供品 hover 超時後的 A 路線第二段；**對象**：同一等待角色 ↔ 玩家游標／供品；**效果**：延續並加重三段式反應；**狀態**：Runtime 選圖。
- [x] `offer_timeout_route_a_step3` — **情境**：供品 hover 超時後的 A 路線第三段；**對象**：同一等待角色 ↔ 玩家游標／供品；**效果**：以移動／逃離反應收尾並進入冷卻與負面餘韻；**狀態**：Runtime 選圖。
- [x] `offer_timeout_route_b_step1` — **情境**：供品 hover 超時後的 B 路線第一段；**對象**：等待供品的角色 ↔ 玩家游標／供品；**效果**：開始兩段式原地不滿反應，不額外迴避游標；**狀態**：Runtime 選圖。
- [x] `offer_timeout_route_b_step2` — **情境**：供品 hover 超時後的 B 路線第二段；**對象**：同一等待角色 ↔ 玩家游標／供品；**效果**：完成兩段式反應並進入冷卻與負面餘韻；**狀態**：Runtime 選圖。

## 分享食物

- [x] `shared_food_approach` — **情境**：第二名角色決定加入拉麵、茶或蜂蜜共享場景；**對象**：partner → 食物持有者；**效果**：顯示 partner 靠近 holder 的移動動畫；**狀態**：Runtime 選圖。
- [x] `shared_food_consume` — **情境**：共享結果輪到某位參與者食用／飲用；**對象**：holder 或 partner ↔ 共享食物；**效果**：顯示該角色的消耗動畫，實際誰吃由 outcome 規則決定；**狀態**：Runtime 選圖。
- [x] `shared_food_hold` — **情境**：共享場景開始時角色持有食物等待；**對象**：holder ↔ 食物／潛在 partner；**效果**：顯示持物與等待動畫；**狀態**：Runtime 選圖。
- [x] `shared_food_react` — **情境**：共享結果揭曉或另一人食用後的反應；**對象**：holder 或 partner ↔ 對方／食物結果；**效果**：顯示滿足、失望或陪伴反應；**狀態**：Runtime 選圖。
- [x] `shared_food_request` — **情境**：partner 注意到食物並表現出想加入；**對象**：partner → holder／食物；**效果**：顯示詢問、期待或索取動畫；**狀態**：Runtime 選圖。
- [x] `shared_food_watch` — **情境**：一名參與者等待或看著另一人食用；**對象**：holder 或 partner → 對方／食物；**效果**：顯示觀看與等待動畫；**狀態**：Runtime 選圖。

## 照護與雙人合體素材

- [x] `care_approach` — **情境**：成人發現 distressed 小孩並靠近；**對象**：照護成人 → 需要照護的小孩；**效果**：通用照護接近移動，角色專用 context 缺少時回退至此；**狀態**：Runtime 選圖。
- [x] `care_approach_teio` — **情境**：成人專門靠近帝寶進行照護；**對象**：照護成人 → 帝寶；**效果**：優先選擇帝寶專用的接近動畫，再回退 `care_approach`；**狀態**：Runtime 選圖。
- [x] `care_approach_tsuyoshi` — **情境**：成人專門靠近鶴寶進行照護；**對象**：照護成人 → 鶴寶；**效果**：優先選擇鶴寶專用的接近動畫，再回退 `care_approach`；**狀態**：Runtime 選圖。
- [x] `care_child_comfort` — **情境**：小孩在一般陪伴照護中被安撫；**對象**：被照護的小孩 ↔ 陪伴成人；**效果**：標記適合小孩安撫階段的素材；現行流程主要以 child comfort action 候選選取並逐步回復心情，候選可刻意包含吃糖、喝飲料等「大人照顧時讓小孩吃東西」的畫面；**狀態**：分類輔助。
- [x] `care_child_recovery` — **情境**：照護成功後小孩進入短暫恢復；**對象**：剛完成照護的小孩自身；**效果**：只保留可選的分類名稱；現行八秒 recovery 的用途是避免立刻重新觸發照護，畫面允許小孩自由選用既有恢復候選，因此不要求另外準備此 context 素材；**狀態**：已註冊、未作嚴格 context 選圖。
- [x] `care_companion` — **情境**：成人不使用合體素材，坐在可見小孩旁陪伴；**對象**：照護成人 ↔ 可見的小孩；**效果**：標記成人一般陪伴姿勢，小孩維持獨立可見並逐步回復心情；**狀態**：分類輔助。
- [x] `care_interaction` — **情境**：成人使用一張同時包含成人與小孩的 stationary 合體素材；**對象**：照護成人 ↔ 被隱藏的小孩；**效果**：通用合體照護篩選，小孩暫時隱藏並由成人的 `interaction` GIF 代表兩人；**狀態**：Runtime 選圖。
- [x] `care_interaction_teio` — **情境**：成人與帝寶的 stationary 合體照護；**對象**：照護成人 ↔ 帝寶；**效果**：優先選擇帝寶專用合體素材，再回退 `care_interaction`；**狀態**：Runtime 選圖。
- [x] `care_interaction_tsuyoshi` — **情境**：成人與鶴寶的 stationary 合體照護；**對象**：照護成人 ↔ 鶴寶；**效果**：優先選擇鶴寶專用合體素材，再回退 `care_interaction`；**狀態**：Runtime 選圖。
- [x] `interaction` — **情境**：單張 GIF 內同時包含多名角色的 stationary 合體素材；**對象**：素材中的成人與小孩；**效果**：通用素材分類，現行照護選圖仍以 `care_interaction*` 作嚴格 context；**狀態**：分類輔助。
- [x] `moving_care_interaction` — **情境**：成人以可移動的合體素材照護小孩；**對象**：照護成人 ↔ 被隱藏的小孩；**效果**：通用移動式合體照護篩選，畫面只顯示成人的 composite GIF 並一起移動；**狀態**：Runtime 選圖。
- [x] `moving_care_interaction_teio` — **情境**：成人與帝寶的移動式合體照護；**對象**：照護成人 ↔ 帝寶；**效果**：優先選擇帝寶專用移動合體素材，再回退 `moving_care_interaction`；**狀態**：Runtime 選圖。
- [x] `moving_care_interaction_tsuyoshi` — **情境**：成人與鶴寶的移動式合體照護；**對象**：照護成人 ↔ 鶴寶；**效果**：預留鶴寶專用移動合體素材；目前 manifests 尚未配置；**狀態**：Runtime 可識別、尚無素材。
- [x] `moving_interaction` — **情境**：單張 GIF 內同時包含多名角色且會移動的合體素材；**對象**：素材中的成人與小孩；**效果**：通用素材分類，現行照護選圖仍以 `moving_care_interaction*` 作嚴格 context；**狀態**：分類輔助。

## 觀察、關係與社交

- [x] `negative_reaction` — **情境**：摔落、被拒絕、孤單或其他負面事件後的反應；**對象**：角色自身與造成反應的事件；**效果**：標記適合負面情緒的素材，現行一般 reaction 主要依 mood preferences／forbidden moods 選圖；**狀態**：分類輔助。
- [x] `observe_hold` — **情境**：角色停下來持續觀察另一名角色；**對象**：觀察者 → 被觀察者；**效果**：保留觀察姿勢分類；現行關係觀察主要改由 `relation_watch`／`relation_close` 與 `post_observe` 選圖；**狀態**：分類輔助。
- [x] `post_observe` — **情境**：一般觀察結束後，角色短暫面向對方並延續互動；**對象**：觀察者 ↔ 剛才的被觀察者；**效果**：在小聊／觀察後鎖定期間選擇 idle 或 move 動畫；**狀態**：Runtime 選圖。
- [x] `relation_close` — **情境**：對焦角色具有較高熟悉與依附，或觀察後進入親近互動；**對象**：角色 → 關係親近的另一名角色；**效果**：選擇較溫暖的表情素材、面向目標並使用 close posture／overlay 語意；**狀態**：Runtime 選圖。
- [x] `relation_watch` — **情境**：角色對附近已有一定熟悉度的角色感到好奇；**對象**：角色 → 被關注的另一名角色；**效果**：選擇觀看／思考類表情並面向目標；**狀態**：Runtime 選圖。
- [x] `side_ready_followup` — **情境**：鶴寶目前畫面仍是 `side_ready`，且下一次真正需要重選 idle 動畫時的稀有後續姿勢池；**對象**：鶴寶自身；**效果**：每次 side-ready 機會只擲一次，10% 依目前 band 從此 context 選圖，90% 回到 `random`。資格只允許緊鄰使用，任何其他 idle／move／drag／Activity 動畫都立即取消；`side_stand`／`side_stand_cheer` 最終套用前會再次驗證一次性 token、目前 action 與畫面幀。選圖後至少保留 60 logic steps，且角色幀實際完成一次畫面繪製、繪製前未被其他動作覆蓋，才送出 1x 沙盒 G2 成就事件；不指定 GIF 或 follow-up action；**狀態**：Runtime 選圖與畫面確認。
- [x] `social_follow` — **情境**：帝寶或鶴寶跟在魯道夫身後；**對象**：社交小孩 → 魯道夫；**效果**：作為 intent／expression 狀態名稱；跟隨者可用任意既有移動方式追上魯道夫，因此刻意使用一般 move candidates，不要求另外配置此 context；**狀態**：狀態語意。
- [x] `social_mimic` — **情境**：帝寶或鶴寶模仿魯道夫正在播放的動作；**對象**：社交小孩 → 魯道夫；**效果**：作為 intent／expression 狀態名稱，實際畫面直接同步魯道夫相同 purpose/action/mood；**狀態**：狀態語意。

## 基本行為、拖曳與視窗

- [x] `drag` — **情境**：使用者按住角色至少 0.1 秒後進入拖曳，即使游標完全沒有移動也會套用；在 0.1 秒內放開仍視為短點，不使用此 context；**對象**：玩家游標 ↔ 被拖曳角色；**效果**：優先選擇 purpose=`drag`，缺少時依同一 context 跨 purpose 尋找素材，並在拖曳期間暫停一般 AI；**狀態**：Runtime 選圖。
- [x] `hard_landing` — **情境**：角色從較高位置重摔到合法地面；**對象**：角色自身 ↔ 地面；**效果**：物理依跌落高度扣心情後，先依目前 band 選擇此 context；該 band 缺素材時只放寬 band、仍不離開此 context；**狀態**：Runtime 選圖。
- [x] `random` — **情境**：沒有更高優先場景時的一般待機、漫遊、玩家短點反應，以及普通拖曳／合奏離場後回到日常；**對象**：角色自身／目前桌面／玩家短點；**效果**：提供 idle 與 move 的日常隨機素材池；一般環境重選會把符合目前 purpose、context 與 mood band 的既有候選素材合併成單一池，直接依每張素材的 manifest weight 抽選，不會先用固定 mood 優先順序覆蓋權重。候選 action 限制仍保留，因此不會擴張鶴寶稀有站立或其他場景；短點與兩種離場恢復均嚴格限定此 context 的 idle 素材，不會取用合奏、工作、照護或供品等專用 context；短點另依序優先 `happy`、`smile`；**狀態**：Runtime 選圖。
- [x] `window_flight` — **情境**：具飛行能力的角色離開地面、飛向視窗或工作列；**對象**：角色自身 → 目標視窗 surface；**效果**：嚴格選擇 purpose=`move` 的飛行素材；缺少此 context 時角色不具自由飛行能力；**狀態**：Runtime 選圖。
- [x] `window_perch` — **情境**：角色停在視窗上緣；**對象**：角色自身 ↔ 被選中的視窗；**效果**：嚴格選擇 purpose=`idle` 的停棲素材；**狀態**：Runtime 選圖。
- [x] `window_walk` — **情境**：角色沿視窗上緣水平移動；**對象**：角色自身 ↔ 目前停棲視窗；**效果**：嚴格選擇 purpose=`move` 的窗台行走素材；**狀態**：Runtime 選圖。

## 保留分類與停用素材

- [x] `disabled` — **情境**：素材保留在資料夾但明確不給 runtime 使用；**對象**：無；**效果**：若一列只有 `disabled`，converter 會接受但 AssetManager 不載入該 GIF；**狀態**：保留、非 runtime。
- [x] `future_ensemble` — **情境**：原始分類字串「future ensemble」；**對象**：分類所描述的群體／合奏素材；**效果**：只保留素材語意，沒有 runtime 行為；**狀態**：保留、非 runtime。
- [x] `future_lie_read` — **情境**：原始分類字串「future lie read」；**對象**：角色自身／閱讀物；**效果**：只保留躺著閱讀的素材語意，沒有 runtime 行為；**狀態**：保留、非 runtime。
- [x] `future_music` — **情境**：原始分類字串「future music」；**對象**：角色自身／樂器或音樂；**效果**：只保留音樂素材語意，沒有 runtime 行為；**狀態**：保留、非 runtime。
- [x] `future_race` — **情境**：原始分類字串「future race」；**對象**：角色自身／競賽對象；**效果**：只保留賽跑素材語意，不會啟動目前尚未實作的比賽機制；**狀態**：保留、非 runtime。
- [x] `future_sleep` — **情境**：原始分類字串「future sleep」；**對象**：角色自身；**效果**：只保留素材分類，不等同正式 `activity_sleep*`，也不會讓角色進入睡眠；**狀態**：保留、非 runtime。
- [x] `future_teach` — **情境**：原始分類字串「future teach」；**對象**：教學者與可能的學習者；**效果**：只保留教學素材語意，沒有 runtime 行為；**狀態**：保留、非 runtime。
- [x] `future_think` — **情境**：原始分類字串「future think」；**對象**：角色自身；**效果**：只保留思考素材語意，沒有 runtime 行為；**狀態**：保留、非 runtime。
- [x] `future_tsuyoshi_think` — **情境**：原始分類字串「future tsuyoshi think」；**對象**：鶴寶自身；**效果**：只保留鶴寶專用思考素材語意，沒有 runtime 行為；**狀態**：保留、非 runtime。
- [x] `future_work` — **情境**：原始分類字串「future work」；**對象**：角色自身／工作語意；**效果**：只保留素材分類，不代表日後會套用魯道夫工作，也不等同 `activity_work_*`；**狀態**：保留、非 runtime。
- [x] `future_work_money` — **情境**：原始分類字串「future work money」；**對象**：角色自身／金錢工作語意；**效果**：只保留素材分類，不會產生收入或家庭事件；**狀態**：保留、非 runtime。

## 維護規則

新增或重新定義 context 時應一起完成：

1. 在 `tanuki_core/manifest_xlsx_converter.py` 的 `KNOWN_CONTEXTS` 登記。
2. 在本文件新增情境、互動對象、效果與接線狀態。
3. 若屬 runtime 選圖，為 selector／profile 與真實 manifest coverage 補測試。
4. 若只做分類，清楚標示不會直接產生 runtime 行為，避免把素材分類誤當功能規格。
