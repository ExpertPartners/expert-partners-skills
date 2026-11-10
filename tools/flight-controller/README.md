# Factory flight controller

A small local controller that watches named Factory sessions on Ember's M2 every 15 minutes and recovers a real stall with at most one bounded message. Every check is ordinary Python against the documented Factory Sessions API. No check starts a model session or makes a paid model request.

A second, smaller program, the observer, runs on the other registered Mac and raises an alarm when the M2 heartbeat goes stale. A watchdog on the same Mac cannot report that Mac being down.

## What a check does

1. Reads the session, its children (with native prompt state) and its recent messages.
2. Decides from evidence, not from the status label alone.
   - `running`: the session is working. Nothing is sent.
   - `waiting_on_children`: idle while children run. Healthy however long it lasts. Nothing is sent.
   - `idle_recent`: idle for less than `stale_minutes`. Nothing is sent.
   - `tool_pending`: the newest assistant turn has an unanswered tool call. Nothing is sent.
   - `blocked_attention`: a native AskUser or permission prompt is waiting, on the session (an unanswered AskUser call) or reported by the API. Allison is alerted. Nothing is answered for her, and a posted message is never treated as clearing the prompt.
   - `child_blocked`: a child is waiting on a prompt. Allison is alerted.
   - `founder_decision` and `held`: the session's or a person's own words say it waits on Allison or is on hold. Nothing is sent.
   - `finished`: the session's own newest words say `Ready to archive`. Reported, never restarted.
   - `usage_exhausted`: the session's newest own words report a usage limit **and** carry a refusal cue beside it or a reported reset time. See below.
   - `stalled`: idle past `stale_minutes`, no live or blocked children, no pending prompt. One nudge.
   - `unknown`: any status the API does not document. Nothing is sent.
3. Only words the session or a person wrote count as evidence. Tool output, reasoning, injected reminders, reports relayed from child sessions and the controller's own messages are ignored.
4. Matching words are not a refusal. A session discussing a usage limit reads exactly like one the provider refused, so an exhaustion phrase counts only when a refusal cue sits beside it or the provider reported a reset time. Without either it stays ordinary prose and the session is judged on its idleness like any other.

## Recovery rules

- One nudge per stall, keyed to the session's `updatedAt`, with a 90 minute cooldown per session and at most 6 sends a day.
- If a nudge gets no assistant reply within `progress_grace_minutes`, it is recorded as unverified, no further nudge is sent and Allison is alerted.
- Usage limits. There is no read-only Factory endpoint for individual usage windows, so reset evidence comes from the provider's own text (`resets at <time>` or `try again in N minutes`). The controller waits for that reset plus `reset_margin_minutes`. When the provider reported no reset, it waits `unknown_reset_wait_minutes` (6 hours) from the message. Then it sends one bounded resume for that message, never a second one. If the session still reports the limit, Allison is alerted. Auto Model is never changed, and nothing pays, bypasses a quota, downgrades or uses another account.
- A silent wait is reported. Waiting hours for a reset while no children are running is indistinguishable from a dead stall, so the wait itself is announced once per exhaustion message, with the time it ends and the basis for it.
- A refused action is reported. If the API refuses the message the controller tried to send, Allison is told that the controller is broken rather than the session, because the failure otherwise reaches only the log.
- An accepted message is recorded (`accepted_at`, `message_id`) separately from resumed progress (`progress_verified_at` with reply and tool call counts), which needs the session's own reply written after the message landed.
- A send whose outcome is unknown (a transport failure after the request left) is never retried blind. The next check searches the session's messages for that send's `[flight-controller <nonce>]` marker first.

## Durability

- State: `state.json` (0600) in `state_dir`, written atomically.
- Heartbeat: `heartbeat.json` (0644) in `state_dir`, rewritten every check with `tick_seq`, `last_tick_at` and every verdict. It is world readable so the observer needs no state access.
- Log: `controller.log` NDJSON in `state_dir`, rotated at 4 MB.
- Single instance: `flock` on `state_dir/lock`. A second check exits without duplicating work. A killed holder releases the lock.
- Startup recovery: a gap longer than two intervals is recorded in `state.json` `gaps` and the check carries on.
- Bounded network: GET retries twice with capped backoff and a 20 second timeout. POST never retries.
- Operator stop switch: `controller.py --stop` creates `state_dir/STOP`. Checks still publish a heartbeat marked `stopped` and take no action. `--resume` removes it.
- Alerts use Ember's existing Sendblue channel to Allison's approved number. Credentials are read from 1Password at run time and never stored or logged. Alerts of the same kind are suppressed for 3 hours. One morning summary is sent after 07:00 America/Chicago.

## Install

Configuration lives outside the repository. Controller, on the M2 (`~/.config/flight-controller/config.json`, mode 0600):

```json
{
  "sessions": ["<session id>"],
  "state_dir": "~/.local/state/flight-controller",
  "factory_key": {"account": "ember", "service": "factory-api-key"},
  "alerts": {"op": "/opt/homebrew/bin/op", "item": "Sendblue API & Secret Key", "vault": "Ember", "recipient": "<approved number>"}
}
```

Every other setting has a default in `controller.py` `DEFAULTS`.

```sh
python3.12 tools/flight-controller/install.py controller \
  --config ~/.config/flight-controller/config.json --python /opt/homebrew/bin/python3.12
```

Observer, on the other Mac (`~/.config/flight-observer/config.json`):

```json
{
  "read_command": ["/usr/bin/ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "ember", "/bin/cat", "/Users/ember/.local/state/flight-controller/heartbeat.json"],
  "state_dir": "~/.local/state/flight-observer",
  "alerts": {"op": "/opt/homebrew/bin/op", "item": "Sendblue API & Secret Key", "vault": "Ember", "recipient": "<approved number>"}
}
```

```sh
python3 tools/flight-controller/install.py observer \
  --config ~/.config/flight-observer/config.json --python /opt/homebrew/bin/python3
```

The installer copies the code to `~/.factory/flight-controller`, renders the LaunchAgent into `~/Library/LaunchAgents`, bootstraps it in the GUI session and prints the label, paths and stop command. Both agents run through `/bin/zsh -lc` so the existing 1Password service account setup in the login shell is available, matching the other Estate agents. Both check `--test-alert` end to end.

## Stop and roll back

```sh
# Pause actions, keep the heartbeat
python3.12 ~/.factory/flight-controller/controller.py --stop
# Stop the schedule
launchctl bootout gui/$(id -u)/com.expertpartners.flight-controller
# Remove it
python3.12 tools/flight-controller/install.py controller --uninstall
# Observer on the other Mac
launchctl bootout gui/$(id -u)/com.expertpartners.flight-observer
```

## Limitations

- The LaunchAgents run in the logged-in GUI session, and the Factory key is in the login keychain. With FileVault on, nothing runs before login or after a power loss until someone logs in. This is not worked around, because that would weaken security.
- A whole-machine reboot has not been tested.
- The Sessions API reports native prompt state only for child sessions. For the watched session, a pending AskUser is detected from an unanswered AskUser tool call in its messages.
- No read-only usage or reset endpoint exists. Reset handling depends on provider text plus a conservative wait. Fixtures cover it; a live quota reset has not been observed.
- The observer depends on the other Mac being awake and on the SSH route between the Macs. If both Macs are down, nothing alerts.
- A Sendblue `DELIVERED` status is the carrier's report, not proof that someone read the alert.

## Request contract

A check reads `GET /sessions/{id}`, `GET /sessions/{id}/children?includeAttention=true&includeUsage=true` and `GET /sessions/{id}/messages`. The one write is `POST /sessions/{id}/messages` with the documented body `{"text": "..."}`; the response `messageId`, `status` and `recipientDroidStatus` are recorded, the last of which separates a message that starts a turn from one queued behind the current turn. `tests/test_controller.py` drives the real `Api` class against a stubbed opener and asserts this body, because a decision fixture that stubs `post_message` cannot see a wrong field name.

## Tests

```sh
python3.12 -m unittest discover -s tools/flight-controller/tests -p 'test_*.py'
```
