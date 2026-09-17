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
- `dashboard_launcher_play_day_concept.png`
- `runtime_memory_album.png`
- `runtime_memory_album_hover.png`
- `runtime_memory_album_compact.png`
- `runtime_achievement_reset.png`
- `memory_album_ui_concept.png`
- `memory_album_ui_concept_partners.png`
- `memory_album_ui_concept_clubroom.png`
- `memory_album_ui_concept_clubroom_v2.png`
- `manual_camera_4_3_ui_concept.svg` / `.png`
- `manual_camera_16_9_ui_concept.svg` / `.png`

## Dashboard launcher contract

- Expanded target size: 310 × 520 logical px. Collapsed rail: 72 logical px.
- The launcher owns navigation and window visibility only. Existing presenters,
  controllers, bindings, and information-center pages remain the data/action
  owners.
- The primary tiles open Information Center and the independent food tray.
- A full-width manual-camera action appears below the primary tiles, with a
  matching camera icon in the collapsed rail. The Dashboard exposes a narrow
  `toggle_manual_camera` controller entry point; the action is enabled only at
  1x and while the non-destructive memory-album capacity has room.
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

## Manual camera concept contract

- Both viewfinders use the same 300 px logical/output height. The 4:3 frame is
  400 × 300 and the 16:9 frame is 534 × 300, so switching ratios changes only
  the left and right field of view.
- The region outside the frame uses a semi-transparent neutral-gray overlay.
  The frame interior remains clear; overlays and controls must be hidden before
  capture and must never be written into the saved photo.
- A low-contrast full outline provides the exact crop boundary. Gold corner
  brackets, a subtle thirds grid, and a center reticle provide composition cues
  without turning the viewfinder into a decorative window frame.
- Camera mode deliberately exposes no persistent ratio selector, shutter
  button, screen label, speed label, or resolution text. The movable frame
  follows the pointer; left-click activates the shutter, `Tab` or `Space`
  switches 4:3 / 16:9, and `Esc` cancels. `Enter` has no camera action so the
  shutter has one unambiguous input path.
- A quiet control hint follows directly above the frame like a compact title
  bar. It stays outside the capture surface and disappears with the overlay
  before capture. Pointer sampling runs at 16 ms and uses floating-point easing
  so the compact frame does not jump between coarse native mouse events.

## Memory album comparison concepts

- `memory_album_ui_concept.png` keeps one large character at lower-left and the
  open album on the right.
- `memory_album_ui_concept_partners.png` reserves a wider left column for the
  original character plus `memory_album_parner1.gif` and
  `memory_album_parner2.gif`, while keeping every photo interaction surface
  unobstructed on the right.
- `memory_album_ui_concept_clubroom.png` uses the current `memory_album.png`
  clubroom. The main character is upper-left; partner 1 is lower-left and
  partner 2 is lower-right. Both partners face inward after horizontal mirroring.
- `memory_album_ui_concept_clubroom_v2.png` is the corrected comparison draft
  with a true left-right reflection applied to both partner designs.
- All four are comparison drafts. None replaces the source artwork or commits
  final runtime foreground geometry.

## Runtime memory album contract

- The memory album uses its own `memory_album` skin and the current
  `memory_album.png` clubroom background; it no longer shares the trophy-cabinet
  scene.
- `memory_album_char.gif` is the lower-right foreground. Both partner GIFs are
  grouped at the lower-left and mirrored by the renderer, so source files remain
  unchanged. The character layers may overlap the outer photo cards by design.
- The main character keeps the GIF's native 1:1 aspect ratio. Its four-frame
  animation runs at 300%, matching `event_note_char.gif` at 100 ms per frame
  while leaving all source GIF timings untouched.
- The album header is split into two compact paper tabs: current usage on the
  left page and the photo-folder action on the right. Capture mode and capacity
  now live in the Status Settings page so no translucent toolbar crosses the
  book spine.
- The live photo grid uses two columns at normal information-center sizes and
  four columns only on wide layouts, preserving the visual left/right book
  spread.
- Every existing photo is painted as a white instant-photo card with a prominent
  colored upper-left pushpin and a wider highlighted metal needle. Hover/focus
  animates the card within its reserved layout
  area, adding scale, lift, and shadow without shifting neighbouring cards.
- Photo cards derive their display height from each image's own aspect ratio and
  always use contain scaling. Portrait, 4:3, 16:9, and wide captures therefore
  keep their subjects intact instead of being cropped; only extreme aspect
  ratios are clamped to a practical card height and receive a small matte.
- Clicking a card continues to open the original file through the operating
  system's default image viewer. `runtime_memory_album.png` and
  `runtime_memory_album_hover.png` were rendered from the live Qt widgets using
  the existing user album rather than placeholder images.
- `runtime_memory_album_compact.png` verifies that the two paper tabs remain
  separated at the minimum window size. `runtime_achievement_reset.png` records
  the trophy card's compact two-stage reset control in its armed danger state.

## Play-day display slot

- The expanded launcher places a compact day chip at the right side of
  the existing `目前狀態` heading. It is hidden in the collapsed rail so the
  persistent desktop footprint does not grow.
- The chip stays hidden until the runtime exposes a positive
  `launcher_play_day_number`.
- Day 1 is the local calendar date on which this feature first initializes.
  Crossing local midnight increments the number even if the application was
  closed; existing installations are not backdated. The start date persists in
  config schema 11.
