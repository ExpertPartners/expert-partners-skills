#!/usr/bin/env bash
# Trusted main-only writer for the regenerated skill graph and AI Workforce feed.
#
# Each attempt fetches the latest main, resets this workflow's disposable CI checkout to
# it, runs the existing producers on that source tree, and pushes one generated-only
# commit on top. When main moves before the push lands, the scratch commit is thrown
# away and the next attempt rebuilds from the new tip. A generated commit is never
# rebased or replayed: an old generated diff conflicts with any newer graph or feed on
# main and is wrong for the newer sources anyway.
#
# Usage: publish.sh --checkout DIR --regenerate CMD [--attempts N] [--reconcile]
#   CMD runs inside DIR once per attempt and must rewrite only the two generated files.
#   --reconcile is for the scheduled run: the extractor stamps generatedFrom with the
#   commit it ran on, so a graph whose only change is that stamp counts as current and
#   an in-sync main gets no commit. Push runs keep committing the fresh stamp.
#
# Refuses to start (exit 4) unless all of these hold:
#   SKILLS_GRAPH_PUBLISH_REF   is refs/heads/main (the run's github.ref)
#   SKILLS_GRAPH_PUSH_TOKEN    is a non-empty writer token (empty when the secret is absent)
#   SKILLS_GRAPH_CI_CHECKOUT   names DIR, declaring it disposable; DIR is a full clone, not
#                              a linked worktree, and neither this script nor CMD lives in it
#
# Exit codes: 0 published or already current, 1 publish error that a retry cannot fix,
# 3 main moved on every attempt (no generated commit left behind), 4 refused,
# 64 usage; a failing CMD exits with its own code and is never retried.
set -euo pipefail

GRAPH=tools/skill-map/skills-graph.json
FEED=tools/capability-feed/ai-workforce-feed.json
REMOTE=origin
BRANCH=main

die() {
  local code=$1
  shift
  echo "::error title=skills-graph publish::$*" >&2
  exit "$code"
}

realdir() { (cd "$1" 2>/dev/null && pwd -P); }

# True when the staged graph equals the committed one apart from generatedFrom.
only_provenance_changed() {
  git -C "$1" show "HEAD:$GRAPH" | python3 -c '
import json, sys
committed = json.load(sys.stdin)
with open(sys.argv[1]) as fh:
    staged = json.load(fh)
for graph in (committed, staged):
    graph.pop("generatedFrom", None)
sys.exit(0 if committed == staged else 1)
' "$1/$GRAPH"
}

main() {
  local checkout="" regenerate="" attempts=5 reconcile=0
  while [ $# -gt 0 ]; do
    case "$1" in
      --checkout) checkout=${2:-}; shift 2 ;;
      --regenerate) regenerate=${2:-}; shift 2 ;;
      --attempts) attempts=${2:-}; shift 2 ;;
      --reconcile) reconcile=1; shift ;;
      *) die 64 "unknown argument: $1" ;;
    esac
  done
  [ -n "$checkout" ] && [ -n "$regenerate" ] || die 64 "usage: publish.sh --checkout DIR --regenerate CMD [--attempts N] [--reconcile]"
  [[ "$attempts" =~ ^[1-9][0-9]*$ ]] || die 64 "--attempts must be a positive whole number, got '$attempts'"

  # The writer gate comes before anything touches git, so a branch run or a run without
  # the app secret can never reach a reset, a commit or a push.
  [ "${SKILLS_GRAPH_PUBLISH_REF:-}" = "refs/heads/$BRANCH" ] \
    || die 4 "refusing to publish from '${SKILLS_GRAPH_PUBLISH_REF:-<unset>}': only refs/heads/$BRANCH writes the graph and feed."
  [ -n "${SKILLS_GRAPH_PUSH_TOKEN:-}" ] \
    || die 4 "refusing to publish: no writer token. Branch validation never needs it; on $BRANCH the app token step must have run."

  local top declared self regen_dir
  top=$(git -C "$checkout" rev-parse --show-toplevel 2>/dev/null) || die 4 "refusing: $checkout is not a git checkout."
  top=$(realdir "$top")
  declared=$(realdir "${SKILLS_GRAPH_CI_CHECKOUT:-/nonexistent}") || declared=""
  [ -n "$declared" ] && [ "$top" = "$declared" ] \
    || die 4 "refusing to reset $top: it is not the checkout named by SKILLS_GRAPH_CI_CHECKOUT, so it may be someone's working tree."
  [ "$(realdir "$(git -C "$top" rev-parse --absolute-git-dir)")" = "$(cd "$top" && realdir "$(git rev-parse --git-common-dir)")" ] \
    || die 4 "refusing to reset $top: it is a linked worktree, not a disposable clone."
  self=$(realdir "$(dirname "${BASH_SOURCE[0]}")")
  regen_dir=$(realdir "$(dirname "$regenerate")") || die 64 "--regenerate $regenerate does not exist."
  case "$self/" in "$top"/*) die 4 "refusing: run a copy of publish.sh from outside $top; the reset would rewrite it mid-run." ;; esac
  case "$regen_dir/" in "$top"/*) die 4 "refusing: run a copy of $regenerate from outside $top; the reset would rewrite it mid-run." ;; esac

  local header
  header=$(printf 'x-access-token:%s' "$SKILLS_GRAPH_PUSH_TOKEN" | base64 | tr -d '\n')
  if [ "${GITHUB_ACTIONS:-}" = "true" ]; then echo "::add-mask::$header"; fi
  # The credential is passed per command and never written to the checkout's config.
  remote_git() { git -C "$top" -c "http.https://github.com/.extraheader=AUTHORIZATION: basic $header" "$@"; }
  fetch_main() {
    remote_git fetch --quiet --no-tags "$REMOTE" "+refs/heads/$BRANCH:refs/remotes/$REMOTE/$BRANCH" \
      || die 1 "could not fetch $REMOTE/$BRANCH."
    git -C "$top" rev-parse "refs/remotes/$REMOTE/$BRANCH"
  }

  local attempt base now stray msg rc current
  base=$(fetch_main)
  for ((attempt = 1; attempt <= attempts; attempt++)); do
    git -C "$top" checkout --quiet --force -B "$BRANCH" "$base"
    git -C "$top" clean -fdq
    echo "Attempt $attempt of $attempts: rebuilding the graph and feed from $REMOTE/$BRANCH at $base."

    rc=0
    (cd "$top" && env -u SKILLS_GRAPH_PUSH_TOKEN "$regenerate") || rc=$?
    if [ "$rc" -ne 0 ]; then
      echo "::error title=skills-graph publish::the producers failed on $REMOTE/$BRANCH at $base (exit $rc). That is a real validation failure, so nothing is pushed or retried." >&2
      exit "$rc"
    fi

    stray=$(git -C "$top" status --porcelain --untracked-files=all -- . ":(exclude)$GRAPH" ":(exclude)$FEED")
    [ -z "$stray" ] || die 1 "the producers changed files other than $GRAPH and $FEED; nothing is pushed:
$stray"

    git -C "$top" add -- "$GRAPH" "$FEED"
    current=0
    if git -C "$top" diff --cached --quiet; then
      current=1
    elif [ "$reconcile" = 1 ] && git -C "$top" diff --cached --quiet -- "$FEED" && only_provenance_changed "$top"; then
      current=1
    fi
    if [ "$current" = 1 ]; then
      now=$(fetch_main)
      if [ "$now" = "$base" ]; then
        git -C "$top" reset --quiet --hard "$base"
        echo "$GRAPH and $FEED already match the sources at $base; nothing to commit."
        return 0
      fi
      echo "::notice title=skills-graph publish::$BRANCH moved from $base to $now during attempt $attempt. Rebuilding from the new tip."
      base=$now
      continue
    fi
    if git -C "$top" diff --cached --quiet -- "$FEED"; then
      msg="skills-graph: regenerate from SKILL.md sources [skip ci]"
    else
      msg="skills-graph: regenerate graph and AI Workforce feed from canonical sources [skip ci]"
    fi
    git -C "$top" commit --quiet -m "$msg"

    if remote_git push --quiet "$REMOTE" "HEAD:refs/heads/$BRANCH"; then
      echo "Published $(git -C "$top" rev-parse HEAD) on top of $base."
      return 0
    fi

    now=$(fetch_main)
    if [ "$now" = "$base" ]; then
      die 1 "the push was rejected but $REMOTE/$BRANCH did not move, so this is not a race (token, rule or hook). Not retrying."
    fi
    echo "::notice title=skills-graph publish::$BRANCH moved from $base to $now during attempt $attempt. The scratch commit is discarded and the next attempt rebuilds from the new tip."
    base=$now
  done

  die 3 "$BRANCH moved during each of $attempts attempts, so no generated commit was pushed. The graph and feed on $BRANCH may be stale until the next run: the hourly scheduled run of this workflow, or the next push to $BRANCH that touches their sources, rebuilds them from the latest $BRANCH."
}

main "$@"
