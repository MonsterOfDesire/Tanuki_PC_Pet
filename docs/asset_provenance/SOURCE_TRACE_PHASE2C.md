# Source Trace Phase 2C: historical archive screening

Generated on 2026-08-26. This phase compares historical public archive packs with every one of the 456 local GIFs. It does not treat a public download, an uploader authorship claim, or the absence of a prohibition as redistribution permission.

## Outcome

- Screened **18 ZIP archives** from two public uploader.jp collections.
- Decoded and compared **538 source GIFs** against **456 local GIFs**.
- Found **0 exact file hashes**, **0 exact decoded RGBA-and-timing sequences**, and **0 exact first frames**.
- The normal perceptual-review threshold (0.84) produced **0 candidates**.
- A deliberately lowered audit threshold (0.78) produced **53 weak candidates**. Of these, 52 pointed to `Air Groove/idle_music-happy.gif` and one to `Sirius Symboli/drag_original-sad.gif`; the maximum score was only 0.814571.
- Visual checks of batch maxima and both local candidate targets rejected the weak candidates. The characters, poses, line work, and props differ. Scores were caused by common transparent 500×500 canvases, matching eight-frame counts, and broad silhouette statistics.
- No local publication decision changed. The six previously identified guitar assets remain orange; the other 450 assets remain gray.

This is useful negative evidence: the screened archives are not direct exports of the current local files. It is not proof that the archives and local assets have no shared upstream body template, pose, editor, or deleted source post.

## Sources screened

### `tanuki_uploader`

The public index describes itself as a self-made tanuki asset uploader and states that material cannot be added by anyone other than the administrator: [public index](https://uu.getuploader.com/tanuki_uploader/).

Screened packs cover 2022 Q4, every monthly/collection pack located for 2023, the separate video-plus-SOZAI pack, and four 2024 packs. They contain **265 GIFs** in total.

The administrator-only statement is relevant evidence of an uploader-level authorship claim, but it does not:

- identify the administrator's real-world or social account identity;
- establish authorship of every upstream body or animation template;
- grant permission for modification, app embedding, repository publication, or installer redistribution.

No asset-specific reuse or redistribution permission was visible on the screened index or download pages.

### `tnk114`

The public index calls the collection a place for tanuki assets the administrator made: [public index](https://uu.getuploader.com/tnk114/).

The three 2024 aggregate packs contain **273 GIFs**:

| Pack | Public comment | GIFs | Uploaded |
| --- | --- | ---: | --- |
| [2024 first half](https://uu.getuploader.com/tnk114/download/6) | `2024年上半期に作成` | 119 | 2024-09-07 00:16:44 JST |
| [2024 middle](https://uu.getuploader.com/tnk114/download/11) | `2024年中半期に作成。改変込みです` | 74 | 2024-10-12 01:22:34 JST |
| [2024 second half](https://uu.getuploader.com/tnk114/download/15) | `2024年下半期に作成。修正した素材と改変・差分多め` | 80 | 2025-02-01 12:53:38 JST |

The archive hierarchy includes paths such as `改変素材/既存素材改変`. This explicitly shows that the collection mixes new work with modifications, fixes, and variants. The uploader claim therefore cannot be interpreted as original authorship of every layer. No asset-specific app-embedding or redistribution permission was visible.

## Matching method

For every source GIF, the tool checks:

1. SHA-256 of the original GIF bytes;
2. SHA-256 of all decoded RGBA frames, including dimensions, order, and per-frame timing;
3. SHA-256 of the decoded first frame;
4. normalized colour and alpha perceptual hashes for the first, middle, and highest-motion frames;
5. canvas dimensions and frame-count ratios, used only to rank manual-review candidates.

Exact decoded-sequence matches are strong file-lineage evidence even if GIF compression metadata differs. Perceptual candidates are never automatic authorship findings because tanuki assets commonly share bodies, poses, canvas sizes, and later edits.

The comparison tool is `tools/build_provenance_phase2c.py`. The archive download hashes, upload dates, extracted counts, and source claims are recorded in `data/external_archive_catalog.json`. Per-source-GIF screening records are stored in the nine `data/archive_screening_*.json` files.

## Coverage boundary

- The investigation targets the 456 local GIFs. Non-GIF source components were catalogued by count but not treated as direct GIF matches. In particular, `続・百狸夜行.zip` contains 44 PNG files and no GIFs.
- A zero direct-match result does not exclude a local GIF being animated from a PNG in one of these packs. Component-level image matching remains a later task.
- Deleted files, old Futaba attachments, unindexed replies, and archive packs not yet downloaded remain outside this phase.
- No uploader identity was inferred from the archive name or public download page.

## Next search route

1. Use character/action filenames and visual-template labels from the local relationship graph to query Futaba archives, tsumanne, Niconico/Nicozon, and web archives.
2. Compare relevant PNG components from the screened packs with local GIF key frames, especially when a shared base body is suspected.
3. Screen later `tnk114` packs only where filenames, characters, or template families overlap the local five-character scope; do not assume that newer packs are upstream merely because they are public.
4. If a source match is found, separate base body, character design, animation, expression variant, and later editor before evaluating permission.

Until those steps identify a creator chain and applicable permission, anonymous or download-only material remains orange when matched and gray when still unlinked; it never becomes green merely because no prohibition was found.
