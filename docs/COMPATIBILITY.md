# Compatibility

本文件記錄 config schema、migration 路徑與正式版本的相容性邊界。

## 目前狀態

- 目前 config schema：`7`
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

所有既有 schema 都會依序 migration 後再 normalize；無法識別、低於 1 或高於目前支援版本的值會採保守預設並保留 warning。

## `v0.6.0-beta` → `v0.7.0-beta`

- config 會自動由 schema 5 升級至 6，不需要刪除 `config.json`。
- household persistence 新增 `race_statistics`；舊資料沒有此欄位時會以空戰績載入。
- 新增 Activity／sleep／transformation／race runtime state 不要求手動修改既有存檔。
- manifest schema 維持 1；新增 contexts 由 converter 的 `KNOWN_CONTEXTS` 驗證。
- 普通與變身形態、關係、事件及戰績仍使用英文 canonical character key；各語系角色名稱只屬 UI 顯示層。

## 使用者設定與版本庫設定

- `config.example.json` 是版本化的預設範例。
- `config.json` 是本機執行狀態並由 `.gitignore` 排除，不應加入 release commit。
- migration 應優先自動完成；若未來出現無法安全推導的設定，必須在 release note 記錄手動處理方式。

## 發版前相容性檢查

- [ ] schema 1–6 均可載入並升級至 schema 7。
- [ ] 無效設定值會回到已記錄的預設值並產生 warning。
- [ ] 舊 household 資料可在沒有競賽戰績時載入。
- [ ] `config.json` 未進入 staged changes。
- [ ] manifest dry-run 與產生的 JSON 一致。
