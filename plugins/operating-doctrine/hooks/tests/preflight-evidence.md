# Preflight activation test receipt

Date 2026-11-08. Technical evidence for the preflight change, not production deployment or certification.

## Baseline and deterministic results

The original skill had no complexity/duration worksheet, sequential zero-additional-worker default or lifecycle activation events. It contained a default-two-agent rule. The new contract tests cover those replacements, explicit Auto preservation, scope distinctions and unknown handling.

The final local hook suite ran 72 tests successfully, including 16 new preflight tests and the unchanged browser-route tests. The existing factory-access suite ran 47 tests successfully. Changed-file pre-commit gates, including gitleaks, passed. The job validator passed; its standalone gitleaks executable was absent, so secret scanning evidence comes from pre-commit instead.

Release tests ran 22 successfully and release `--check` proposed 2.88.0 without writing. Graph extraction ran 40 successfully with PyYAML available; layout ran seven successfully; the feed suite passed after its locked dependencies were installed. Broader tooling checks were not all green. Under Python 3.12, `python3 -m unittest discover -s tools/readiness/tests -v` ran 55 tests with three failures in Python checker fixtures due to missing research-ops dependencies/stubs (`PIL`, `tldextract`, `bs4`, `protego`, `yt_dlp`, `av`). `python3 -m unittest discover -s tools/dead-code/tests -v` ran 32 with four failures in JavaScript detector fixtures, where knip reported reachable fixture files as unused under Node 26.13.0. Those tools and sources are unchanged by this diff. A baseline replay was not performed, so a pre-existing defect is not proven. No unrelated source or dependency declarations were changed to address them.

## Native local setup

The documented local marketplace route installed the branch plugin at project scope in an isolated temporary project. The regular user-scope marketplace install remained unchanged. That project disabled the older user plugin only for its own context. No global model/default, launcher, daemon or routing setting was changed.

The native CLI version was 1.6.0. The project plugin reported source revision `068913715f07`, manifest metadata 2.87.1. Because the local checkout was dirty, the commit label alone is not a content receipt. Source and installed SHA-256 matched before each run.

| File | First-run installed SHA-256 |
|---|---|
| hooks/hooks.json | `46b87ec55fa17ef9c590a0a5f2e8825c4b247251aa933c863d866cb080e448a0` |
| hooks/factory_preflight.py | `632acee8efb31f36032e14040c15c65649ffd351ab3b3173667cf91a4c2d077b` |
| skills/factory-operator/SKILL.md | `709cb65440a9154d9fa00db2141d17bf771a15efb256739c6c31c1342138b681` |

## Initial result

An ordinary assignment reviewed the hook and manifest for settings changes or recursion. Its user prompt did not tell the model to load a skill. SessionStart ran the installed plugin command and returned fixed context, exit 0. The model then classified read-only review as outside substantial work and read the files without invoking the skill. This failed the intended new-assignment activation behavior.

The instruction was corrected to include read/review/explain assignments, with only a one-line preflight for small work. Deep malformed JSON was also corrected to catch RecursionError and covered deterministically.

## Confirmation and remaining ordering gap

One authorized confirmation resumed the same local session with an ordinary new assignment to inspect regression coverage. The revised SessionStart hook completed, exit 0. An actual `Skill` call with `skill: factory-operator` appears in the tool transcript. Its returned file was the project plugin's updated skill. The model produced a one-line preflight and performed the review without additional workers.

However, the model bundled Skill and the first task Read in `Promise.allSettled`. The call occurred, but completion before meaningful task operations was not established. This fails strict ordering acceptance. The final hook and skill now explicitly require awaiting Skill in a separate step, never in parallel. Final deterministic tests verify that emitted instruction contract only. No third inference was run. Strict native ordering remains unverified, so this is not release-ready activation proof.

SessionStart startup/resume are observed. No UserPromptSubmit receipt appeared in these exec runs. Desktop, new Workstream assignment events, SendMessage routing and M4 coverage remain unverified.

## Runtime and usage boundaries

Both CLI requests selected Auto with reasoning `none`, its lowest supported request value. Local message records exposed `routerId: auto`, `modelId: claude-opus-5-5`, `apiProvider: snowflake` and `reasoningEffort: medium` for the observed responses. This is partial local visibility, not a promise to see every Auto backend or enforcement of lowest effective reasoning. No active user selection was replaced.

The initial run reported 44,768 Factory credits. The resumed completion reported 108,888, which may be cumulative session accounting. These are recorded separately, not summed or treated as an isolated delta, invoice or dollars. Initial usage reported 716 input, 1,682 output, 17,157 cache-read and 15,436 cache-create tokens. The resumed completion reported 726 input, 2,611 output, 59,738 cache-read and 42,068 cache-create tokens, with the same cumulative caveat.

Local process/log evidence tied the run to the registered M2. No managed computer or additional worker was requested. This is not a measured zero managed-compute-hours bill.

## Disposition

Review-ready source change, not production activation complete. The existing work record retains a strict sequential invocation test with the implementation owner after review, plus separate routing and M4 dependencies. Normal review, release and marketplace delivery are still required. The final source is newer than the temporary installed confirmation bytes.
