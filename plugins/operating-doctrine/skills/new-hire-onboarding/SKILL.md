---
name: new-hire-onboarding
description: "Onboard a named person or AI employee into a company brain and department. Verify the HR assignment, reconcile Drive sharing or the AI's scoped brain gateway, and return a first-use receipt. Use for new hires, new AI employees, and resuming incomplete onboarding. Owned by HQ People and HR."
allowed-tools: []
tier: plugin
zone: brain
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "gets a person or AI employee to verified day-one access"
---

# New Hire Onboarding

Owner: HQ People and HR. Run when the owner names a hire or asks for a no-change readiness check. This skill sets up knowledge access, not HR records, general application access or offboarding. Do not use a pilot checklist as authorization.

1. Discover the live HQ Rulebook, Decision Log, Organization Instructions and Departments, Workspaces and Brain Folders map in HQ Company Core. Read all required pages with the original version. Apply the newest applicable decision and the owning department's instructions. Read held Cal evidence before advising on method; don't attribute this implementation to Cal.
2. Resolve the hire's exact identity, kind, company, department, manager and first work task from the named request and authorized HR assignment. Resolve the folder(s) and an appropriate non-sensitive sample live. Do not infer a principal from a display name, guess a folder ID, substitute a leader session or widen the assignment. Without a named authorized hire only run readiness checks; make no writes.
3. Follow the [connector runbook](references/runbook.md). Run the bundled `scripts/onboarding.py` with Python 3 and a single JSON object on stdin, using observations from the actual connector responses and operator-owned source of truth. The helper emits one JSON result and never sends a request. Do not pass credentials or document content to it. The connector runner must execute allowed actions and capture their real evidence; a generated plan is not a grant.
4. Give the hire one useful first task, the exact knowledge entry points and a clear next step if something is still missing. In the existing restricted HR onboarding record, record the date, assigned principal, company and department, before/after access status, first-use proof and any remaining failure with its owner. Do not write a Decision Log entry, start a second tracker, send an unrequested message or put personal details in general reports. Separate ready to fire, access verified, and onboarding complete; never label a partial run complete.

For an AI hire, install the company-first pointer in the named project's existing instructions before its first company-dependent task. Use the AI's own authenticated route, not a founder token, as proof. Run a controlled recovery check on the target runtime: verify it rejects a known unrelated scope, reports incomplete evidence and recovers using an authorized route rather than making up a result. Keep existing named entitlements intact. The Week Builder's gateway rollout is not part of an individual hire run.
