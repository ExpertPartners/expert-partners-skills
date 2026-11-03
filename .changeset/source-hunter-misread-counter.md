---
research-ops: patch
---

Source Hunter joins a ticking header even when its words are misread a little from frame to frame. The live May 13 recheck after PR 199 showed the counter rule never fired, because it needed the header letters to match exactly. It now accepts them at the stitching similarity bar, only where the change looks like OCR damage, so a rewritten top line still starts a new screen.
