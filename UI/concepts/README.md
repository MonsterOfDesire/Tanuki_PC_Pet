# TanukiProject UI concept notes

These images are layout concepts derived from the source artwork in `UI/`.
The source images and GIFs remain unchanged. Text, names, values, and settings
shown in the mockups are illustrative placeholders rather than runtime data.

## Window structure

- The food tray remains a small independent tool window.
- Relationship/summon, event log, family summary, and status settings share one
  singleton Information Center window.
- The legacy Dashboard control list is replaced by a small launcher. Its expanded
  state exposes only Information Center, food tray, a read-only runtime summary,
  an explicit status-settings button, and shutdown. Its collapsed state becomes
  an icon rail.
- Runtime summary chips are display-only. Status settings are opened through a
  separate, clearly labelled action in both expanded and collapsed modes.
- The Information Center keeps a slim common navigation row while the scene and
  content surface change with the selected page.
- Pinning or detaching an individual page can be added later without changing
  the presenter/controller/action boundaries.

## Page mapping

1. `diet.png`: the truck service window becomes a row of food item slots. The
   vehicle body is the drag surface; window controls stay small and peripheral.
2. `relation_summon.gif`: the whiteboard holds summon and relationship content.
   `relation_summon_char.gif` is an independent animated foreground layer.
3. `event_note.jpg`: the chalkboard becomes a two-pane event list and detail
   view; the podium remains decoration rather than an interactive surface.
4. `family_status_abstract.png`: a warm translucent panel covers the visually
   busy logo wall and contains household metrics, member cards, and recent news.
5. `status_setting.png`: the black stage screen contains grouped settings;
   developer actions remain visually secondary to normal settings.

## Relationship page layer order

From back to front:

1. `relation_summon.gif` played as the scene background.
2. A clean opaque whiteboard/content surface aligned to the source whiteboard.
3. Native Qt widgets for summon and relationship data.
4. The exact `relation_summon_char.gif` played with `QMovie` as foreground.

The content layout reserves a right-side safe area for the foreground character,
so the pointer and body may overlap the board without covering essential data.

The five files below `UI/family_icon/` are the avatar sources. Runtime avatar
loading uses only their first GIF frame. Each character has an independent
normalized head crop rectangle so the current first-pass crops can be reviewed
and adjusted one by one instead of forcing different source proportions into one box.

`UI/diet_char.gif` is also part of the runtime asset contract, but its final
placement over the food truck remains intentionally unset until the tray page is
implemented.

## Scaling rules

- Define each scene's board, screen, or panel rectangle in normalized source-image
  coordinates; do not position content using raw desktop pixels.
- Keep UI geometry in Qt logical pixels and let Qt apply the monitor device pixel
  ratio. Bitmap resources should not be manually multiplied by DPR twice.
- Scale the decorative scene as a single aspect-ratio-preserving layer. At small
  sizes, clip peripheral decoration before shrinking the interactive surface below
  its minimum usable size.
- Give the content surface a minimum logical size. When the window is larger,
  expand the clean surface independently (nine-slice or a native painted panel)
  instead of stretching text, character art, or the whole bitmap.
- Keep common navigation and all live text as native widgets, not baked into the
  background art.
- Pause hidden-page GIF movies and resume only the active page. Background and
  foreground GIFs may retain their own frame durations.
- Use actual presenter/state-mapper data and existing runtime setting choices when
  implementing the pages; mockup labels and values are not a data contract.

## Concept files

- `diet_ui_concept.png`
- `relation_summon_ui_concept.png`
- `event_log_ui_concept.png`
- `family_status_ui_concept.png`
- `status_settings_ui_concept.png`
- `dashboard_launcher_ui_concept.svg`
- `dashboard_launcher_ui_concept.png`
- `runtime_dashboard_launcher.png`
- `runtime_dashboard_launcher_collapsed.png`
- `runtime_status_settings_toggles.png`

## Dashboard launcher contract

- Expanded target size: 310 × 520 logical px. Collapsed rail: 72 logical px.
- The launcher owns navigation and window visibility only. Existing presenters,
  controllers, bindings, and information-center pages remain the data/action
  owners.
- The primary tiles open Information Center and the independent food tray.
- The three summary chips show world mode, time speed, and care state without
  accepting pointer or keyboard interaction.
- Expanded and collapsed layouts both provide an explicit status-settings action.
- The collapsed expand control sits directly below the brand icon so its location
  remains consistent with the expanded layout's top-mounted collapse control.
- Collapse/hide is distinct from application shutdown. Shutdown keeps an
  explicit label and power icon to reduce accidental exits.
- The default unpinned mode still retracts completely and uses the legacy
  20 px hover-progress sensor, preserving the original zero-obstruction goal.
- Pinning opts into the visible 72 px rail. Clicking outside then collapses to
  the rail instead of hiding completely; its buttons remain immediately
  clickable and expose the three runtime status indicators.
- The next implementation batch should introduce a separate
  `DashboardLauncherPanel`; do not continue adding UI branches to
  `dashboard_ui.py`.
