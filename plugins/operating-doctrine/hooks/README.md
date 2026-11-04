# operating-doctrine hooks

Claude Code hooks that ship with the operating-doctrine plugin. `hooks.json` wires them in when the plugin is enabled, following the plugin hooks format in the Claude Code docs (`hooks/hooks.json` with a top-level `hooks` object, checked 2026-11-03).

| File | What it does |
|---|---|
| `hooks.json` | Wires `headless_route_check.py` to `PreToolUse` for browser navigation, new tab and browser code tools. |
| `headless_route_check.py` | The headless route check. Python 3.9 or later, standard library only. |
| `tests/test_headless_route_check.py` | Unit tests. |

## Headless route check

The hook backs the check order in browser-automation Rule 0, which points to where the rule itself lives. It runs before the browser navigation tools, `browser_navigate`, `navigate`, `tabs_create_mcp` and `browser_tabs` (a new tab with a `url`) on any MCP server, which covers `playwright-ember`, `playwright-allison` and `claude-in-chrome`. It also runs before the browser code tools `browser_run_code_unsafe`, `browser_run_code` and `browser_evaluate`, and checks every string literal their code navigates to with `page.goto`, `location`, `location.href`, `location.assign`, `location.replace` or `window.open`. For `browser_run_code_unsafe` and `browser_run_code` given a `filename`, it reads that file, relative to the session's working folder when the name is relative. It cannot see a URL held in a variable, so the check order in browser-automation Rule 0 still applies to every browser job. The hook reads the target host and looks it up in the access map, the Google Sheet owned by Keys and Sign-Ins.

| Access map status for the host | What the hook does |
|---|---|
| live | Refuses the call and names the headless route and the 1Password item to use |
| setting up | Refuses the call and says the setup job comes first |
| no API | Lets the call through |
| host not on the map | Lets the call through and adds the host to `unknown-hosts.log` |
| no cached map at all | Lets the call through and logs it in `hook.log` |

Either way the session gets the `Headless route checked` report line to use. A refusal carries it in the deny reason. A call that goes through gets it as `additionalContext`, with no permission decision, so the normal permission flow is unchanged.

The hook reads a URL the way browsers do, following the WHATWG URL Standard rather than Python's `urlsplit`, which the Python docs say follows neither standard fully:

- Leading and trailing spaces and control characters are dropped, and tabs and newlines anywhere are removed.
- In `http` and `https` URLs, `\` counts as `/`, any run of slashes before the host is skipped (`https:///host`, `https:host`, `//host`), the host ends at `/`, `?` or `#`, and the last `@` ends the user name.
- The host is percent-decoded, lowercased and mapped the way IDNA maps it, so `%2E`, full-width letters and `。` read as their ASCII forms, and a trailing dot is dropped.
- A navigation tool's URL with no scheme gets `https://`, as the tools add it. `view-source:` is checked as the URL it shows. `back` and `forward` on `navigate` are history steps and open no new site.
- In browser code, a string literal is read as JavaScript reads it, so `\/`, `\x2f` and `\u002f` are `/`. A relative target such as `/contacts`, `contacts`, `?page=2`, `#top` or `https:contacts` resolves against the current page, which the hook cannot see, and a template literal can build the host at run time. With a cached map, the hook refuses a call with such a target, or with a code file it cannot open, and asks for a full `https://` URL. A mapped live or setting-up host in the same call is named first.

`about:`, `chrome:`, `file:`, `data:`, `javascript:` and local addresses are never checked. A host matches a map entry when it is the entry's host or a subdomain of it, and the most specific entry wins.

- `example.com` covers `example.com` and every subdomain. `*.example.com` covers the subdomains only. For one host name, an exact match beats `*.`, which beats a parent domain.
- Two rows can share a host, for example one feature with an API and one without. When equally specific rows disagree, the status decides and row order never does: no API wins and the call goes through, because the feature with no API needs the browser. The hook logs `map-conflict` in `hook.log`. The skills' check order still applies, so work the API covers goes through the API. When equally specific rows share a status, a refusal names every one of their routes and 1Password items, sorted, so row order never changes what the session is told.

The map needs the columns System, Hosts, Headless route, 1Password item, Status and No-API reason. Hosts can hold several hosts separated by commas or spaces. Status is read loosely: anything starting with live (Live, Live - API) counts as live, setting up, set up, setup and in progress count as setting up, and no API, no and none count as no API. Any other status lets the call through and is logged, and `--refresh` names the rows that carry one. The map holds 1Password item names only. The hook never reads a secret, and if a map value looks like one (a known token prefix such as an AWS, Stripe, GitHub, GitLab, Slack or Google key, a private key, a password or bearer value, credentials in a URL, a long unbroken run of letters and digits, or a long word that mixes upper case, lower case and digits) it prints `[withheld, not an item name]` instead. MCP tool names, `op://` paths and item names print as written.

### The cache

The hook reads only a local copy of the map, so a browser call never waits on Drive. After the hook has printed its decision, it starts one background refresh if the last refresh attempt is more than an hour old. A failed refresh keeps the last good copy. A refresh also fails, and keeps the last good copy, when a row that is not wholly blank has no System, Hosts or Status, so a half-finished edit to the sheet never drops a protected host from the cache. Wholly blank rows are skipped. Run a refresh by hand with:

```
python3 plugins/operating-doctrine/hooks/headless_route_check.py --refresh
```

Files live in `~/.cache/expert-partners/headless-route/` (or `$XDG_CACHE_HOME/expert-partners/headless-route/`, or `$EP_HEADLESS_ROUTE_DIR`):

| File | Contents |
|---|---|
| `access-map.json` | The last good copy of the map |
| `refresh-attempt` | Its modified time is the last refresh attempt |
| `unknown-hosts.log` | One line per new host, `time<TAB>host<TAB>tool`, for the nightly check to file setup jobs |
| `hook.log` | Refusals, refresh results, map conflicts, and calls allowed because no map was cached |

### Setup on each machine

The sheet ID never goes in this repository, because the repository is public. Keys and Sign-Ins gives it. Put it in `~/.config/expert-partners/headless-route.json` (or the file `$EP_HEADLESS_ROUTE_CONFIG` names), or set `EP_ACCESS_MAP_SHEET_ID`:

```json
{
  "sheet_id": "<access map sheet ID>",
  "gid": "0",
  "token_command": ["gcloud", "auth", "application-default", "print-access-token"]
}
```

- `sheet_id` is read through the sheet's CSV export. `gid` picks the tab and is optional.
- `token_command` prints a Google access token that can read the sheet, and the hook sends it as a bearer token. It never logs or stores the token. The token needs a Drive scope. A plain `gcloud auth login` gives none, and the export then refuses it. Sign in once with a Drive read scope, using the Google account that can open the sheet:

  ```
  gcloud auth application-default login --scopes=https://www.googleapis.com/auth/drive.readonly,https://www.googleapis.com/auth/cloud-platform
  ```

  A user sign-in made with `gcloud auth login --enable-gdrive-access` also works, with `["gcloud", "auth", "print-access-token"]` as the command. `token_command` can be left out only when the sheet's CSV export needs no sign-in.
- `fetch_command` is the alternative to `sheet_id`. It is a command that prints the whole map as CSV, for a machine that reads Sheets another way.

Run `--refresh` once after setup and check that it prints `access map refreshed`. When the export refuses the token, it prints the HTTP status and says the token needs a Drive scope. Until the map is configured and cached, the hook lets every call through and logs each one in `hook.log`.

## Tests

```
python3 -m unittest discover -s plugins/operating-doctrine/hooks/tests -v
```
