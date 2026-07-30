# SA+DWD Cloud Path: Google Workspace Access from Cloud and iOS Claude Code Sessions

Established 2026-07-30 (session "SA Path Local", M4 Pro Mac mini). Verified live the same day.

## The problem this solves

Cloud and iOS Claude Code sessions have no local filesystem keyfile and no 1Password
desktop-app sign-in, so they previously could not reach the Google service-account plus
domain-wide-delegation (SA+DWD) path that all Google file work runs on. This doc records
the durable delivery chain that fixes that.

## The credential chain

1. **Google service account (the DWD identity):** `workspace-automation-sa@workspace-automation-sa.iam.gserviceaccount.com`.
   This is the account granted domain-wide delegation with full Workspace write; it
   impersonates `allison@expertpartners.com`. Verified live 2026-07-30: minted a DWD
   access token with scope `https://www.googleapis.com/auth/drive` and called Drive
   `files.get` successfully.
   - Do NOT confuse it with `ember-gws-bridge@sdk-ember-prod.iam.gserviceaccount.com`
     (1Password item `GWS-Service-Account-Key`, same vault). That is Ember's bridge SA
     and is NOT authorized for the drive scope (`unauthorized_client`, verified live
     2026-07-30).

2. **Keyfile home (source of truth):** 1Password, vault `Ember-Production`
   (id `tlewiyf4p3uansqtttyocpublm`), item `GWS-Workspace-Automation-SA-Key`
   (id `7ofgfoto3djd6tttz54ws2nxpm`), field `credential` (the full JSON keyfile).
   The M4-local copy at `~/.openclaw/.secrets/service-account.json` is a mirror of the
   same key, not the canonical home.

3. **Delivery token (how cloud sessions reach 1Password):** 1Password service account
   `Claude Cloud SA Path` (UUID `EBIXJWNISFFCFKH5DZ3YC5ANKY`), granted `read_items` on
   the `Ember-Production` vault ONLY. Its token is stored in 1Password item
   `OP Service Account Token - Claude Cloud SA Path` (id `vwuilp7atz65b2xjj7hbhs7iku`,
   same vault). Scope verified live: reads the keyfile item, denied on all other vaults.

## Wiring a cloud or iOS session

- Set the env var `OP_SERVICE_ACCOUNT_TOKEN` to the delivery token in the Claude Code
  cloud environment settings (or the session's environment for iOS).
- Runtime bootstrap inside the session:

```bash
op read "op://Ember-Production/GWS-Workspace-Automation-SA-Key/credential" > "$TMPDIR/sa.json" && chmod 600 "$TMPDIR/sa.json"
```

- Then use `$TMPDIR/sa.json` with google-auth (subject `allison@expertpartners.com`)
  exactly as on the M4. Shred the temp file before session end.
- Service-account `op` calls always require `--vault` (or full `op://` paths).

## Rotation

- The delivery token expires **2026-10-28**. The `op` CLI caps service-account token
  lifetime at 2160 hours (90 days), which matches the standing quarterly rotation
  expectation; longer-lived tokens would require the 1Password web console and are not
  recommended.
- Quarterly rotation: mint a replacement token (`op service-account create` must run as
  a signed-in user, not a service account), update the 1Password item above, update the
  env var in cloud settings. The Google keyfile itself rotates on its own cadence; when
  it does, update the `credential` field of `GWS-Workspace-Automation-SA-Key` and the
  chain keeps working with no other changes.

## Known residue

- An orphaned 1Password service account `Claude Cloud SA Path`
  (UUID `5TWFRF4CCNDYXDGR6FW4DS6YLQ`, created 2026-07-30, token never captured, unusable)
  awaits revocation in the 1Password web console (Developer > Service Accounts).

No secret values appear in this document; vault and item ids are references only.
