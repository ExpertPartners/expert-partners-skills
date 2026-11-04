---
classification: public
---

# Factory runner ledger access

The reusable builder runs a read-only MCP preflight before Droid starts only when its caller sets the boolean `ledger_access_enabled: true`. The input defaults to `false`, preserving existing callers and their Droid command. The Skills caller opts in explicitly; the pinned Google Workspace caller is not changed by this patch. The preflight initializes a tool-capable session, discovers `job_status`, and reads the exact GitHub issue from the ledger. Both `job_id` and `repo` must match. It never claims, renews, creates, replies to, or finishes a job.

## Runtime inputs

- `FACTORY_LEDGER_MCP_URL`: the approved bearer MCP endpoint. This draft accepts only `https://partnersync.app.n8n.cloud/mcp/chat-to-code-factory`.
- `FACTORY_LEDGER_MCP_TOKEN`: the existing Factory-specific bearer credential, provided through the workflow secret. Never put its value in a prompt, repository file, output, or artifact.
- `FACTORY_LEDGER_JOB_ID`: the issue number already authorized by the overlap gate.
- `GITHUB_REPOSITORY`: the repository expected in the ledger result.

The reusable workflow accepts the `ledger_mcp_url` input, falling back to the caller repository or organization variable `FACTORY_LEDGER_MCP_URL`. Each caller must explicitly forward the `FACTORY_LEDGER_MCP_TOKEN` secret, as the skills caller demonstrates. Defining an organization secret alone does not pass it through an explicit reusable-workflow secret mapping.

After a successful read, the script merges the `factory-ledger` server into `~/.factory/mcp.json`. It writes only the literal `${FACTORY_LEDGER_MCP_TOKEN}` environment reference, never the bearer value. The Droid step receives the same environment variable and uses `--add-tools MCP:factory-ledger`. The distinct server name avoids colliding with the existing cloud computer's OAuth `chat-to-code` configuration.

The helper checkout is moved into a unique `RUNNER_TEMP` directory before execution. Git status assertions verify a clean caller checkout before setup and after staging and preflight, so the helper cannot be accidentally added to a caller commit. Project and ancestor `.factory/mcp.json` definitions are inspected before provisioning; a differing same-name server fails instead of shadowing the endpoint proved by the HTTP check. Disabled callers receive an empty credential environment value.

The client rejects redirects and off-endpoint URLs. Errors withhold server bodies, ledger content, and credentials. Requests have a maximum 20-second timeout, a two-minute client budget, bounded response sizes and tool pagination, and an explicit three-minute workflow step timeout. A failed preflight fails the build step. The existing `release` job still runs through `always()` after the gate started, and performs its existing cleanup and redispatch.

## Deployment prerequisites

This is an undeployed draft. The endpoint owner has verified the exact bearer endpoint; a real Actions runner has not yet exercised it. Provision the credential and URL through the approved secret owner, and update each intended caller's secret forwarding before opting that caller into the preflight. A disabled caller neither checks out nor executes the preflight and does not add the ledger MCP tools. An enabled caller fails clearly if provisioning is missing. Recheck the latest source and concurrent ownership before applying the patch.

The current GitHub issue must already have an exact repository/job record in the ledger. Missing or mismatched records fail with an actionable error rather than allowing a successful HTTP response to masquerade as access.

No new service, account, computer, broad key, OAuth-cache copy, or routing change is introduced. Existing builds and their workspace configuration are unaffected until this draft is reviewed and deployed. This preflight proves ledger access only; it does not certify native Factory connectors.

## Validation

```
python3 -m unittest discover -s tools/factory-access/tests -v
```

The tests cover the read-only handshake, session/protocol propagation, paginated tool discovery, JSON/SSE responses, exact repository/job matching, credential rejection without body disclosure, malformed replies, redirect rejection, configuration preservation, environment-reference output, missing credentials and deadlines.

After authorized deployment, a real runner must demonstrate authenticated MCP discovery and exact-job read, followed by Droid discovering and using the configured server. Independently verify a native connector read under the same Factory identity. Confirm that a controlled preflight failure still executes the existing overlap release path. Never upload the runner's MCP file or credential-bearing environment as an artifact.

Supported vendor mechanics:

- [MCP environment references and header authentication](https://docs.factory.com/harness/mcp#secrets-and-variable-expansion)
- [Headless MCP tool selection](https://docs.factory.com/droid-exec/overview#tool-controls)
