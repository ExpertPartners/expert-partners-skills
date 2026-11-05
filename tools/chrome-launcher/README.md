# Quiet Chrome launcher for macOS

`chrome_quiet.py` produces a reusable AppleScript application outside Chrome's signed
bundle. It requires the existing signed-in Default profile and installs one Dock tile
and one login launch configuration. It reuses the installed `chrome-ai` or `chrome-quiet`
LaunchAgent and preserves its label. If both exist, it refuses before mutation so their
ownership can be reconciled instead of adding competing login launches. It never writes Chrome profile data or credentials
and never quits Chrome. The script is the producer for the generated application and
launch configuration.

```sh
python3 tools/chrome-launcher/chrome_quiet.py prepare
python3 tools/chrome-launcher/chrome_quiet.py install --receipt /absolute/new/backup-directory
```

Prepare and inspect the application and configuration before coordinating a graceful
Chrome quit. The install command saves the prior Dock and login configuration, and
replaces only the stock Chrome Dock tile. Activate the existing login item through
launchctl and reload the Dock after coordinating with the browser owners. Start Chrome
through the new Dock tile. Existing running Chrome processes ignore added startup
arguments, so process inspection after an agreed graceful relaunch is required.

The generated app launches the installed Chrome with `--silent-debugger-extension-api`,
`--restore-last-session` and `--profile-directory=Default`. Google documents the first
switch in [Chrome flags for tooling](https://github.com/GoogleChrome/chrome-launcher/blob/main/docs/chrome-flags-for-tools.md).
The switch suppresses the extension debugger infobar while retaining the extension's
debugging capability. It does not create a new profile, expose a debugging port or
disable extensions. Verify actual native browser chrome while Playwright is attached,
as a page screenshot cannot establish whether an infobar exists.

Directly starting the stock app from Finder, Spotlight, a recent Dock item or an external
URL handler while Chrome is stopped can omit the switch. The custom Dock tile and login
item are the supported launch paths. Chrome's own restart behavior must be verified
separately; this utility does not rewrite Google's application bundle or default URL
handlers to intercept every possible launch. Restored windows and tabs depend on the
browser's session restoration. A graceful quit must honor unsaved-work prompts.

Rollback restores the former login configuration and original Chrome Dock tile while
preserving later changes to unrelated Dock tiles. It retains the generated launcher for
inspection. Unload the installed launch agent before restoring its configuration and
reload the Dock afterward. Reload the old launch agent only if it was previously loaded.

```sh
python3 tools/chrome-launcher/chrome_quiet.py rollback --receipt /absolute/backup-directory
```

Rollback does not restart Chrome. Its current startup switch stays effective until a
later browser quit and stock launch.
