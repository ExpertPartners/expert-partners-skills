## 0.5.5 - 2026-11-03

Source Hunter joins a ticking header even when its words are misread a little from frame to frame. The live May 13 recheck after PR 199 showed the counter rule never fired, because it needed the header letters to match exactly. It now accepts them at the stitching similarity bar, only where the change looks like OCR damage, so a rewritten top line still starts a new screen.
## 0.5.4 - 2026-11-03

Source Hunter stitching now joins three more kinds of frames that belong to the screen already being built. A top line that reads the same in every frame apart from a running counter pairs with its earlier reading, at the top of the window only, so a long line lower down whose number changes still starts a new screen. A line between 21 and 29 letters long that differs only by one lone digit word, with every other word the same, counts as OCR noise, as it already did for long lines. A frame that adds nothing and only reads one line cut off, as a clean start of a line that is not a status word, joins the screen and keeps the cut reading as a variant, while a short status line that changes in place still starts a new screen.
## 0.5.3 - 2026-11-03

Source Hunter stitching now tolerates real OCR noise. A growing or repeated frame is judged by how much of the screen it keeps in order, so a few misread steady lines no longer split one screen into many. A long line that is a near miss of its earlier reading joins it, a stray digit on a long line is read as noise, and a steady line missing from one frame is kept. The other reading always stays as a variant, so no reading is lost. Short lines, and lines where one number reads as another, still mark a new screen.
## 0.5.2 - 2026-11-03

Source Hunter now stitches a chat message that grows as it streams into one screen. The pane can shift up a little, the top or bottom line can be cut off, and a spinner or status word beside the message can read differently in every frame; that changing line is kept once, with its other readings. A line that was still being typed keeps its complete reading, and a typed word that wraps to the next line is not repeated. A static slide whose title or numbered line changes still starts a new screen, even when it adds a bullet.
