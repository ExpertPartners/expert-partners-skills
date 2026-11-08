#!/usr/bin/env bash
# Prints a settings.json fragment to paste into ~/.factory/settings.json. Never contains secrets.
# Usage: render-settings-fragment.sh byok <model-id> <display-name> [env-var]
#        render-settings-fragment.sh subagents <light-model> <medium-model>
set -euo pipefail
case "${1:-}" in
  byok)
    model="${2:?model id from https://docs.factory.com/models.md}"; name="${3:-Claude (EP BYOK)}"; var="${4:-EP_ANTHROPIC_FACTORY_KEY}"
    cat <<JSON
{
  "customModels": [
    {
      "model": "${model}",
      "displayName": "${name}",
      "baseUrl": "https://api.anthropic.com",
      "apiKey": "\${${var}}",
      "provider": "anthropic",
      "baseModelId": "${model}",
      "maxOutputTokens": 16384
    }
  ]
}
JSON
    ;;
  subagents)
    light="${2:?light model id}"; medium="${3:?medium model id}"
    cat <<JSON
{
  "subagentModelSettings": {
    "lightModel": "${light}",
    "lightReasoningEffort": "medium",
    "mediumModel": "${medium}",
    "mediumReasoningEffort": "medium",
    "heavyModel": "inherit"
  }
}
JSON
    ;;
  *) echo "usage: $0 byok <model-id> [display-name] [env-var] | subagents <light> <medium>" >&2; exit 1;;
esac
