## 0.5.3 - 2026-11-03

Source Hunter stitching now tolerates real OCR noise. A growing or repeated frame is judged by how much of the screen it keeps in order, so a few misread steady lines no longer split one screen into many. A long line that is a near miss of its earlier reading joins it, a stray digit on a long line is read as noise, and a steady line missing from one frame is kept. The other reading always stays as a variant, so no reading is lost. Short lines, and lines where one number reads as another, still mark a new screen.
## 0.5.2 - 2026-11-03

Source Hunter now stitches a chat message that grows as it streams into one screen. The pane can shift up a little, the top or bottom line can be cut off, and a spinner or status word beside the message can read differently in every frame; that changing line is kept once, with its other readings. A line that was still being typed keeps its complete reading, and a typed word that wraps to the next line is not repeated. A static slide whose title or numbered line changes still starts a new screen, even when it adds a bullet.
