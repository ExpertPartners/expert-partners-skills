# generate

`render.py` renders generated surface files, such as a repository's CLAUDE.md, from templates listed in `targets.yaml`, and `--check` fails when an output drifts from its template.

Moved here on November 8, 2026 from ExpertPartners/Development (archived) at commit 325fd884, under the HQ Repository Map. Full history stays in the archived Development repository.

Paths in `targets.yaml` resolve from `tools/`, the parent of this folder. The bundled templates are the retired Development CLAUDE.md and index, kept as working fixtures. Point `targets.yaml` at real templates and outputs before running it without `--dry-run`, so it never writes `tools/CLAUDE.md`.

## Commands

```bash
python3 -m unittest discover -s tools/generate/tests
python3 tools/generate/render.py --dry-run --out-dir /tmp/render-check
```
