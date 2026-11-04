#!/usr/bin/env bash
# Rebuilds tools/skill-map/skills-graph.json and tools/capability-feed/ai-workforce-feed.json
# in the current checkout from its committed sources, with the existing producers.
# publish.sh runs it once per attempt after resetting the checkout to the latest main, so
# a producer's dependencies are reinstalled whenever that tip carries a different
# package-lock.json than the one installed. SKILLS_GRAPH_INSTALLED_REV names the commit
# the earlier install steps ran npm ci from.
set -euo pipefail

root=$(git rev-parse --show-toplevel)

for producer in tools/skill-map tools/capability-feed; do
  marker="$root/$producer/node_modules/.skills-graph-ci-lock"
  want=$(git -C "$root" hash-object "$producer/package-lock.json")
  if [ -f "$marker" ]; then
    have=$(cat "$marker")
  else
    have=$(git -C "$root" rev-parse --quiet --verify "${SKILLS_GRAPH_INSTALLED_REV:-none}:$producer/package-lock.json" 2>/dev/null || true)
  fi
  if [ "$want" != "$have" ] || [ ! -d "$root/$producer/node_modules" ]; then
    echo "Installing $producer dependencies for this source tree."
    (cd "$root/$producer" && npm ci)
    echo "$want" > "$marker"
  fi
done

(cd "$root/tools/skill-map" && node extract-skills-graph.mjs --eps "$root" --out "$root/tools/skill-map/skills-graph.json")
node "$root/tools/capability-feed/generate-feed.mjs" --write
