# Compatibility

本文件記錄 config schema、migration 路徑與正式版本的相容性邊界。

## 目前狀態

- 目前 config schema：`8`
- manifest schema：`1`
- migration 實作：`tanuki_core/config_rules.py`
- config 載入與保存：`tanuki_core/config_store.py`
- household persistence：`tanuki_core/household_persistence.py`

## Config migration 路徑

- schema 1 → 2：補入 `debug_enabled`，並支援舊 root-level dashboard 欄位搬移。
- schema 2 → 3：補入 `world_mode` 與合法的 `household` 區塊。
- schema 3 → 4：補入資訊中心 geometry、分頁與建議尺寸設定。
- schema 4 → 5：補入 `social_status_enabled`。
- schema 5 → 6：補入 `race_frequency=normal` 與 `mood_climate=cheerful`。
- schema 6 → 7：補入 `chorus_frequency=normal`。
- schema 7 → 8：補入 `ui_locale=zh_TW`。

所有既有 schema 都會依序 migration 後再 normalize；無法識別、低於 1 或高於目前支援版本的值會採保守預設並保留 warning。

## `v0.6.0-beta` → `v0.7.0-beta`

- config 會自動由 schema 5 升級至 6，不需要刪除 `config.json`。
- household persistence 新增 `race_statistics`；舊資料沒有此欄位時會以空戰績載入。
- 新增 Activity／sleep／transformation／race runtime state 不要求手動修改既有存檔。
- manifest schema 維持 1；新增 contexts 由 converter 的 `KNOWN_CONTEXTS` 驗證。
- 普通與變身形態、關係、事件及戰績仍使用英文 canonical character key；各語系角色名稱只屬 UI 顯示層。

## `v0.7.0-beta` → `v0.8.0-beta`

- config 會自動由 schema 6／7 升級至 8；未設定語言時使用繁體中文，不需要刪除 `config.json`。
- household persistence 新增成就進度、睡眠／變身／合奏等既有玩法狀態；缺少新欄位時使用安全預設。
- 主程式第一次執行會在 LocalAppData 登記安裝位置、版本與介面語言，供獨立更新器辨識；舊版可攜資料夾仍可由更新器同資料夾偵測或由使用者選取一次。
- `TanukiUpdater.exe` 會保留舊版 `config.json`，並以 staging、SHA-256 驗證、同磁碟替換與失敗 rollback 更新，不需要解除安裝。
- manifest schema 維持 1；新增 Activity contexts 與權重仍由 `manifest_edit.xlsx` 及正式 converter 管理。

## `v0.8.0-beta` → `v0.9.0-beta`

- config schema 維持 8，不需要進行資料 migration。
- 已存在且合法的 `world_mode` 完整保留；只有新安裝、缺值或無效值使用新的 `sandbox` 預設。
- Windows 更新包沿用既有 updater／manifest／ZIP 流程；macOS 首版採 Release 手動下載，不共用 Windows 安裝登記或更新器。
- macOS 將同一份 config persistence 放在 Application Support；家庭事件、角色狀態與成就仍隨 config 保存。

## 使用者設定與版本庫設定

- `config.example.json` 是版本化的預設範例。
- `config.json` 是本機執行狀態並由 `.gitignore` 排除，不應加入 release commit。
- migration 應優先自動完成；若未來出現無法安全推導的設定，必須在 release note 記錄手動處理方式。

## 平台相容性

- 沒有既有設定或 `world_mode` 無效時，新安裝預設使用 `sandbox`；既有明確的 `golden_legend` 設定不會被覆寫。
- Windows 可攜版仍將 `config.json` 放在主程式資料夾並由 `TanukiUpdater.exe` 保留。
- macOS 功能受限版使用 `~/Library/Application Support/Tanuki_PC_Pet/config.json`，不寫入 `.app` bundle。
- macOS 不啟動 Win32 WindowTracker、全域滑鼠監聽器或 Windows 獨立更新器；完整能力差異見 [MACOS_LIMITED_VERSION.md](MACOS_LIMITED_VERSION.md)。

## 發版前相容性檢查

- [ ] schema 1–7 均可載入並升級至 schema 8。
- [ ] 無效設定值會回到已記錄的預設值並產生 warning。
- [ ] 舊 household 資料可在沒有競賽戰績時載入。
- [ ] `config.json` 未進入 staged changes。
- [ ] manifest dry-run 與產生的 JSON 一致。
