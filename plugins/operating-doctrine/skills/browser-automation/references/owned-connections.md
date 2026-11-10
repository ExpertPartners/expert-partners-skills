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

## Per-job MCP route

The packaged `scripts/browser_jobs.py` supplies the per-job stdio MCP route. It
runs on the browser host around the existing protected launcher. It has no network
listener, scheduler or background dispatch. The caller starts one browser job per
task and passes the returned opaque `job_id` on every ordinary browser tool call.
A missing or unknown handle is refused. There is no shared-current-tab fallback.

- `browser_job_start` takes a short task name and creates a separate persistent
  MCP connection, Chrome window, extension group and working page.
- Ordinary browser tools require that job's `job_id`. The current working page is
  selected from a retained Page reference in that job's private MCP process.
  `browser_tabs` uses the same indices shown by ordinary tools' Open tabs and
  lists only working pages. The connector's index is reserved and cannot be
  selected or closed. Different jobs may execute concurrently; calls within one
  job serialize.
- `browser_job_status` returns only that job's lifecycle and ownership receipt.
- `browser_job_finish` and `browser_close` close only the job's own pages,
  connector and subprocess group. A peer keeps its connection and pages.
- `browser_job_recover` first reconciles a failed job's saved pages, then creates
  a new connection under the same job handle. It closes the old working pages,
  loses their task state and never replays an action. Inspect uncertain business
  results before deciding what to do on the new page.

The extension ungroups its pages on disconnect. Failed-job cleanup therefore
checks the saved browser process generation, exact tab IDs and window, the
connector's client identity, debugger attachment and the extension's current
connection claims. A moved, claimed or ambiguous page is refused. Cleanup never
chooses tabs by color, title, active focus or a guessed blank URL.

Creation provenance is separate from group membership. The private MCP process
retains an exact set of Pages it created. Chrome's tab-creation API receives the
explicit owned window and returns the new tab's birth ID. A unique nonce fragment
on the blank page binds the SDK Page to that ID before business navigation. Later
cleanup uses proven IDs and retained Pages, not the URL. An opener-owned popup is accepted only through the retained parent,
and its ID is bound using Chrome's matching opener metadata in the original
window and group. Separate-window or ambiguous popups require reconciliation;
this route does not claim arbitrary OAuth popup support. Unknown arrivals
are refused and are never adopted simply because they entered the group. Cleanup
preserves those unknown pages. An interrupted operation whose page inventory was
not checkpointed requires explicit reconciliation before recovery; it is never
reported clean from an incomplete list of IDs.
Disconnected cleanup also checks for unrecorded arrivals in the isolated window
and opener descendants across all windows, before and after closing saved IDs.
Live cleanup checks for late descendants after closing the parent pages. If the
inventory changed, cleanup stays incomplete and preserves unknown tabs.
Chrome removes opener metadata when the opener disappears, so closure also checks
all-window tab-ID deltas and refuses missing saved IDs. Close auxiliary pages with
`browser_tabs` and finish with `browser_job_finish`; a raw Page close that bypasses
the inventory checkpoint cannot be certified as clean. A concurrent unrelated
tab birth during closure can conservatively leave cleanup uncertain, while that
other tab remains untouched.

Each route checks the existing profile before starting its protected launcher.
It passes the window adapter as `--executable-path`; the launcher still owns the
profile-specific credential. It checks the launcher's configured source hash and
the MCP server version before opening a browser connection. The server reports
the Playwright core version, which differs from the launcher's MCP package version.
Do not substitute one for the other when configuring a pin.

The route calls the canonical `headless_route_check.py` policy before forwarding
URL or browser-code tools. It preserves the policy's host logging and reporting
notes, refuses a denied host and fails closed on policy execution errors. Native
consumer hooks stay enabled. Browser installation is not exposed as a job tool.

Local configuration names `host`, `profile`, `expected_account`, `launcher`,
`launcher_sha256`, `mcp_version`, `headless_hook`, `state_dir` and `bootstrap_lock`.
All facades on one host must use the same bootstrap lock. Use the hook from the
same installed operating-doctrine plugin. Run the packaged Python entry point
with `--config` and the absolute local configuration path, through the existing
SSH route where needed. Configuration and receipts are private host files. They
must not contain tokens. The owning SOP records actual installed paths and pins.

Receipts contain only lifecycle and ownership metadata, never connector queries,
page contents or tool arguments. EOF and normal termination of the facade attempt
owned-job cleanup. After an abrupt facade kill, preserve its receipts and reconcile the
exact orphan pages under the owning repair procedure. A restarted facade does
not silently adopt old handles or replay work. If Chrome restarted, saved tab IDs
are insufficient to authorize cleanup and the route refuses.

Opening another window through a shared connection does not implement ownership.
Shared cookies, sign-ins, application state and business-record ownership remain
outside tab scoping. There is no two-job limit or promise of unlimited capacity.
Report the workload and concurrency actually tested on the target host.

Create the job's window and working page before starting another bootstrap. Once
both exist, their page operations may run concurrently. Use the direct Page
reference through navigation. Do not navigate the connector page or move attached
tabs between groups as a substitute for a new connection.

The private browser pilot records actual runtime results, source hashes and host
paths. Source tests exercise forwarding, rejection, redaction, ownership routing,
policy refusal, concurrency and owned-process cleanup. They do not establish
native consumer adoption.

```sh
python3 -m unittest discover -s tools/browser-worker -p 'test_*.py'
```

## Window lifecycle

Each job owns one whole Chrome window, and the window closes when the job is done.
Completion is proven, never guessed from age or idle time.

- Binding. The lifecycle hook (`scripts/browser_window_cleanup.py`, entered through
  `hooks/browser_window_cleanup.py` and the stable user hook
  `~/.local/bin/ep-browser-window-cleanup`) adds the native `owner_session_id` to every
  `browser_job_start`. The route records the job's owner in a private ledger under the
  receipt directory (`owners/<job_id>.json`). One job has one owner session and a peer
  session cannot rebind it.
- Terminal evidence. Stop and SessionEnd mark only that session's jobs terminal. Sessions
  that never started a job never reach the M2. Codex allows SessionEnd only three
  seconds, so SessionEnd saves the terminal mark and finishes in a detached helper.
- Closure. A live facade finishes through its private same-user socket
  (`control-<id>.sock`), which accepts only a terminal job whose owner matches. After the
  owned pages close, the connector closes the whole window and the route confirms the
  window is gone. If the window also holds a tab the job did not open, only the job's own
  tabs close and the receipt records `window_disposition: preserved_shared`. A facade
  that has exited is reconciled through exact saved IDs, and any uncertainty preserves
  the receipt as `preserved_uncertain`.
- Failed-job reconciliation. A fresh maintenance connector first proves ownership
  without closing anything, records `window_removal_issued`, then removes the exact
  saved window and polls briefly until Chrome stops listing it. A missing connector is
  accepted only when every saved working page survives in the saved window, and no
  extra, claimed, attached or descendant tab is present. A retry after an interrupted
  removal finishes idempotently. Once a receipt is finished, a stale facade adopts it
  and never writes it back. A failed owned step records a static code from this
  route's own browser code (`owned_operation_failed:<code>`), never vendor text.
- Transport close. The route kills the job's own MCP process group with SIGKILL before
  closing its stdin. A graceful Playwright MCP exit closes pages one at a time and was
  cut off part way, which left windows without their connector. A hard kill only drops
  the relay. The extension ungroups the tabs intact, and reconciliation closes them by
  exact ID.
- Isolation at birth. Chrome can place a new connector in the newest existing window when
  two jobs start close together. Each connector that finds another tab in its window
  moves itself to a new window before ownership is recorded.
- Nightly sweep. The M2 LaunchAgent `com.expertpartners.browser-window-sweep` runs
  `browser_lifecycle.py --sweep` at 02:35. It finishes only terminal owned jobs. Active
  jobs, receipts with no owner record and uncertain receipts are left as they are. An
  owner row whose job finished more than thirty days ago is dropped; its receipt stays.
- Install. `scripts/install_browser_lifecycle.py` writes the stable user hooks for
  Factory, Claude Code and Codex on either Mac, so a pinned plugin version still runs
  them. On the M4 it forwards every request to the M2 over SSH. On the M2 it also
  installs the sweep. `install_job_route.py --upgrade` points future facades at a new
  produced runtime and leaves running transports alone.
## Deployment and acceptance

Use the existing producer and owning runtime configuration. Do not hand-edit a
marketplace cache or change a shared launcher while another job owns it. Keep the
previous executable-path setting so rollback is one step, and start a fresh job
connection after the old job finishes. Never restart Chrome to roll back this adapter.

The packaged `scripts/install_job_route.py` is the shared-entry producer. Given
the verified produced skill, private route settings and the exact existing
launcher hash, it preserves the protected bootstrap byte-for-byte in an
owner-only backup, writes private configuration, then atomically replaces only
the entry script. Future MCP starts receive the job facade. Existing transports
keep running until their own safe boundary. No browser, native app, daemon,
credential source or scheduler is restarted. The same installer restores the
original script only after verifying both installed and backup hashes.

Use `--settings`, `--runtime`, `--config` and the existing absolute `--python`
interpreter path for installation. Use `--config` and `--rollback` to restore
the entry. Settings contain the existing protected launcher's path and hash;
the generated private configuration points its child launches at the retained
bootstrap. Never point a facade's child launcher back at its facade entry.

A source change is not an installed route. Verify Codex, Claude Code and Ember
separately with multiple distinct connections, windows, groups and owned test pages,
overlapping real page operations, peer-tab exclusion and cleanup that preserves
the other job. Exercise a supported reconnect path with the original owned-page
disposition established before replacement. Preserve headless-route policy checks
and the visited-host feed on every consumer. A terminal helper that bypasses those
checks is not an accepted integration.

Describe the route as installed only on the consumers where it actually runs.
