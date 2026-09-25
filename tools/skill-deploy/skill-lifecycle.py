#!/usr/bin/env python3
"""skill-lifecycle: the read-only lifecycle half of tools/skill-deploy.

Three modes, reached through deploy-skill.sh so the producer stays the one entry
point (deploy-skill.sh --audit-surfaces | --receipt <file> | --receipt-template <id>):

  audit            Walk every local surface a canonical skill can load from on this
                   machine, classify each copy against canonical, resolve which
                   copies actually load, and exit non-zero on any finding. This is
                   the gate aura's repo mounts already had (deploy-skill --verify in
                   aura CI) extended to user mounts, plugin caches, the claude.ai sync
                   mirrors and Cowork's caches.

  receipt-check    Validate a skill release receipt (schema skill-release-receipt/v1)
                   against canonical at a git ref and a live audit. Each surface key
                   climbs CANONICAL -> PACKAGED -> INSTALLED -> DISCOVERED ->
                   BEHAVIOR TESTED, computed from independent evidence slots, never
                   claimed. The receipt verdict is RELEASE COMPLETE only when every
                   intended surface reached BEHAVIOR TESTED, every surface key is
                   decided, and every unintended surface where a copy LOADS carries a
                   disposition. Inert copies (not loading) are reported, never silent.

  receipt-template Print a receipt skeleton for one skill: every surface key present,
                   every evidence slot null, the canonical block filled from the ref.

Canonical is read from a git ref, never from whatever the checkout happens to hold:
by default origin/main of each repo when it resolves, else HEAD; --canonical-ref and
--aura-ref override it, and the value WORKTREE reads the working tree the way the
producer does. The resolved commits are printed and written into the JSON.

What "the same as canonical" means, per surface:
  * pipeline copies (a DEPLOYED COPY header): the whole tree must equal what
    deploy-skill.sh would render today (header date aside), and the committed
    checksums.sha256 must describe the bytes. This is the producer's own --verify.
  * every other copy (plugin caches, claude.ai mirrors, Cowork caches, header-less
    copies): the SKILL.md body, the frontmatter name and description, and every
    supporting file must equal canonical; extra files are drift. Other frontmatter
    keys are ignored because the upload path strips them.

Which copies load (what the audit calls loads=true), each rule from a live source:
  * Claude Code: personal (~/.claude/skills) beats project (.claude/skills) for the
    same name (code.claude.com/docs/en/skills, read 2026-09-24); a plugin copy loads
    only at the installed version and when enabledPlugins does not disable it; a
    claude.ai org plugin is not loaded while a local plugin of the same name is
    installed and enabled ("... on this machine has the same name and takes
    precedence", claude plugin list, 2026-09-24) or when enabledPlugins disables
    "<name>@inline". Account skills and plugin skills are namespaced and all load.
  * Codex: every skill under the user, repo and synced mounts loads, same names are
    not merged (learn.chatgpt.com/docs/build-skills, read 2026-09-24); a plugin cache
    copy loads when plugin@marketplace is enabled in config.toml, and only the newest
    cached version dir of a plugin is taken as active (assumption, stated in output).
  * Cowork: only the signed-in org and account (~/.claude.json oauthAccount) load;
    other org/account caches are inert.

Read-only. Never writes into a mount, a cache or a mirror. Needs python3 and git;
PyYAML is used when present to parse frontmatter.
"""
import argparse
import datetime
import hashlib
import itertools
import json
import os
import re
import subprocess
import sys
from collections import defaultdict

try:
    import yaml  # noqa: F401
except ImportError:  # pragma: no cover - CI and the producer both install PyYAML
    yaml = None

SCHEMA_RECEIPT = "skill-release-receipt/v1"
SCHEMA_AUDIT = "skill-surface-audit/v2"

SURFACES = {
    "claude-code-user-mount":       {"client": "claude-code", "local": True,  "what": "~/.claude/skills (Claude Code personal skills)"},
    "claude-code-project-mount":    {"client": "claude-code", "local": True,  "what": "<aura>/.claude/skills (Claude Code project skills; canonical home for some aura-native skills)"},
    "claude-code-plugin-cache":     {"client": "claude-code", "local": True,  "what": "~/.claude/plugins/cache/<marketplace>/<plugin>/<version> (installed plugins)"},
    "claudeai-org-plugin-sync":     {"client": "claude-code", "local": True,  "what": "~/.claude/plugins/synced/<org_account> (claude.ai org plugins, GitHub sync, one-way download)"},
    "claudeai-account-skills-sync": {"client": "claude-code", "local": True,  "what": "~/.claude/skills/synced/<org_account> (claude.ai account Skills shelf, one-way download)"},
    "codex-user-mount":             {"client": "codex",       "local": True,  "what": "~/.agents/skills (Codex user skills)"},
    "codex-repo-mount":             {"client": "codex",       "local": True,  "what": "<aura>/.agents/skills (Codex repo skills, pipeline copies)"},
    "codex-plugin-cache":           {"client": "codex",       "local": True,  "what": "~/.codex/plugins/cache/<marketplace>/<plugin>/<version> (enabled in config.toml)"},
    "codex-synced-mirror":          {"client": "codex",       "local": True,  "what": "~/.agents/skills/synced/<org_account> (a copy no producer writes; never a release target)"},
    "cowork-account-skills":        {"client": "cowork",      "local": True,  "what": "Claude desktop local-agent-mode-sessions/skills-plugin/<org>/<account>/skills (the account Skills shelf as Cowork loads it)"},
    "cowork-org-plugins":           {"client": "cowork",      "local": True,  "what": "Claude desktop local-agent-mode-sessions/<account>/<org>/rpm/<plugin_id>/skills (org plugins as Cowork loads them)"},
    "claude-chat":                  {"client": "claude-chat", "local": False, "what": "claude.ai chat (loads the account Skills shelf and org plugins; no local read)"},
    "chatgpt-north":                {"client": "chatgpt",     "local": False, "what": "ChatGPT/NORTH (receipt only; nothing local to read)"},
}
LOCAL_SURFACES = [k for k, v in SURFACES.items() if v["local"]]
LADDER = ["CANONICAL", "PACKAGED", "INSTALLED", "DISCOVERED", "BEHAVIOR TESTED"]
PIPELINE_SURFACES = {"claude-code-user-mount", "claude-code-project-mount", "codex-user-mount", "codex-repo-mount"}
PLUGIN_SURFACES = {"claude-code-plugin-cache", "claudeai-org-plugin-sync", "codex-plugin-cache", "cowork-org-plugins"}
ZIP_SURFACES = {"claudeai-account-skills-sync", "cowork-account-skills"}
ANY_PACKAGE_SURFACES = {"claude-chat", "chatgpt-north"}
NEVER_INTENDED = {"codex-synced-mirror"}

JUNK_NAMES = {"checksums.sha256", ".DS_Store"}
HDR = re.compile(r"^# DEPLOYED COPY \((\d{4}-\d{2}-\d{2}), skill-deploy pipeline\): the canonical home is\n# (.+?)\. Deployed at (.+?)\.$", re.M)
HDR_DATE = re.compile(rb"^(# DEPLOYED COPY \()\d{4}-\d{2}-\d{2}(, skill-deploy pipeline\))", re.M)
TITLE_VER = re.compile(r"^# .*?\bv(\d+\.\d+(?:\.\d+)?)\b", re.M)
PRODUCER_VER = re.compile(r"v[0-9]+\.[0-9]+")
CODEX = re.compile(r"\bCodex\b")
PLACEHOLDER = re.compile(r"<[^>]*>|^YYYY|^\s*$")


class Fatal(SystemExit):
    pass


def fatal(msg):
    raise Fatal(f"FATAL: {msg}")


def is_junk(rel):
    parts = rel.split("/")
    base = parts[-1]
    return base in JUNK_NAMES or base.startswith("._") or base.endswith(".pyc") or "__pycache__" in parts[:-1]


def sha256b(data):
    return hashlib.sha256(data).hexdigest()


def dec(data):
    return data.decode("utf-8", "surrogateescape")


# ------------------------------------------------------------------------- git
def git(root, *args, stdin=None, check=True):
    return subprocess.run(["git", "--no-replace-objects", "-C", root, *args], input=stdin,
                          capture_output=True, check=check)


def resolve_ref(root, requested):
    """-> (ref label, commit sha or None for WORKTREE)."""
    if requested == "WORKTREE":
        return "WORKTREE", None
    cands = ["origin/main", "HEAD"] if requested in (None, "", "auto") else [requested]
    for cand in cands:
        r = git(root, "rev-parse", "--verify", "-q", cand + "^{commit}", check=False)
        if r.returncode == 0:
            return cand, dec(r.stdout).strip()
    fatal(f"{root}: canonical ref {' or '.join(cands)} does not resolve")


def cat_blobs(root, shas):
    uniq = list(dict.fromkeys(shas))
    if not uniq:
        return {}
    data = git(root, "cat-file", "--batch", stdin=("\n".join(uniq) + "\n").encode()).stdout
    out, i = {}, 0
    for sha in uniq:
        nl = data.index(b"\n", i)
        head = data[i:nl].split()
        if len(head) < 3 or head[1] != b"blob":
            fatal(f"git cat-file could not read blob {sha} in {root}")
        size = int(head[2])
        out[sha] = data[nl + 1:nl + 1 + size]
        i = nl + 1 + size + 1
    return out


class Tree:
    """Canonical bytes of one repo at a commit, or at the working tree (WORKTREE)."""

    def __init__(self, root, ref, commit):
        self.root, self.ref, self.commit = root, ref, commit

    def files(self, rel_dir):
        rel_dir = rel_dir.strip("/")
        if self.commit is None:
            d = os.path.join(self.root, rel_dir)
            if not os.path.isdir(d):
                return {}
            try:
                out = git(d, "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", ".").stdout
                names = [dec(n) for n in out.split(b"\0") if n]
                names = [n for n in names if os.path.isfile(os.path.join(d, n))]
            except subprocess.CalledProcessError:
                names = [os.path.relpath(os.path.join(dp, f), d) for dp, dn, fn in os.walk(d) for f in fn]
            return {n: open(os.path.join(d, n), "rb").read() for n in sorted(names) if not is_junk(n)}
        out = git(self.root, "ls-tree", "-r", "-z", self.commit, "--", rel_dir + "/").stdout
        blobs = []
        for ent in out.split(b"\0"):
            if not ent:
                continue
            meta, _, path = ent.partition(b"\t")
            mode, typ, sha = meta.split()
            if typ == b"blob":
                rel = dec(path)[len(rel_dir) + 1:]
                if not is_junk(rel):
                    blobs.append((rel, dec(sha)))
        data = cat_blobs(self.root, [s for _, s in blobs])
        return {rel: data[s] for rel, s in sorted(blobs)}

    def read(self, rel_path):
        if self.commit is None:
            p = os.path.join(self.root, rel_path)
            return open(p, "rb").read() if os.path.isfile(p) else None
        r = git(self.root, "cat-file", "-p", f"{self.commit}:{rel_path}", check=False)
        return r.stdout if r.returncode == 0 else None

    def subdirs(self, rel_dir):
        rel_dir = rel_dir.strip("/")
        if self.commit is None:
            d = os.path.join(self.root, rel_dir)
            return sorted(x for x in os.listdir(d) if os.path.isdir(os.path.join(d, x))) if os.path.isdir(d) else []
        out = git(self.root, "ls-tree", "-z", self.commit, "--", rel_dir + "/").stdout
        names = []
        for ent in out.split(b"\0"):
            if ent:
                meta, _, path = ent.partition(b"\t")
                if meta.split()[1] == b"tree":
                    names.append(dec(path).split("/")[-1])
        return sorted(names)


# ----------------------------------------------------------------- frontmatter
def split_frontmatter(text):
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return "", text
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1:])
    return "", text


def body_of(text):
    return split_frontmatter(text)[1]


def name_desc(text):
    fm = split_frontmatter(text)[0]
    data = None
    if yaml is not None:
        try:
            data = yaml.safe_load(fm)
        except Exception:
            data = None
    if not isinstance(data, dict):
        data = {}
        for key in ("name", "description"):
            m = re.search(rf"^{key}:\s*(.*)$", fm, re.M)
            if m:
                data[key] = m.group(1).strip().strip("'\"")
    name = data.get("name")
    desc = data.get("description")
    return (str(name).strip() if name is not None else None,
            " ".join(str(desc).split()) if desc is not None else None)


def title_version(text):
    m = TITLE_VER.search(body_of(text))
    return "v" + m.group(1) if m else None


def deployed_header(text):
    m = HDR.search(split_frontmatter(text)[0])
    return {"deployedAt": m.group(1), "canonical": m.group(2), "stamp": m.group(3)} if m else None


def producer_grep_version(text):
    """What `grep -m1 -oE 'v[0-9]+\\.[0-9]+'` returns inside $(...): every match on the
    first matching line, newline-joined, trailing newlines stripped."""
    for line in text.split("\n"):
        found = PRODUCER_VER.findall(line)
        if found:
            return "\n".join(found)
    return ""


def tree_stamp(files):
    lines = b"".join(sha256b(files[rel]).encode() + b"  ./" + rel.encode("utf-8", "surrogateescape") + b"\n"
                     for rel in sorted(files, key=lambda r: ("./" + r).encode("utf-8", "surrogateescape")))
    return sha256b(lines)[:12]


def fingerprint(text, support):
    name, desc = name_desc(text)
    h = hashlib.sha256()
    for part in (name or "", desc or "", body_of(text)):
        h.update(part.encode("utf-8", "surrogateescape") + b"\0")
    for rel in sorted(support):
        h.update(rel.encode() + b"\0" + support[rel].encode() + b"\0")
    return h.hexdigest()


# ------------------------------------------------------------------- canonical
def origin_repo_name(root):
    r = git(root, "remote", "get-url", "origin", check=False)
    url = dec(r.stdout).strip() if r.returncode == 0 else ""
    top = dec(git(root, "rev-parse", "--show-toplevel").stdout).strip()
    base = os.path.basename(url[:-4] if url.endswith(".git") else url) if url else os.path.basename(top)
    return base.lower()


def make_record(sid, repo_key, rel_dir, tree, status, plugin=None, plugin_version=None, external_repo=None):
    files = tree.files(rel_dir)
    if "SKILL.md" not in files:
        return None
    text = dec(files["SKILL.md"])
    support = {rel: sha256b(b) for rel, b in files.items() if rel != "SKILL.md"}
    name, desc = name_desc(text)
    if repo_key == "eps" and rel_dir.startswith("skills/"):
        label = f"expert-partners-skills {rel_dir}/SKILL.md"
        stamp = producer_grep_version(text) or f"tree sha256 {tree_stamp(files)}"
    elif repo_key == "eps":
        label = f"expert-partners-skills {rel_dir}/SKILL.md"
        stamp = plugin_version or "?"
    else:
        label = f"{external_repo} {rel_dir}/SKILL.md"
        stamp = producer_grep_version(text) or f"tree sha256 {tree_stamp(files)}"
    return {
        "id": sid, "repo": "expert-partners-skills" if repo_key == "eps" else "aura", "repoKey": repo_key,
        "path": f"{rel_dir}/SKILL.md", "dir": rel_dir, "status": status, "plugin": plugin, "pluginVersion": plugin_version,
        "files": files, "text": text, "support": support, "name": name, "description": desc,
        "sha256": sha256b(files["SKILL.md"]), "version": title_version(text), "label": label, "stamp": stamp,
        "fingerprint": fingerprint(text, support),
    }


def load_canonical(eps, aura, eps_ref=None, aura_ref=None, graph_path=None):
    eps = os.path.abspath(eps)
    eref, ecommit = resolve_ref(eps, eps_ref)
    etree = Tree(eps, eref, ecommit)
    graph_bytes = open(graph_path, "rb").read() if graph_path else etree.read("tools/skill-map/skills-graph.json")
    if not graph_bytes:
        fatal("canonical skills graph is missing or empty")
    graph = json.loads(graph_bytes)
    if not graph.get("nodes"):
        fatal("canonical skills graph has no nodes")
    status_by_id, aura_nodes = {}, {}
    graph_nodes = graph.get("nodes", [])
    for n in graph_nodes:
        sid = n["id"]
        if sid in status_by_id:
            fatal(f"graph has duplicate canonical id {sid}")
        status_by_id[sid] = n.get("status", "live")
        repo, rel = n["source"].split(":", 1)
        if repo not in ("eps", "aura"):
            fatal(f"graph source for {sid} has unknown owner {repo}")
        if repo == "aura":
            aura_nodes[sid] = rel
    canon = {}
    for sid in etree.subdirs("skills"):
        rec = make_record(sid, "eps", f"skills/{sid}", etree, status_by_id.get(sid, "live"))
        if rec:
            canon[sid] = rec
    for plugin in etree.subdirs("plugins"):
        pj = etree.read(f"plugins/{plugin}/.claude-plugin/plugin.json")
        pv = json.loads(pj).get("version") if pj else None
        for sid in etree.subdirs(f"plugins/{plugin}/skills"):
            rec = make_record(sid, "eps", f"plugins/{plugin}/skills/{sid}", etree, status_by_id.get(sid, "live"), plugin, pv)
            if not rec:
                continue
            if sid in canon:
                fatal(f"{sid} has two canonical homes in expert-partners-skills ({canon[sid]['path']} and {rec['path']})")
            canon[sid] = rec
    refs = {"eps": {"ref": eref, "commit": ecommit}}
    if aura:
        aura = os.path.abspath(aura)
        aref, acommit = resolve_ref(aura, aura_ref)
        atree = Tree(aura, aref, acommit)
        arepo = origin_repo_name(aura)
        for sid, rel in sorted(aura_nodes.items()):
            rel_dir = os.path.dirname(rel)
            rec = make_record(sid, "aura", rel_dir, atree, status_by_id.get(sid, "live"), external_repo=arepo)
            if not rec:
                continue
            if sid in canon:
                fatal(f"{sid} is canonical in both expert-partners-skills and aura")
            canon[sid] = rec
        refs["aura"] = {"ref": aref, "commit": acommit}
    for sid, rec in canon.items():
        if sid not in status_by_id:
            fatal(f"canonical source {rec['repoKey']}:{rec['path']} is absent from the graph")
    for n in graph_nodes:
        sid = n["id"]
        repo, rel = n["source"].split(":", 1)
        if repo == "aura" and not aura:
            continue
        rec = canon.get(sid)
        if rec is None:
            fatal(f"graph node {sid} has no canonical home at {n['source']}")
        if rec["repoKey"] != repo or rec["path"] != rel:
            fatal(f"graph source mismatch for {sid}: {n['source']} != {rec['repoKey']}:{rec['path']}")
    return canon, refs, set(aura_nodes)


# ----------------------------------------------------------------- copy reads
def copy_files(skill_dir, drop_junk=True):
    out = {}
    for dp, dn, fn in os.walk(skill_dir):
        for f in fn:
            rel = os.path.relpath(os.path.join(dp, f), skill_dir)
            if rel == "checksums.sha256" or (drop_junk and is_junk(rel)):
                continue
            out[rel] = open(os.path.join(dp, f), "rb").read()
    return out


def manifest_state(skill_dir):
    mf = os.path.join(skill_dir, "checksums.sha256")
    if not os.path.isfile(mf):
        return "absent"
    listed = {}
    for line in open(mf, encoding="utf-8"):
        line = line.rstrip("\n")
        if line.strip():
            h, _, p = line.partition("  ")
            listed[os.path.normpath(p)] = h.strip()
    actual = {os.path.normpath(rel): sha256b(b) for rel, b in copy_files(skill_dir, drop_junk=False).items()}
    return "ok" if listed == actual else "fails"


def render_expected(canon):
    """The files deploy-skill.sh would render for this canonical, header date normalised."""
    out = dict(canon["files"])
    lines = canon["text"].split("\n")
    end = next(i for i, l in enumerate(lines[1:], 1) if l.strip() == "---")
    header = [f"# DEPLOYED COPY (DATE, skill-deploy pipeline): the canonical home is",
              f"# {canon['label']}. Deployed at {canon['stamp']}.",
              "# Edit the canonical copy first, then redeploy via tools/skill-deploy."]
    lines[end:end] = header
    out["SKILL.md"] = "\n".join(lines).encode("utf-8", "surrogateescape")
    return out


def pipeline_diff(canon, skill_dir):
    exp = render_expected(canon)
    got = copy_files(skill_dir, drop_junk=False)
    if "SKILL.md" in got:
        got["SKILL.md"] = HDR_DATE.sub(rb"\1DATE\2", got["SKILL.md"])
    diffs = []
    for rel in sorted(set(exp) | set(got)):
        if rel not in got:
            diffs.append(f"missing {rel}")
        elif rel not in exp:
            diffs.append(f"extra file {rel}")
        elif exp[rel] != got[rel]:
            diffs.append(f"{rel} differs from a fresh render")
    return diffs


def content_diff(canon, files):
    diffs = []
    sk = files.get("SKILL.md")
    if sk is None:
        return ["SKILL.md missing"]
    text = dec(sk)
    name, desc = name_desc(text)
    if body_of(text) != body_of(canon["text"]):
        diffs.append("SKILL.md body differs")
    if name != canon["name"]:
        diffs.append("frontmatter name differs")
    if desc != canon["description"]:
        diffs.append("frontmatter description differs")
    for rel in sorted(canon["files"]):
        if rel == "SKILL.md":
            continue
        if rel not in files:
            diffs.append(f"missing supporting file {rel}")
        elif files[rel] != canon["files"][rel]:
            diffs.append(f"supporting file {rel} differs")
    for rel in sorted(files):
        if rel not in canon["files"]:
            diffs.append(f"extra file {rel}")
    return diffs


def reverse_variants(line):
    s = line.replace("AGENTS.md", "CLAUDE.md")
    occ = [m.start() for m in CODEX.finditer(s)]
    if not occ:
        return {s}
    choices = ("Claude Code", "Claude", "claude")
    out = set()
    if len(occ) <= 4:
        for combo in itertools.product(choices, repeat=len(occ)):
            pieces, last = [], 0
            for pos, rep in zip(occ, combo):
                pieces.append(s[last:pos])
                pieces.append(rep)
                last = pos + len("Codex")
            pieces.append(s[last:])
            out.add("".join(pieces))
    else:
        out.update(CODEX.sub(c, s) for c in choices)
    return out


def is_rewritten(copy_text, canon_text):
    """A Claude-to-Codex text substitution of canonical: the copy carries more Codex or
    AGENTS.md tokens than canonical, and reversing the substitution turns a quarter or
    more of its changed Codex lines back into canonical lines."""
    def tokens(t):
        return len(CODEX.findall(t)) + t.count("AGENTS.md")
    if tokens(copy_text) <= tokens(canon_text):
        return False
    canon_lines = {l.strip() for l in canon_text.split("\n")}
    tried = hits = 0
    for line in copy_text.split("\n"):
        s = line.strip()
        if not s or s in canon_lines or ("Codex" not in s and "AGENTS.md" not in s):
            continue
        tried += 1
        if any(v in canon_lines for v in reverse_variants(s)):
            hits += 1
    return hits >= 1 and hits * 4 >= tried


def classify(canon, skill_dir, surface):
    files = copy_files(skill_dir)
    text = dec(files.get("SKILL.md", b""))
    hdr = deployed_header(text) if text else None
    rec = {"surface": surface, "path": os.path.join(skill_dir, "SKILL.md"),
           "sha256": sha256b(files["SKILL.md"])[:12] if "SKILL.md" in files else None,
           "version": title_version(text) if text else None,
           "rewritten": bool(text) and is_rewritten(text, canon["text"]),
           "fingerprint": fingerprint(text, {r: sha256b(b) for r, b in files.items() if r != "SKILL.md"}) if text else None,
           "detail": ""}
    if hdr:
        rec["deployedHeader"] = hdr
        if hdr["canonical"] != canon["label"]:
            rec["state"] = "ORPHAN"
            rec["detail"] = f"DEPLOYED COPY header names {hdr['canonical']!r}; canonical for this id is {canon['label']!r}"
            return rec
        ms = manifest_state(skill_dir)
        rec["manifest"] = ms
        if ms != "ok":
            rec["state"] = "HAND-EDITED"
            rec["detail"] = f"checksums.sha256 {ms}"
        else:
            diffs = pipeline_diff(canon, skill_dir)
            if diffs:
                rec["state"] = "STALE"
                rec["detail"] = (f"pipeline copy stamped {hdr['stamp']} on {hdr['deployedAt']}; the producer would stamp "
                                 f"{canon['stamp']} today; " + "; ".join(diffs[:6]))
            else:
                rec["state"] = "CURRENT"
    else:
        diffs = content_diff(canon, files)
        if surface in PIPELINE_SURFACES:
            rec["state"] = "UNTRACKED-COPY-STALE" if diffs else "UNTRACKED-COPY"
            rec["detail"] = "no DEPLOYED COPY header, not produced by the pipeline" + ("; " + "; ".join(diffs[:6]) if diffs else "")
        else:
            rec["state"] = "STALE" if diffs else "CURRENT"
            rec["detail"] = "; ".join(diffs[:6])
    if rec["rewritten"]:
        rec["detail"] = (rec["detail"] + "; " if rec["detail"] else "") + "Claude-to-Codex text rewrite of canonical"
    return rec


# ---------------------------------------------------------------- local state
def walk_mount(root):
    out = {}
    if os.path.isdir(root):
        for d in sorted(os.listdir(root)):
            if d.lower() != "synced" and os.path.isfile(os.path.join(root, d, "SKILL.md")):
                out[d] = os.path.join(root, d)
    return out


def version_key(v):
    return [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", v)]


def claude_settings(home, aura):
    enabled = {}
    paths = [os.path.join(home, ".claude", "settings.json"), os.path.join(home, ".claude", "settings.local.json")]
    if aura:
        paths += [os.path.join(aura, ".claude", "settings.json"), os.path.join(aura, ".claude", "settings.local.json")]
    for p in paths:
        if os.path.isfile(p):
            try:
                enabled.update(json.load(open(p)).get("enabledPlugins") or {})
            except (ValueError, OSError):
                pass
    return enabled


def installed_claude_plugins(home):
    p = os.path.join(home, ".claude", "plugins", "installed_plugins.json")
    out = {}
    if os.path.isfile(p):
        for key, entries in (json.load(open(p)).get("plugins") or {}).items():
            if entries:
                out[key] = entries[0].get("version")
    return out


def codex_enabled(codex_home):
    p = os.path.join(codex_home, "config.toml")
    out = set()
    if os.path.isfile(p):
        text = open(p, encoding="utf-8").read()
        for m in re.finditer(r'\[plugins\."([^"]+)"\]\s*\n\s*enabled\s*=\s*true', text):
            out.add(m.group(1))
    return out


def active_cowork(home, app):
    p = os.path.join(home, ".claude.json")
    if os.path.isfile(p):
        try:
            oa = json.load(open(p)).get("oauthAccount") or {}
            if oa.get("organizationUuid") and oa.get("accountUuid"):
                return oa["organizationUuid"], oa["accountUuid"], "~/.claude.json oauthAccount"
        except (ValueError, OSError):
            pass
    root = os.path.join(app, "local-agent-mode-sessions", "skills-plugin")
    best = None
    if os.path.isdir(root):
        for org in os.listdir(root):
            for acct in os.listdir(os.path.join(root, org)) if os.path.isdir(os.path.join(root, org)) else []:
                d = os.path.join(root, org, acct)
                if os.path.isdir(d):
                    t = os.path.getmtime(d)
                    if best is None or t > best[0]:
                        best = (t, org, acct)
    if best:
        return best[1], best[2], "most recently written skills-plugin cache (no ~/.claude.json)"
    return None, None, "none found"


def collect_audit(args):
    home = os.path.abspath(args.home)
    app = os.path.abspath(args.app_support) if args.app_support else os.path.join(home, "Library", "Application Support", "Claude")
    codex_home = os.path.abspath(args.codex_home) if args.codex_home else os.path.join(home, ".codex")
    aura = os.path.abspath(args.aura) if args.aura else None
    canon, refs, _ = load_canonical(args.eps, aura, args.canonical_ref, args.aura_ref, args.graph)
    only = None
    if args.only:
        only = [x for x in args.only.split(",") if x]
        unknown = [x for x in only if x not in canon]
        if unknown:
            fatal("--only names no canonical skill: " + ", ".join(unknown))
        only = set(only)
    wanted = sorted(canon) if only is None else sorted(only)
    enabled = claude_settings(home, aura)
    installed = installed_claude_plugins(home)
    local_enabled_plugins = {k.split("@")[0] for k in installed if enabled.get(k, True) is not False}
    cx_enabled = codex_enabled(codex_home)
    c_org, c_acct, c_how = active_cowork(home, app)

    copies = defaultdict(list)

    def add(sid, skill_dir, surface, loads=True, why=None, **extra):
        if sid not in canon or sid not in wanted:
            return
        rec = classify(canon[sid], skill_dir, surface)
        rec.update({"loads": loads, "inertReason": None if loads else why})
        rec.update(extra)
        copies[sid].append(rec)

    for sid, d in walk_mount(os.path.join(home, ".claude", "skills")).items():
        add(sid, d, "claude-code-user-mount")
    for sid, d in walk_mount(os.path.join(home, ".agents", "skills")).items():
        add(sid, d, "codex-user-mount")
    if aura:
        for sid, d in walk_mount(os.path.join(aura, ".claude", "skills")).items():
            if sid not in canon or sid not in wanted:
                continue
            c = canon[sid]
            if c["repoKey"] == "aura" and c["dir"] == f".claude/skills/{sid}":
                files = copy_files(d)
                live_fp = fingerprint(dec(files.get("SKILL.md", b"")), {r: sha256b(b) for r, b in files.items() if r != "SKILL.md"})
                state = "CANONICAL" if live_fp == c["fingerprint"] and files == c["files"] else "CANONICAL-UNMERGED"
                copies[sid].append({"surface": "claude-code-project-mount", "path": os.path.join(d, "SKILL.md"),
                                    "sha256": sha256b(files["SKILL.md"])[:12], "version": title_version(dec(files["SKILL.md"])),
                                    "state": state, "rewritten": False, "fingerprint": live_fp, "loads": True, "inertReason": None,
                                    "detail": "" if state == "CANONICAL" else f"working tree differs from canonical at {refs['aura']['ref']}"})
            else:
                add(sid, d, "claude-code-project-mount")
        for sid, d in walk_mount(os.path.join(aura, ".agents", "skills")).items():
            add(sid, d, "codex-repo-mount")
    # Claude Code plugin cache: loads only at the installed version, and only when enabled
    croot = os.path.join(home, ".claude", "plugins", "cache")
    for mkt in sorted(os.listdir(croot)) if os.path.isdir(croot) else []:
        for plugin in sorted(os.listdir(os.path.join(croot, mkt))) if os.path.isdir(os.path.join(croot, mkt)) else []:
            key = f"{plugin}@{mkt}"
            pdir = os.path.join(croot, mkt, plugin)
            for ver in sorted(os.listdir(pdir)) if os.path.isdir(pdir) else []:
                for sid, d in walk_mount(os.path.join(pdir, ver, "skills")).items():
                    if installed.get(key) != ver:
                        add(sid, d, "claude-code-plugin-cache", False, f"not the installed version ({installed.get(key) or 'not installed'})", plugin=plugin, pluginVersion=ver, marketplace=mkt)
                    elif enabled.get(key, True) is False:
                        add(sid, d, "claude-code-plugin-cache", False, "plugin disabled in enabledPlugins", plugin=plugin, pluginVersion=ver, marketplace=mkt)
                    else:
                        add(sid, d, "claude-code-plugin-cache", True, plugin=plugin, pluginVersion=ver, marketplace=mkt)
    # claude.ai org plugins synced into Claude Code
    sroot = os.path.join(home, ".claude", "plugins", "synced")
    for acct in sorted(os.listdir(sroot)) if os.path.isdir(sroot) else []:
        aroot = os.path.join(sroot, acct)
        if not os.path.isdir(aroot):
            continue
        for d in sorted(os.listdir(aroot)):
            pj = os.path.join(aroot, d, ".claude-plugin", "plugin.json")
            if not os.path.isfile(pj):
                continue
            pjson = json.load(open(pj))
            pname = pjson.get("name", d)
            meta = {}
            mp = os.path.join(aroot, d + ".meta.json")
            if os.path.isfile(mp):
                try:
                    meta = json.load(open(mp))
                except ValueError:
                    meta = {}
            if pname in local_enabled_plugins:
                loads, why = False, f"shadowed by the locally installed plugin {pname}"
            elif enabled.get(f"{pname}@inline", enabled.get(f"{pname}@synced", True)) is False:
                loads, why = False, f"disabled in enabledPlugins ({pname}@inline)"
            else:
                loads, why = True, None
            for sid, sd in walk_mount(os.path.join(aroot, d, "skills")).items():
                add(sid, sd, "claudeai-org-plugin-sync", loads, why, plugin=pname, pluginVersion=pjson.get("version"), marketplace=meta.get("marketplace_name"))
    # claude.ai account skills synced into Claude Code (namespaced anthropic-skills:<name>)
    kroot = os.path.join(home, ".claude", "skills", "synced")
    for acct in sorted(os.listdir(kroot)) if os.path.isdir(kroot) else []:
        meta = {}
        mp = os.path.join(kroot, acct, "manifest.json")
        if os.path.isfile(mp):
            try:
                meta = {s.get("name"): s for s in json.load(open(mp)).get("skills", [])}
            except (ValueError, OSError):
                meta = {}
        for sid, d in walk_mount(os.path.join(kroot, acct)).items():
            add(sid, d, "claudeai-account-skills-sync", updatedAt=(meta.get(sid) or {}).get("updatedAt"))
    # Codex synced mirror (a copy nothing produces)
    xroot = os.path.join(home, ".agents", "skills", "synced")
    for acct in sorted(os.listdir(xroot)) if os.path.isdir(xroot) else []:
        for sid, d in walk_mount(os.path.join(xroot, acct)).items():
            add(sid, d, "codex-synced-mirror")
    # Codex plugin caches: enabled plugin@marketplace, newest cached version only
    xcroot = os.path.join(codex_home, "plugins", "cache")
    for mkt in sorted(os.listdir(xcroot)) if os.path.isdir(xcroot) else []:
        for plugin in sorted(os.listdir(os.path.join(xcroot, mkt))) if os.path.isdir(os.path.join(xcroot, mkt)) else []:
            pdir = os.path.join(xcroot, mkt, plugin)
            vers = sorted((v for v in os.listdir(pdir) if os.path.isdir(os.path.join(pdir, v))), key=version_key) if os.path.isdir(pdir) else []
            for ver in vers:
                for sid, d in walk_mount(os.path.join(pdir, ver, "skills")).items():
                    if f"{plugin}@{mkt}" not in cx_enabled:
                        add(sid, d, "codex-plugin-cache", False, "plugin not enabled in config.toml", plugin=plugin, pluginVersion=ver, marketplace=mkt)
                    elif ver != vers[-1]:
                        add(sid, d, "codex-plugin-cache", False, f"older cached version (newest {vers[-1]} taken as active)", plugin=plugin, pluginVersion=ver, marketplace=mkt)
                    else:
                        add(sid, d, "codex-plugin-cache", True, plugin=plugin, pluginVersion=ver, marketplace=mkt)
    # Cowork caches: only the signed-in org and account load
    lroot = os.path.join(app, "local-agent-mode-sessions")
    kp = os.path.join(lroot, "skills-plugin")
    for org in sorted(os.listdir(kp)) if os.path.isdir(kp) else []:
        for acct in sorted(os.listdir(os.path.join(kp, org))) if os.path.isdir(os.path.join(kp, org)) else []:
            active = (org, acct) == (c_org, c_acct)
            for sid, d in walk_mount(os.path.join(kp, org, acct, "skills")).items():
                add(sid, d, "cowork-account-skills", active, None if active else "inactive Cowork org/account", org=org, account=acct)
    for acct in sorted(os.listdir(lroot)) if os.path.isdir(lroot) else []:
        if acct == "skills-plugin" or not os.path.isdir(os.path.join(lroot, acct)):
            continue
        for org in sorted(os.listdir(os.path.join(lroot, acct))):
            rpm = os.path.join(lroot, acct, org, "rpm")
            if not os.path.isdir(rpm):
                continue
            active = (org, acct) == (c_org, c_acct)
            for pid in sorted(os.listdir(rpm)):
                pj = os.path.join(rpm, pid, ".claude-plugin", "plugin.json")
                if not os.path.isfile(pj):
                    continue
                pjson = json.load(open(pj))
                for sid, d in walk_mount(os.path.join(rpm, pid, "skills")).items():
                    add(sid, d, "cowork-org-plugins", active, None if active else "inactive Cowork org/account",
                        plugin=pjson.get("name"), pluginVersion=pjson.get("version"), org=org, account=acct)

    # Claude Code precedence: personal beats project for the same name
    for sid, cs in copies.items():
        personal = [r for r in cs if r["surface"] == "claude-code-user-mount"]
        if personal:
            for r in cs:
                if r["surface"] == "claude-code-project-mount" and r["loads"]:
                    r["loads"] = False
                    r["inertReason"] = f"shadowed by the personal skill {personal[0]['path']} (personal beats project)"
                    r["shadowedBy"] = personal[0]["path"]

    findings = []
    per_skill = {}
    for sid in wanted:
        c = canon[sid]
        cs = copies.get(sid, [])
        loaded = [r for r in cs if r["loads"]]
        for r in cs:
            if r.get("shadowedBy") and r["fingerprint"] != next(p["fingerprint"] for p in cs if p["path"] == r["shadowedBy"]):
                findings.append({"id": sid, "kind": "SHADOWED", "surface": r["surface"], "path": r["path"],
                                 "detail": f"{r['state']} copy never runs; the personal copy {r['shadowedBy']} runs instead and differs"})
            if r["state"] == "ORPHAN" or (r["loads"] and r["state"] in ("STALE", "HAND-EDITED", "UNTRACKED-COPY", "UNTRACKED-COPY-STALE", "CANONICAL-UNMERGED")):
                findings.append({"id": sid, "kind": r["state"], "surface": r["surface"], "path": r["path"], "detail": r["detail"]})
            if r["loads"] and r["rewritten"]:
                findings.append({"id": sid, "kind": "REWRITTEN", "surface": r["surface"], "path": r["path"],
                                 "detail": "Claude-to-Codex text substitution of canonical; drift, never an adaptation"})
        dups = {}
        for client in ("claude-code", "codex", "cowork"):
            lc = [r for r in loaded if SURFACES[r["surface"]]["client"] == client]
            if len(lc) > 1:
                distinct = len({r["fingerprint"] for r in lc})
                dups[client] = {"copies": [{"surface": r["surface"], "path": r["path"], "state": r["state"], "version": r["version"]} for r in lc],
                                "distinctContents": distinct}
                findings.append({"id": sid, "kind": "DUPLICATE-IDENTITY", "client": client, "divergent": distinct > 1,
                                 "detail": f"{len(lc)} copies load in {client}, {distinct} distinct content(s)"})
        if c["status"] == "retired":
            for r in loaded:
                findings.append({"id": sid, "kind": "RETIRED-LOADING", "surface": r["surface"], "path": r["path"],
                                 "detail": "graph status retired, yet this copy loads"})
        per_skill[sid] = {"canonical": {"repo": c["repo"], "path": c["path"], "version": c["version"], "stamp": c["stamp"],
                                        "status": c["status"], "plugin": c["plugin"], "pluginVersion": c["pluginVersion"],
                                        "sha256": c["sha256"][:12]},
                          "copies": [{k: v for k, v in r.items() if k not in ("deployedHeader", "fingerprint")} for r in cs],
                          "duplicates": dups}
    if only is None:
        for mount, surface in ((os.path.join(home, ".claude", "skills"), "claude-code-user-mount"),
                               (os.path.join(home, ".agents", "skills"), "codex-user-mount")):
            for sid, d in walk_mount(mount).items():
                if sid in canon:
                    continue
                hdr = deployed_header(dec(open(os.path.join(d, "SKILL.md"), "rb").read()))
                if hdr:
                    findings.append({"id": sid, "kind": "ORPHAN", "surface": surface, "path": os.path.join(d, "SKILL.md"),
                                     "detail": f"DEPLOYED COPY header names {hdr['canonical']!r}; no canonical skill owns this id"})
    by_kind = defaultdict(int)
    for f in findings:
        by_kind[f["kind"]] += 1
    return {"schema": SCHEMA_AUDIT, "canonicalRefs": refs, "home": home, "activeCowork": {"org": c_org, "account": c_acct, "how": c_how},
            "canonicalCount": len(canon), "auditedCount": len(wanted), "surfacesObserved": LOCAL_SURFACES,
            "skills": per_skill, "findings": findings, "summary": {"findings": len(findings), "byKind": dict(sorted(by_kind.items()))}}


def run_audit(args):
    res = collect_audit(args)
    refs = ", ".join(f"{k} {v['ref']} {(v['commit'] or 'working tree')[:12]}" for k, v in res["canonicalRefs"].items())
    print(f"canonical: {refs}; active Cowork: {res['activeCowork']['org']} / {res['activeCowork']['account']} ({res['activeCowork']['how']})")
    flagged = {f["id"] for f in res["findings"]}
    for sid, rec in res["skills"].items():
        if args.quiet and sid not in flagged:
            continue
        c = rec["canonical"]
        print(f"{sid} [{c['repo']} {c['path']} {c['version'] or c['stamp']} status={c['status']}]")
        for r in rec["copies"]:
            inert = "" if r["loads"] else f" (inert: {r['inertReason']})"
            rw = " REWRITTEN" if r.get("rewritten") else ""
            print(f"  {r['surface']}: {r['state']}{inert}{rw} {r.get('version') or ''} {r['path']}")
    print(f"audit-surfaces: {res['auditedCount']} of {res['canonicalCount']} canonical skill(s) audited, {res['summary']['findings']} finding(s)"
          + (f" {res['summary']['byKind']}" if res["findings"] else ""))
    if args.json:
        with open(args.json, "w") as f:
            json.dump(res, f, indent=2)
    return 1 if res["findings"] and not args.report_only else 0


# --------------------------------------------------------------------- receipt
def valid_date(s):
    if not isinstance(s, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return False
    try:
        datetime.date.fromisoformat(s)
        return True
    except ValueError:
        return False


def real_text(s):
    return isinstance(s, str) and not PLACEHOLDER.search(s.strip() if isinstance(s, str) else "")


def slot_problem(slot, fields):
    if not isinstance(slot, dict):
        return "slot missing"
    if not valid_date(slot.get("verifiedAt")):
        return "verifiedAt must be a real YYYY-MM-DD date"
    for f in fields:
        if not real_text(slot.get(f)):
            return f"{f} must be filled with real text (no placeholder)"
    return None


def receipt_template(args):
    aura = os.path.abspath(args.aura) if args.aura else None
    canon, refs, aura_ids = load_canonical(args.eps, aura, args.canonical_ref, args.aura_ref, args.graph)
    sid = args.skill
    if sid not in canon:
        if sid in aura_ids and not aura:
            fatal(f"{sid} is aura-native; pass --aura <aura checkout> (or set AURA_PATH)")
        fatal(f"{sid} is not a canonical skill")
    c = canon[sid]
    commit = refs[c["repoKey"]]["commit"]
    tmpl = {
        "schema": SCHEMA_RECEIPT, "skill": sid,
        "canonical": {"repo": c["repo"], "path": c["path"], "commit": commit, "skillmdSha256": c["sha256"], "version": c["version"]},
        "packaged": [],
        "surfaces": {k: {"intended": None, "reason": None, "installed": None, "discovered": None, "behaviorTested": None, "disposition": None} for k in SURFACES},
        "_help": {
            "packaged": "one entry per artifact: {kind: upload-zip, artifact: <zip filename>, sha256: <64 hex>, builtFrom: <canonical.commit>} or {kind: plugin-version, artifact: <plugin>@<version>, builtFrom: <canonical.commit>}",
            "surfaces": "every key: intended true or false and a reason; a loading copy on an unintended surface needs a disposition",
            "installed": "{verifiedAt: YYYY-MM-DD, method, evidence}",
            "discovered": "{verifiedAt: YYYY-MM-DD, method, evidence}",
            "behaviorTested": "{verifiedAt: YYYY-MM-DD, fixture, result: pass | fail, evidence}",
            "plugin": c["plugin"], "pluginVersion": c["pluginVersion"],
        },
    }
    print(json.dumps(tmpl, indent=2))
    return 0


def receipt_check(args):
    aura = os.path.abspath(args.aura) if args.aura else None
    try:
        raw = sys.stdin.read() if args.receipt == "-" else open(args.receipt).read()
        rc = json.loads(raw)
    except (OSError, ValueError) as e:
        fatal(f"cannot read receipt {args.receipt}: {e}")
    canon, refs, aura_ids = load_canonical(args.eps, aura, args.canonical_ref, args.aura_ref, args.graph)
    problems = []
    if rc.get("schema") != SCHEMA_RECEIPT:
        problems.append(f"schema must be {SCHEMA_RECEIPT}, got {rc.get('schema')!r}")
    sid = rc.get("skill")
    if sid not in canon:
        if sid in aura_ids and not aura:
            problems.append(f"{sid} is aura-native; pass --aura <aura checkout> (or set AURA_PATH) to check its receipt")
        else:
            problems.append(f"skill {sid!r} has no canonical home (missing canonical home)")
        print("receipt-check: NOT COMPLETE")
        for p in problems:
            print(f"  FAIL: {p}")
        return 1
    c = canon[sid]
    ref = refs[c["repoKey"]]
    root = os.path.abspath(args.eps) if c["repoKey"] == "eps" else aura
    if c["status"] != "live":
        why = {"designed": "not yet canonical; promote it before any release",
               "benched": "benched (aura ADR 0045 for Moxie); no release while benched",
               "retired": "retired; a retired skill has removals, not a release"}.get(c["status"], f"status {c['status']}")
        problems.append(f"{sid} is {why}")
    can = rc.get("canonical") if isinstance(rc.get("canonical"), dict) else {}
    if can.get("path") != c["path"] or str(can.get("repo") or "").lower() != c["repo"]:
        problems.append(f"receipt canonical {can.get('repo')} {can.get('path')} does not match live canonical {c['repo']} {c['path']}")
    commit = str(can.get("commit") or "")
    if not re.fullmatch(r"[0-9a-f]{7,40}", commit):
        problems.append("canonical.commit must be the merged commit the release was built from")
    else:
        blob = git(root, "cat-file", "-p", f"{commit}:{c['path']}", check=False)
        if blob.returncode != 0:
            problems.append(f"canonical.commit {commit} does not contain {c['path']} in {c['repo']}")
        elif sha256b(blob.stdout) != can.get("skillmdSha256"):
            problems.append(f"canonical.skillmdSha256 does not match {c['path']} at {commit}")
    if not re.fullmatch(r"[0-9a-f]{64}", str(can.get("skillmdSha256") or "")):
        problems.append("canonical.skillmdSha256 is required (64 hex)")
    elif can.get("skillmdSha256") != c["sha256"]:
        problems.append(f"receipt canonical SKILL.md sha256 {str(can.get('skillmdSha256'))[:12]} differs from canonical at {ref['ref']} "
                        f"{c['sha256'][:12]} (stale receipt: canonical moved since this release)")
    if c["version"] and can.get("version") != c["version"]:
        problems.append(f"canonical.version {can.get('version')!r} does not match the live version line {c['version']}")

    kinds = set()
    for i, p in enumerate(rc.get("packaged") or []):
        if not isinstance(p, dict):
            problems.append(f"packaged[{i}] must be an object")
            continue
        k = p.get("kind")
        if p.get("builtFrom") != can.get("commit"):
            problems.append(f"packaged[{i}].builtFrom {p.get('builtFrom')!r} must equal canonical.commit")
            continue
        if k == "upload-zip":
            if not re.fullmatch(r"[0-9a-f]{64}", str(p.get("sha256") or "")) or not real_text(p.get("artifact")):
                problems.append(f"packaged[{i}] upload-zip needs a real artifact name and a 64-hex sha256")
                continue
            kinds.add("upload-zip")
        elif k == "plugin-version":
            want = f"{c['plugin']}@{c['pluginVersion']}" if c["plugin"] else None
            if not want:
                problems.append(f"packaged[{i}] plugin-version given for {sid}, which no plugin carries")
                continue
            if p.get("artifact") != want:
                problems.append(f"packaged[{i}] plugin-version artifact {p.get('artifact')!r} must be {want} (plugin.json at {ref['ref']})")
                continue
            kinds.add("plugin-version")
        else:
            problems.append(f"packaged[{i}].kind must be upload-zip or plugin-version, got {k!r}")

    surfaces = rc.get("surfaces") if isinstance(rc.get("surfaces"), dict) else {}
    missing = [k for k in SURFACES if k not in surfaces]
    if missing:
        problems.append("every surface key must be present and decided (intended true or false with a reason): missing " + ", ".join(missing))
    unknown_keys = [k for k in surfaces if k not in SURFACES]
    if unknown_keys:
        problems.append("unknown surface keys: " + ", ".join(unknown_keys))

    audit = collect_audit(argparse.Namespace(eps=args.eps, aura=args.aura, home=args.home, app_support=args.app_support,
                                             codex_home=args.codex_home, graph=args.graph, only=sid,
                                             canonical_ref=args.canonical_ref, aura_ref=args.aura_ref))
    live = audit["skills"].get(sid, {})
    by_surface = defaultdict(list)
    for r in live.get("copies", []):
        by_surface[r["surface"]].append(r)
    surface_findings = defaultdict(list)
    divergent_clients = set()
    for f in audit["findings"]:
        if f.get("surface"):
            surface_findings[f["surface"]].append(f["kind"])
        if f["kind"] == "DUPLICATE-IDENTITY" and f.get("divergent"):
            divergent_clients.add(f["client"])

    rows = []
    reached = {}
    for key in SURFACES:
        s = surfaces.get(key)
        if key in surfaces and not isinstance(s, dict):
            problems.append(f"{key}: entry must be an object with intended and reason, got {type(s).__name__}")
            rows.append((key, "UNDECIDED", "entry is not an object"))
            continue
        if s is None:
            rows.append((key, "UNDECIDED", "no entry"))
            continue
        intended = s.get("intended")
        if intended not in (True, False):
            problems.append(f"{key}: intended must be true or false, got {intended!r}")
            rows.append((key, "UNDECIDED", "intended not decided"))
            continue
        if not real_text(s.get("reason")):
            problems.append(f"{key}: reason is required")
        cs = by_surface.get(key, [])
        loaded = [r for r in cs if r["loads"]]
        inert = [r for r in cs if not r["loads"]]
        inert_note = f"; inert copy present: {', '.join(sorted({r['state'] for r in inert}))}" if inert else ""
        if not intended:
            if loaded and not real_text(s.get("disposition")):
                problems.append(f"{key}: not intended, yet a copy loads there ({loaded[0]['state']} {loaded[0]['path']}); a disposition is required")
            note = (f"loading copy: {loaded[0]['state']} -> {s.get('disposition') or 'DISPOSITION MISSING'}" if loaded else "no loading copy") + inert_note
            rows.append((key, "NOT INTENDED", note))
            continue
        if key in NEVER_INTENDED:
            problems.append(f"{key}: an unsourced mirror is never a release target; intend the surface it mirrors instead")
            rows.append((key, "REFUSED", "never a release target"))
            continue
        if key in PLUGIN_SURFACES and not c["plugin"]:
            problems.append(f"{key}: {sid} is not plugin-carried, so no plugin surface can carry it")
            rows.append((key, "REFUSED", "not plugin-carried"))
            continue
        state, notes = "CANONICAL", []
        need = ("plugin-version" if key in PLUGIN_SURFACES else "upload-zip" if key in ZIP_SURFACES
                else "any" if key in ANY_PACKAGE_SURFACES else None)
        if need and not (kinds if need == "any" else kinds & {need}):
            notes.append(f"no valid {need if need != 'any' else ''} package recorded".replace("  ", " "))
        else:
            state = "PACKAGED"
            prob = slot_problem(s.get("installed"), ("method", "evidence"))
            if prob:
                notes.append(f"installed: {prob}")
            else:
                ok = True
                if SURFACES[key]["local"]:
                    if not loaded:
                        ok = False
                        notes.append("no loading copy on this surface" + (f" ({inert[0]['inertReason']})" if inert else ""))
                    else:
                        bad = sorted({r["state"] for r in loaded if r["state"] not in ("CURRENT", "CANONICAL")})
                        if bad:
                            ok = False
                            notes.append("a loading copy is " + ", ".join(bad))
                        if any(r.get("rewritten") for r in loaded):
                            ok = False
                            notes.append("a loading copy is a Claude-to-Codex rewrite")
                        extra = sorted(set(surface_findings.get(key, [])) - {"STALE", "HAND-EDITED", "UNTRACKED-COPY", "UNTRACKED-COPY-STALE", "REWRITTEN", "CANONICAL-UNMERGED"})
                        if extra:
                            ok = False
                            notes.append("audit findings on this surface: " + ", ".join(extra))
                    if SURFACES[key]["client"] in divergent_clients:
                        ok = False
                        notes.append(f"divergent duplicate identity in {SURFACES[key]['client']}: another loading copy differs")
                if ok:
                    state = "INSTALLED"
                    prob = slot_problem(s.get("discovered"), ("method", "evidence"))
                    if prob:
                        notes.append(f"discovered: {prob}")
                    else:
                        state = "DISCOVERED"
                        beh = s.get("behaviorTested")
                        prob = slot_problem(beh, ("fixture", "evidence"))
                        result = str((beh or {}).get("result") or "").lower() if isinstance(beh, dict) else ""
                        if prob:
                            notes.append(f"behaviorTested: {prob}")
                        elif result == "pass":
                            state = "BEHAVIOR TESTED"
                        elif result == "fail":
                            notes.append("behavior fixture failed")
                        else:
                            notes.append("behaviorTested.result must be pass or fail")
        reached[key] = state
        rows.append((key, state, "; ".join(notes) + inert_note))
        if state != "BEHAVIOR TESTED":
            problems.append(f"{key}: intended surface reached {state} only ({'; '.join(notes) or 'see row'})")
    if not reached:
        problems.append("no surface is intended; a release names at least one surface")
    width = max(len(k) for k in SURFACES)
    cref = f"{ref['ref']} {(ref['commit'] or 'working tree')[:12]}"
    print(f"release receipt: {sid} ({c['repo']} {c['path']} {c['version'] or c['stamp']}; canonical at {cref})")
    for key, state, note in rows:
        print(f"  {key.ljust(width)}  {state.ljust(15)}  {note}")
    if problems:
        print("receipt-check: NOT COMPLETE")
        for p in problems:
            print(f"  FAIL: {p}")
        return 1
    print("receipt-check: RELEASE COMPLETE, every intended surface installed, discovered and behavior tested; every loading copy elsewhere dispositioned")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="skill-lifecycle.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--eps", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."), help="expert-partners-skills checkout (default: this repo)")
        p.add_argument("--aura", default=os.environ.get("AURA_PATH"), help="aura checkout for aura-native canonicals and repo mounts (default: $AURA_PATH)")
        p.add_argument("--canonical-ref", default="auto", help="git ref for expert-partners-skills canonical (default: origin/main, else HEAD; WORKTREE reads the working tree)")
        p.add_argument("--aura-ref", default="auto", help="git ref for aura canonical (default: origin/main, else HEAD; WORKTREE reads the working tree)")
        p.add_argument("--graph", default=None, help="skills-graph.json file (default: the graph at the canonical ref)")
        p.add_argument("--home", default=os.path.expanduser("~"), help="home directory holding .claude, .agents, .codex (default: $HOME)")
        p.add_argument("--app-support", default=None, help="Claude desktop Application Support dir (default: <home>/Library/Application Support/Claude)")
        p.add_argument("--codex-home", default=None, help="Codex home (default: <home>/.codex)")

    a = sub.add_parser("audit", help="classify every local copy of every canonical skill")
    common(a)
    a.add_argument("--only", default=None, help="comma-separated skill ids (unknown ids are an error)")
    a.add_argument("--json", default=None, help="write the machine-readable audit here (after the report prints)")
    a.add_argument("--quiet", action="store_true", help="print only skills with findings")
    a.add_argument("--report-only", action="store_true", help="exit 0 even with findings")
    a.set_defaults(func=run_audit)

    r = sub.add_parser("receipt-check", help="validate a release receipt; '-' reads it from stdin")
    common(r)
    r.add_argument("receipt")
    r.set_defaults(func=receipt_check)

    t = sub.add_parser("receipt-template", help="print a receipt skeleton with every surface key")
    common(t)
    t.add_argument("skill")
    t.set_defaults(func=receipt_template)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
