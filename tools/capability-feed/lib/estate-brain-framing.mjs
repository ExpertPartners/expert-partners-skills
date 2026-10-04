// How the feed arrives at HQ, and how to read it back.
//
// HQ reads the feed server-side through the Estate Brain MCP `fetch` tool. That
// tool returns the file wrapped in a one-line header, exactly:
//
//   # <repo>/<path> (<size> KB)\n\n<file content>
//
// (aura tools/mcp-brain-server/server/server.py, fetch(), read 2026-10-03, and
// observed live the same day). JSON.parse on the raw tool text therefore fails.
// A consumer must remove that header first. This is the reference unwrap HQ's
// server-side reader should apply before parsing; test/feed.test.mjs proves it
// against the exact framing and the real generated feed.

const FETCH_HEADER = /^# [^\n]+ \(\d+(?:\.\d+)? KB\)\n\n/;

/** File content from an Estate Brain fetch result: the header removed, or the text unchanged when there is none. */
export function unwrapFetchText(text) {
  return typeof text === 'string' ? text.replace(FETCH_HEADER, '') : text;
}

/** The exact text the Estate Brain fetch tool returns for a file (mirrors server.py). */
export function frameLikeEstateBrain(repo, path, content) {
  const sizeKb = (Math.round((content.length / 1024) * 10) / 10).toFixed(1);
  return `# ${repo}/${path} (${sizeKb} KB)\n\n${content}`;
}
