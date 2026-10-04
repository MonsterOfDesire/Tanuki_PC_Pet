# Source trace Phase 2F: motion-template triage

Generated: 2026-08-27T20:32:55+08:00

## Outcome

- Reviewed **89** GIFs in `idle_lie*`, `idle_sit*`, and `idle_mix_dance*`.
- **89** are motion-semantic rejections for the documented canonical Jitabata branch. This is not a pixel/source-frame exclusion.
- Umaru-meeting branch: **15 medium-confidence candidates** (`idle_mix_dance*`), **22 low-confidence candidates** (`idle_sit_no/wave*`), and **52 semantic rejections**.
- No local file received an author attribution or a permission upgrade. All prior orange decisions remain unchanged.

## New author evidence

The [2021-10-26 Inside Games mini-interview](https://www.inside-games.jp/article/2021/10/26/134933.html) records Deon's explanation of the illustration's origin and his surprise/amusement at the meme. It contains no visible reuse, modification, app-embedding, or redistribution grant or prohibition. Friendly acknowledgement is not permission.

The [MUGENwiki history](https://w.atwiki.jp/niconicomugen/pages/11090.html) remains the basis for separating the anonymous early low-frame Jitabata branch from later Umaru-meeting traced motions.

A [2024 downstream creator's production note](https://note.com/beam_tarai_no2/n/n6a353a7abfb2) independently distinguishes Jitabata from Umaru Dance and says the reusable Umaru Dance cycle has eight frames. All 15 local `idle_mix_dance*` candidates also have eight frames. Because this source is later and its author is not the template author, it strengthens motion compatibility only, not authorship or permission.

## Evidence products

- `data/motion_template_audit.json`: per-file frame metrics and branch reviews.
- `review/phase2f_idle_lie_frames.png`: 24-file contact sheet.
- `review/phase2f_idle_sit_frames.png`: 50-file contact sheet.
- `review/phase2f_idle_mix_dance_frames.png`: 15-file contact sheet.

## Limitation and next target

Early Futaba attachment payloads remain unavailable, and the in-app browser safety policy blocked the NicoNico player page. No workaround was attempted. Exact-source comparison therefore remains open. The next highest-value target is recovering a historical source pack or archived frames for the 15 medium candidates before spending time on the 22 low candidates.
