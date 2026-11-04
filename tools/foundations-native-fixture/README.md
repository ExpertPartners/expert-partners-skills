# Foundations native failure fixture

This optional test invokes the existing marketplace-installed Business Brain Foundations skill through the normal subscribed Codex account. It supplies one approved synthetic first-file draft and a local stdio MCP storage adapter whose saves always fail. The adapter never tells the model whether or how to retry. It accepts later-file requests too, so an incorrect continuation stays observable.

The fixed expectation comes from the canonical public Foundations procedure. Save the same first file twice after repeated storage failure, then report that it did not save without proceeding to another file. The exact installed skill must supply that behavior. No skill is copied, installed or changed by this fixture.

Run transport checks without any model or account access.

```sh
python3 -m unittest discover -s tools/foundations-native-fixture/tests -v
```

Run the optional native case only under the existing authorized test scope.

```sh
python3 tools/foundations-native-fixture/run.py \
  --codex /absolute/path/to/codex \
  --output /private/new/evidence/directory
```

The output directory must not already exist. Evidence stays outside this public repository. The runner preserves normal account authentication and the existing marketplace installation, disables apps and unrelated plugin defaults for this invocation, ignores user MCP configuration and registers only its synthetic storage server. Only that synthetic connection receives automatic tool approval under the authorized test scope. It removes inherited credential variables and runs the model with a read-only shell sandbox. It never changes global configuration or requests new credentials.

The receipt records installed version and source hash, exact invocation, actual native JSON events, actual adapter calls and failures. Inspect the native events to establish activation of the installed skill and whether the model stopped without drafting another file. A policy explanation, skill listing or the transport assertion result is insufficient. Successful process exit returns REVIEW_REQUIRED, never an automatic native behavior pass. Runtime or quota failure returns UNRUN_RUNTIME_BLOCKED and exit 2. No real Drive or Notion writes, company data, production acceptance or certification is tested.

The fixture retains source event files and the final native response for independent review. Synthetic event tests are explicitly transport tests, not a simulated assistant or evidence that the native skill passed.

The implementation follows the official [Codex MCP configuration](https://developers.openai.com/codex/mcp), [configuration reference](https://developers.openai.com/codex/config-reference) and [skill invocation documentation](https://developers.openai.com/codex/skills). Local CLI help remains part of each execution receipt.
