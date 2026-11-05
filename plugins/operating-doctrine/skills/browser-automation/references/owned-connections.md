# Browser job windows

The packaged `scripts/chrome_job_window.py` is a narrow executable-path adapter for Playwright MCP
extension mode on the browser host. It forwards the existing profile and connector
URL to the existing Chrome executable with `--new-window`. Chrome creates the window
before the extension attaches. No profile, credential, browser setting or installed
launcher is changed by this file.

Pass its absolute executable path through the existing launcher's
`--executable-path` argument. The existing protected launcher still chooses its
pinned MCP version, profile and credential. Configure `EP_BROWSER_EXPECTED_ACCOUNT`
from the current assigned account before enabling this route. The adapter reads the
existing profile directory, Chrome's current profile identity metadata and that
profile's account metadata, and refuses if the expected account is missing or does
not match. It also refuses while Chrome is stopped. It does not create a profile,
choose a fallback account, start a stopped browser or perform a sign-in.

`EP_BROWSER_EXECUTABLE` may name the
already installed Chrome executable when its path differs from the macOS default.
Do not pass a new user-data directory or use this adapter to launch a fresh profile.

The normal marketplace producer delivers the adapter alongside this skill on the
browser host. The SOP records its actual installed host path. Do not substitute
the copy on the calling computer or hand-copy a cache file to create another source.

The adapter accepts only an explicit `Default` or `Profile N` directory and the
Playwright extension's connect page. It forwards the full connector URL unchanged
and never prints it. Failure messages omit exception details because launch
arguments can contain a profile-specific token.

Identity metadata is a routing preflight. It does not prove that a website's session
is live. Before business actions, verify the target application's own signed-in
account and selected location. A blank connector page or a successful connection is
not application authentication evidence. If the assigned browser or website is
signed out, follow the existing authorized sign-in route. Never change profiles or
create a new one to get past the check.

This is one component of the per-job route. The consumer must allocate a distinct,
long-lived MCP connection for each job and retain that transport and its exact
working Page reference. Opening another window through a shared connection does
not implement that ownership. Shared cookies, sign-ins, application state and
business-record ownership remain outside tab scoping.

Create the job's window and working page before starting another bootstrap. Once
both exist, their page operations may run concurrently. Use the direct Page
reference through navigation. Do not navigate the connector page or move attached
tabs between groups as a substitute for a new connection.

The private browser pilot records the supervised native results and actual host
paths. Synthetic checks here exercise the adapter's forwarding, rejection and
redaction behavior only.

```sh
python3 -m unittest discover -s tools/browser-worker -p 'test_*.py'
```

## Deployment and acceptance

Use the existing producer and owning runtime configuration. Do not hand-edit a
marketplace cache or change a shared launcher while another job owns it. Back up
and record the previous executable-path setting before applying a reviewed change.
Rollback restores that setting and starts a fresh job connection after the old
job reaches its own safe boundary. Never restart Chrome to roll back this adapter.

A source change is not an installed route. Verify Codex, Claude Code and Ember
separately with two distinct connections, windows, groups and owned test pages,
overlapping real page operations, peer-tab exclusion and cleanup that preserves
the other job. Exercise a supported reconnect path with the original owned-page
disposition established before replacement. Preserve headless-route policy checks
and the visited-host feed on every consumer. A terminal helper that bypasses those
checks is not an accepted integration.

Until those consumer checks are recorded, the adapter is a reviewed rollout
component rather than proof of automatic per-job allocation or recovery.
