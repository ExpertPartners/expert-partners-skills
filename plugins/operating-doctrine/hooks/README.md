# operating-doctrine hooks

Claude Code hooks that ship with the operating-doctrine plugin. `hooks.json` wires them in when the plugin is enabled, following the plugin hooks format in the Claude Code docs (`hooks/hooks.json` with a top-level `hooks` object, checked 2026-11-03).

| File | What it does |
|---|---|
| `hooks.json` | Wires `headless_route_check.py` to `PreToolUse` for browser navigation tools. |
| `headless_route_check.py` | The headless route check. Python 3.9 or later, standard library only. |
| `tests/test_headless_route_check.py` | Unit tests. |

## Headless route check

No AI drives a browser at a system that already has headless access (Decision Log 2026-11-03, Headless access comes first, and Standing yes for headless access setup). The hook runs before every browser navigation, `browser_navigate`, `navigate` and `tabs_create_mcp` on any MCP server, which covers `playwright-ember`, `playwright-allison` and `claude-in-chrome`. It reads the target host and looks it up in the access map, the Google Sheet owned by Keys and Sign-Ins.

| Access map status for the host | What the hook does |
|---|---|
| live | Refuses the call and names the headless route and the 1Password item to use |
| setting up | Refuses the call and says the setup job comes first |
| no API | Lets the call through |
| host not on the map | Lets the call through and adds the host to `unknown-hosts.log` |
| no cached map at all | Lets the call through and logs it in `hook.log` |

A host matches a map entry when it is the entry's host or a subdomain of it, and the most specific entry wins. `about:`, `chrome:`, `file:` and local addresses are never checked.

The map needs the columns System, Hosts, Headless route, 1Password item, Status and No-API reason. Hosts can hold several hosts separated by commas or spaces, and `*.example.com` covers every subdomain. The map holds 1Password item names only. The hook never reads a secret, and if a map value looks like one it prints `[withheld, not an item name]` instead.

### The cache

The hook reads only a local copy of the map, so a browser call never waits on Drive. After the hook has printed its decision, it starts one background refresh if the last refresh attempt is more than an hour old. A failed refresh keeps the last good copy. Run a refresh by hand with:

```
python3 plugins/operating-doctrine/hooks/headless_route_check.py --refresh
```

Files live in `~/.cache/expert-partners/headless-route/` (or `$XDG_CACHE_HOME/expert-partners/headless-route/`, or `$EP_HEADLESS_ROUTE_DIR`):

| File | Contents |
|---|---|
| `access-map.json` | The last good copy of the map |
| `refresh-attempt` | Its modified time is the last refresh attempt |
| `unknown-hosts.log` | One line per new host, `time<TAB>host<TAB>tool`, for the nightly check to file setup jobs |
| `hook.log` | Refusals, refresh results, and calls allowed because no map was cached |

### Setup on each machine

The sheet ID never goes in this repository, because the repository is public. Keys and Sign-Ins gives it. Put it in `~/.config/expert-partners/headless-route.json` (or the file `$EP_HEADLESS_ROUTE_CONFIG` names), or set `EP_ACCESS_MAP_SHEET_ID`:

```json
{
  "sheet_id": "<access map sheet ID>",
  "gid": "0",
  "token_command": ["gcloud", "auth", "print-access-token"]
}
```

- `sheet_id` is read through the sheet's CSV export. `gid` picks the tab and is optional.
- `token_command` is optional. It prints a Google access token that can read the sheet, and the hook sends it as a bearer token. It never logs or stores the token.
- `fetch_command` is the alternative to `sheet_id`. It is a command that prints the whole map as CSV, for a machine that reads Sheets another way.

Until the map is configured and cached, the hook lets every call through and logs each one in `hook.log`.

## Tests

```
python3 -m unittest discover -s plugins/operating-doctrine/hooks/tests -v
```
