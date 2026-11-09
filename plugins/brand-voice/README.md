# Brand voice workflows

All business canon and private profiles stay in the owning Google Drive brain. This plugin holds retrieval and task mechanics, never a copied voice bank.

| Entry point | Use |
| --- | --- |
| [Brand Voice](skills/brand-voice/SKILL.md) | Select the existing brand route and retrieve current canon. |
| [Custom Instruction Builder](skills/custom-instruction-builder/SKILL.md) | Generate or audit concise marketing workspace instructions from verified knowledge and voice evidence. |
| [Voice Guide Extractor](skills/voice-guide-extractor/SKILL.md) | Extract from authentic samples, or audit and reuse an approved calibrated guide. |
| [Brand Guardian](skills/brand-guardian/SKILL.md) | Audit or revise writing using current canon and the default Anti AI editorial pass. |
| [Anti AI Writing Guide](skills/brand-guardian/references/anti-ai-writing-guide.md) | Bundled reference loaded by Brand Guardian, not a separately installed skill. |

## Prerequisites and use

Install `brand-voice` through the Expert Partners marketplace. Use an authorized Drive connector to read current HQ authority, Company Core canon and the relevant private voice references. Do not put credentials into this plugin.

Ask for the named capability, for example `Use Brand Guardian to audit this draft for the selected company and audience` or `Use Custom Instruction Builder for this marketing workspace`. Asking for Anti AI Writing Guide or anti-AI polish routes through Brand Guardian and loads its reference by default.

The new workflows are independently written reconstructions from bounded recovered Week 2 behavior. They are not original course packages. Complete original voice schema and later department variants remain unknown. Existing calibrated guides and brand skills are reused, not replaced.

## Output checks

Custom Instruction Builder includes a standard-library structural validator.

```sh
python3 plugins/brand-voice/skills/custom-instruction-builder/scripts/validate_instructions.py /absolute/path/marketing-workspace-custom-instructions.md
python3 -m unittest discover -s tools/brand-workflows/tests -v
```

The validator checks heading order, inclusive 80 to 120 word voice length, maximum 1,000 word total, filename and basic inventory leaks. It does not prove factual accuracy, detect every document title or judge authentic voice. Brand Guardian compares those against the actual sources.

Fresh personal extraction needs an isolated context and authentic samples, not a generated guide. Review-only requests do not rewrite or publish. File generation, saved output, installed delivery and active use must be reported separately. Company output follows the current document standard and stays in its owning brain, not this repository.
