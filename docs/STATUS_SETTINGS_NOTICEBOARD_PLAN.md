# Status Settings Wooden Noticeboard Plan

## Approved design direction

- Keep the farm scene as the background.
- Replace the six-category rail with two top tabs:
  - Mode Settings
  - Developer Tools
- Use a wooden noticeboard as the outer frame and a warm paper sheet as the
  only interactive content area.
- Keep `status_setting_char.gif` at the large runtime scale and original aspect
  ratio. The character may overlap the wooden frame but not the paper controls.
- Reserve a fixed safe inset around every option row. Narrow layouts wrap or
  stack controls instead of clipping the rightmost option.

The current reference mockup is
`UI/concepts/status_settings_alternatives/07_wooden_noticeboard_activity_controls.png`.

## Settings contract

| Feature | UI control | Stored value | Default |
| --- | --- | --- | --- |
| Character care | Toggle switch | `care_feature_enabled` | enabled |
| Race | Frequency selector | `disabled`, `frequent`, `normal`, `occasional` | `normal` |
| Chorus | Frequency selector | `disabled`, `frequent`, `normal`, `occasional` | `normal` |
| Autonomous sleep | Toggle switch | `autonomous_sleep_enabled` | enabled |
| Autonomous transformation | Toggle switch | `autonomous_transformation_enabled` | enabled |

Mood climate remains a three-state style selector (`cheerful`, `balanced`,
`expressive`). It deliberately has no disabled state because it shapes natural
mood variation rather than starting a standalone activity.

Race and chorus use an integrated `disabled` frequency instead of a separate
switch. This avoids contradictory states such as a disabled switch paired with
the `normal` frequency.

The renamed cooldown section is user-facing **Rudolf Imitation Cooldown**. Keep
the existing internal `social_cooldown` identifiers and duration indices to
avoid an unnecessary config migration for a presentation-only rename.

## Disable semantics

- Disabling a feature prevents new autonomous sessions from starting.
- A race, chorus, sleep session, or transformation already in progress finishes
  normally. Disabling does not discard results or force a visual reset.
- Pending sleep observation/join attempts are cleared when autonomous sleep is
  disabled.
- Re-enabling race, chorus, or sleep starts from a fresh initial delay; an
  overdue timer must not trigger immediately.
- Transformation tendency does not accumulate while autonomous transformation
  is disabled. Existing transformed forms may complete their normal automatic
  return path.
- Sandbox/manual controls under Developer Tools remain available regardless of
  autonomous feature settings.
- Settings changes do not retroactively modify achievements or event history.

## Mode Settings layout

Wide layout uses four paper cards:

1. Basic and Display
   - world mode
   - character care
   - time speed
   - display scale
2. Autonomous Activities
   - autonomous sleep
   - autonomous transformation
   - race frequency
   - chorus frequency
   - mood climate
3. Rudolf Imitation Cooldown
   - Teio duration
   - Tsuyoshi duration
4. Memories and System
   - photo mode and capacity
   - interface language
   - update actions and status

The Chinese layout retains four cards down to the supported compact window.
English and Japanese switch to one column when labels need more width; the
paper content then scrolls vertically while both tabs stay visible.

## Artwork-aligned implementation

- The accepted background stays unchanged. Its 1600 x 900 source coordinates
  define the widget surface: `(90, 44, 1076, 734)`.
- The two tabs map directly onto the source wooden tabs. The content viewport
  maps to the inside of the source paper; it no longer has an opaque/frosted
  overlay or a second rectangular panel across the board.
- `status_settings_art.py` paints paper tab inserts, leaf emblems, functional
  vector icons, section headings, dotted dividers and glossy green selection
  pills. Native Qt buttons still own focus, keyboard input and click signals.
- Existing avatar crops are reused for Teio and Tsuyoshi. The foreground GIF
  keeps its original skin rectangle and playback configuration.
- `tools/render_status_settings_runtime.py` renders actual interactive widgets
  with fixture data and explicitly loads available Windows CJK fonts for the
  offscreen preview. It does not load or modify the player's saved config.

## Implementation batches

### A. Persistence and pure settings

- Add the two autonomous booleans to `RuntimeSettings` and
  `DashboardConfigState`.
- Add `disabled` to race and chorus frequency options.
- Increment the config schema and migrate old configs with both autonomous
  booleans enabled.
- Extend state mapping, config payload validation, and round-trip tests.

### B. Runtime gates

- Race and chorus executors recognize `disabled`, finish active sessions, clear
  pending schedule state, and avoid new proposals.
- Sleep runtime continues active sleepers but blocks new autonomous sleep and
  clears pending observation/join state.
- Transformation runtime continues transitions and automatic returns while
  blocking autonomous starts and tendency accumulation.
- Keep manual sandbox preview paths independent from autonomous gates.

### C. Binding and localized UI

- Extend `StatusSettingsSnapshot` and `DashboardStatusSettingsBinding`.
- Replace the category rail with the two-tab noticeboard layout.
- Add localized labels, tooltips, disabled-frequency text, and activity-state
  explanations for Traditional Chinese, Simplified Chinese, Japanese, and
  English.
- Keep runtime and persistence logic outside `status_settings_ui.py`.

### D. Skin and responsive verification

- Produce a blank wooden-board-and-paper runtime background without baked-in
  controls.
- Render tabs and controls in Qt so selection and localization remain dynamic.
- Restore the large character foreground rectangle without changing GIF aspect
  ratio.
- Verify wide, 16:10, 4:3, minimum-size, and long English/Japanese layouts.

## Required regression tests

- Old config loads with every existing feature enabled by default.
- Disabled race and chorus never schedule a new session.
- Active race and chorus sessions finish after being disabled.
- Disabled autonomous sleep blocks proposals and join attempts but does not
  force active sleepers awake.
- Disabled autonomous transformation blocks new starts without trapping an
  already transformed character.
- Manual sandbox controls work while autonomous features are disabled.
- Every language keeps the rightmost selector option inside the paper safe area.
