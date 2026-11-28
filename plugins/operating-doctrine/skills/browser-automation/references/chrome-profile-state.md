# Saved profile state on macOS

Window cleanup and profile persistence are independent. Close completed or failed
job tabs and windows. Keep the existing profile directory, cookies, site storage,
permissions and macOS Chrome Safe Storage key. Never sign out or clear browser
data as part of window cleanup. A website can still expire or revoke its own login.

`scripts/chrome_profile_state.py --config <private-config>` checks the login
Keychain without opening Chrome. If locked, it retrieves the configured Mac login
credential from 1Password and unlocks through Security.framework. The password
never appears in process arguments or files. Failures return fixed error codes.
The helper does not change Keychain locking settings or Chrome security settings.

The owner-only JSON config holds `keychain`, `op`, `credential_item`,
`credential_vault`, `service_account_token_file`, `chrome_data`, and `profiles`.
The last field maps existing profile directory names to expected account emails.
It contains references and paths, never a password or token. The referenced token
file must also be owned by the current user with no group or other access.

For a real browser task, append `--open <existing-profile>` and optionally
`--url https://…`. Identity is checked against both Chrome metadata and the
profile's saved account list before credential lookup or browser opening. Verify
the actual website's signed-in identity separately. No fresh user-data directory,
incognito mode, copied cookies or restore-last-session flag is used.

Install from producer-built skill output. An existing macOS login LaunchAgent may
run the readiness check at login and periodically, but must not open Chrome or
restore old tabs. An explicit browser opener should call the helper before
opening the requested existing profile. Do not replace or restart peer jobs to
install the readiness helper.

Verify the locked and unlocked readiness paths, private-file permissions, wrong
profile refusal and sanitized failures. On the browser host, verify real saved
website sign-ins after closing and reopening each profile. A whole-process restart
test must preserve active work and must be reported separately from a window test.
