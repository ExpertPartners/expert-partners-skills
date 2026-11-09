# M4 Fix M27 hermetic test receipt

Result: PASS. The complete repaired suite ran 76 test methods with zero failures and zero errors after one coordinated production repair. Exit status was 0. No production operation was performed.

The initial complete run had 69 methods and 14 failing assertions: 13 production safety/regression findings plus one synthetic-library newline defect. A supplemental initial startup test confirmed six additional startup-injection assertions. The fixture defect was corrected without changing its expected behavior. Production fixes were combined into the one authorized repair. Initial details are in `initial-suite-results.json`; the raw initial output remains in the tool transcript.

The final suite retains every initial safety expectation and adds fresh eligible-skip identity checks, malformed/truncated lsof cases, snapshot identity drift, and a complete sequence of 28 fake guarded npx operations followed by one fake replacement-bound snapshot operation.

## Final evidence

- Full log: `repaired-suite.log`
- Structured receipt: `M27-hermetic-tests.json`
- Test source SHA-256: `3c740ae9c6afe5103ff9ccabd183c2f93c6858c46ef9382ee2ed2fa31420899b`
- Log SHA-256: `4bba13376268d5bba436cb6da81c159d11deb2022b8fe1d6521cb507a92a5b00`
- Retained synthetic directory: `/private/tmp/m4-guard-hermetic-avtwzt33`

| Group | Methods |
| --- | ---: |
| CoreTest | 29 |
| RuntimeTest | 22 |
| SnapshotTest | 15 |
| EntrypointStructureTest | 3 |
| StartupBoundaryTest | 1 |
| LegacyTest | 6 |

## Isolation and limits

All runtime command and estate-filesystem effects are primitive fakes. Real mutable files are synthetic retained stores, inert startup marker fixtures and a dangling symlink under /private/tmp test directories. Legacy hook tests use a temporary HOME and no-delete synthetic approval library. Startup tests invoke temporary wrapper copies with invalid modes only. No installed guard, production notes, real npm/tmutil/mount/database/cache cleanup or network calls were used.

- Synthetic noninvocation models a platform-denied launch; it is not a real auto-review result.
- Tests do not establish current production eligibility or physical storage reclaim. Parent owns fresh execution checks.
- Final-check race tests verify the designated checkpoints, not atomic exclusion of noncooperating external writers.
- M28 independent review and parent-controlled integration/deployment gates remain separate.

Parent M4 Fix owns M28 acceptance, publication, deployment and any authorized production execution. This subagent changed only its test file, test fixtures and assigned evidence files. No guard source, installed files, app settings or production state was modified by this subagent.
