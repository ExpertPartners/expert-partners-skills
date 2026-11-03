---
research-ops: patch
---

Source Hunter stitching now tolerates real OCR noise. A growing or repeated frame is judged by how much of the screen it keeps in order, so a few misread steady lines no longer split one screen into many. A long line that is a near miss of its earlier reading joins it, a stray digit on a long line is read as noise, and a steady line missing from one frame is kept. The other reading always stays as a variant, so no reading is lost. Short lines, and lines where one number reads as another, still mark a new screen.
