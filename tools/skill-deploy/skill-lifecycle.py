#!/usr/bin/env python3
"""skill-lifecycle: the read-only lifecycle half of tools/skill-deploy.

Two jobs, both invoked through deploy-skill.sh so the producer stays the one entry
point (deploy-skill.sh --audit-surfaces ..., deploy-skill.sh --receipt <file> ...):

  audit            Walk every local surface a canonical skill can load from on this
                   machine, classify each copy against canonical, and exit non-zero
                   on any finding. This is the gate the aura repo mounts already had
                   (deploy-skill --verify in aura CI) extended to the surfaces that
                   were ungated on 2026-09-24: user mounts, plugin caches, the
                   claude.ai sync mirrors, Cowork's caches.

  receipt-check    Validate a skill release receipt (schema skill-release-receipt/v1)
                   against live canonical and a live audit, compute the lifecycle
                   state each intended surface has actually reached
                   (CANONICAL -> PACKAGED -> INSTALLED -> DISCOVERED -> BEHAVIOR TESTED
                   -> COMPLETE), and exit zero only when every intended surface is
                   COMPLETE and every unintended surface holding a copy carries a
                   disposition. That exit is the definition of "release complete".

  receipt-template Print a receipt skeleton for a skill with every surface key
                   present, so the author has to decide each surface explicitly.

Surfaces are distinct keys on purpose (Claude Chat, Cowork, Claude Code, Codex and
ChatGPT are five surfaces, never one shelf). Evidence recorded for one key never
satisfies another.

Read-only. Never writes into a mount, a cache or a mirror. Needs only python3;
PyYAML is optional (frontmatter name is read by regex when it is absent).
"""
import argparse
import hashlib
import json
import os
import re
import sys
from collections import defaultdict

SCHEMA_RECEIPT = "skill-release-receipt/v1"
SCHEMA_AUDIT = "skill-surface-audit/v1"

# Every surface the Estate loads skills from. `local` surfaces are observable on
# this machine; the others are receipt-only.
SURFACES = {
    "claude-code-user-mount":       {"client": "claude-code", "local": True,  "what": "~/.claude/skills (Claude Code personal skills)"},
    "claude-code-project-mount":    {"client": "claude-code", "local": True,  "what": "<repo>/.claude/skills (Claude Code project skills; canonical home for aura-native)"},
    "claude-code-plugin-cache":     {"client": "claude-code", "local": True,  "what": "~/.claude/plugins/cache/<marketplace>/<plugin>/<version> (installed plugins)"},
    "claudeai-org-plugin-sync":     {"client": "claude-code", "local": True,  "what": "~/.claude/plugins/synced/<org_account> (claude.ai org plugins, GitHub sync, one-way download)"},
    "claudeai-account-skills-sync": {"client": "claude-code", "local": True,  "what": "~/.claude/skills/synced/<org_account> (claude.ai account Skills, one-way download)"},
    "codex-user-mount":             {"client": "codex",       "local": True,  "what": "~/.agents/skills (Codex user skills)"},
    "codex-repo-mount":             {"client": "codex",       "local": True,  "what": "<repo>/.agents/skills (Codex repo skills, deployed copies)"},
    "codex-plugin-cache":           {"client": "codex",       "local": True,  "what": "~/.codex/plugins/cache/<marketplace>/<plugin>/<version> (enabled per config.toml)"},
    "codex-synced-mirror":          {"client": "codex",       "local": True,  "what": "~/.agents/skills/synced/<org_account> (a copy Codex never produces; unsourced)"},
    "cowork-account-skills":        {"client": "cowork",      "local": True,  "what": "Claude desktop local-agent-mode-sessions/skills-plugin/<org>/<account>/skills"},
    "cowork-org-plugins":           {"client": "cowork",      "local": True,  "what": "Claude desktop local-agent-mode-sessions/<account>/<org>/rpm/<plugin_id>/skills"},
    "claude-chat":                  {"client": "claude-chat", "local": False, "what": "claude.ai chat (loads the account Skills shelf and org plugins; no local read)"},
    "chatgpt-north":                {"client": "chatgpt",     "local": False, "what": "ChatGPT/NORTH (manual upload through the ChatGPT UI; receipt only)"},
}
LOCAL_SURFACES = [k for k, v in SURFACES.items() if v["local"]]
LADDER = ["CANONICAL", "PACKAGED", "INSTALLED", "DISCOVERED", "BEHAVIOR TESTED", "COMPLETE"]

HDR = re.compile(r"^# DEPLOYED COPY \((\d{4}-\d{2}-\d{2}), skill-deploy pipeline\): the canonical home is\n# (.+?)\. Deployed at (.+?)\.$", re.M)
VER = re.compile(r"^# .*?\bv(\d+\.\d+(?:\.\d+)?)\b", re.M)
REWRITE = re.compile(r"\bCodex project conversations\b|\bCodex app\b|\bCodex Chat\b")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def read_text(path):
    with open(path, encoding="utf-8", errors="surrogateescape") as f:
        return f.read()


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


def version_of(text):
    m = VER.search(body_of(text))
    return "v" + m.group(1) if m else None


def deployed_header(text):
    m = HDR.search(split_frontmatter(text)[0])
    return {"deployedAt": m.group(1), "canonical": m.group(2), "stamp": m.group(3)} if m else None


def frontmatter_name(text):
    fm = split_frontmatter(text)[0]
    m = re.search(r"^name:\s*['\"]?([A-Za-z0-9_-]+)['\"]?\s*$", fm, re.M)
    return m.group(1) if m else None


def manifest_state(skill_dir):
    mf = os.path.join(skill_dir, "checksums.sha256")
    if not os.path.isfile(mf):
        return "absent"
    listed = {}
    for line in open(mf, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line.strip():
            continue
        h, _, p = line.partition("  ")
        listed[os.path.normpath(p)] = h.strip()
    actual = {}
    for dp, _, fn in os.walk(skill_dir):
        for f in fn:
            if f == "checksums.sha256":
                continue
            p = os.path.join(dp, f)
            actual[os.path.normpath(os.path.relpath(p, skill_dir))] = sha256_file(p)
    return "ok" if listed == actual else "fails"


# ----------------------------------------------------------------- canonical
def load_canonical(eps, aura, graph_path=None):
    """Canonical skills: every SKILL.md under eps skills/ and plugins/*/skills/, plus
    the aura-native nodes of the committed skills graph when --aura is given. Status
    comes from the graph when present, else 'live'."""
    graph = None
    gp = graph_path or os.path.join(eps, "tools", "skill-map", "skills-graph.json")
    if os.path.isfile(gp):
        graph = json.load(open(gp))
    status_by_id = {}
    aura_nodes = {}
    if graph:
        for n in graph.get("nodes", []):
            status_by_id[n["id"]] = n.get("status", "live")
            repo, rel = n["source"].split(":", 1)
            if repo == "aura":
                aura_nodes[n["id"]] = rel
    canon = {}
    for d in sorted(os.listdir(os.path.join(eps, "skills"))) if os.path.isdir(os.path.join(eps, "skills")) else []:
        p = os.path.join(eps, "skills", d, "SKILL.md")
        if os.path.isfile(p):
            canon[d] = {"id": d, "repo": "expert-partners-skills", "path": f"skills/{d}/SKILL.md", "abs": p, "plugin": None}
    pl_root = os.path.join(eps, "plugins")
    if os.path.isdir(pl_root):
        for plugin in sorted(os.listdir(pl_root)):
            sroot = os.path.join(pl_root, plugin, "skills")
            if not os.path.isdir(sroot):
                continue
            pv = None
            pj = os.path.join(pl_root, plugin, ".claude-plugin", "plugin.json")
            if os.path.isfile(pj):
                pv = json.load(open(pj)).get("version")
            for d in sorted(os.listdir(sroot)):
                p = os.path.join(sroot, d, "SKILL.md")
                if os.path.isfile(p):
                    if d in canon:
                        raise SystemExit(f"FATAL: {d} has two canonical homes in eps ({canon[d]['path']} and plugins/{plugin}/skills/{d}); resolve before auditing")
                    canon[d] = {"id": d, "repo": "expert-partners-skills", "path": f"plugins/{plugin}/skills/{d}/SKILL.md", "abs": p, "plugin": plugin, "pluginVersion": pv}
    if aura:
        for sid, rel in aura_nodes.items():
            p = os.path.join(aura, rel)
            if os.path.isfile(p):
                if sid in canon:
                    raise SystemExit(f"FATAL: {sid} is canonical in both eps and aura ({canon[sid]['path']} and aura:{rel})")
                canon[sid] = {"id": sid, "repo": "aura", "path": rel, "abs": p, "plugin": None}
    for c in canon.values():
        text = read_text(c["abs"])
        c["sha256"] = sha256_file(c["abs"])
        c["bodySha256"] = hashlib.sha256(body_of(text).encode("utf-8", "surrogateescape")).hexdigest()
        c["version"] = version_of(text)
        c["status"] = status_by_id.get(c["id"], "live")
    return canon


# ------------------------------------------------------------------- surfaces
def enabled_claude_plugins(home):
    """installed plugin -> version, from installed_plugins.json (what actually loads)."""
    p = os.path.join(home, ".claude", "plugins", "installed_plugins.json")
    out = {}
    if os.path.isfile(p):
        for key, entries in json.load(open(p)).get("plugins", {}).items():
            if entries:
                out[key] = entries[0].get("version")
    return out


def enabled_codex_plugins(codex_home):
    p = os.path.join(codex_home, "config.toml")
    out = set()
    if os.path.isfile(p):
        text = read_text(p)
        for m in re.finditer(r'\[plugins\."([^"]+)"\]\s*\n\s*enabled\s*=\s*true', text):
            out.add(m.group(1))
    return out


def walk_mount(root):
    """<root>/<id>/SKILL.md -> {id: path}."""
    out = {}
    if os.path.isdir(root):
        for d in sorted(os.listdir(root)):
            if d.lower() == "synced":
                continue
            p = os.path.join(root, d, "SKILL.md")
            if os.path.isfile(p):
                out[d] = p
    return out


def walk_plugin_cache(root):
    """<root>/<marketplace>/<plugin>/<version>/skills/<id>/SKILL.md."""
    out = []
    if not os.path.isdir(root):
        return out
    for mkt in sorted(os.listdir(root)):
        mroot = os.path.join(root, mkt)
        if not os.path.isdir(mroot):
            continue
        for plugin in sorted(os.listdir(mroot)):
            proot = os.path.join(mroot, plugin)
            if not os.path.isdir(proot):
                continue
            for ver in sorted(os.listdir(proot)):
                sroot = os.path.join(proot, ver, "skills")
                if not os.path.isdir(sroot):
                    continue
                for d in sorted(os.listdir(sroot)):
                    p = os.path.join(sroot, d, "SKILL.md")
                    if os.path.isfile(p):
                        out.append({"marketplace": mkt, "plugin": plugin, "version": ver, "id": d, "path": p})
    return out


def walk_synced_plugins(root):
    """~/.claude/plugins/synced/<org_account>/<plugin-dir>/skills/<id>/SKILL.md with .meta.json beside the dir."""
    out = []
    if not os.path.isdir(root):
        return out
    for acct in sorted(os.listdir(root)):
        aroot = os.path.join(root, acct)
        if not os.path.isdir(aroot):
            continue
        for d in sorted(os.listdir(aroot)):
            pj = os.path.join(aroot, d, ".claude-plugin", "plugin.json")
            if not os.path.isfile(pj):
                continue
            pjson = json.load(open(pj))
            meta = {}
            mp = os.path.join(aroot, d + ".meta.json")
            if os.path.isfile(mp):
                meta = json.load(open(mp))
            sroot = os.path.join(aroot, d, "skills")
            if not os.path.isdir(sroot):
                continue
            for sid in sorted(os.listdir(sroot)):
                p = os.path.join(sroot, sid, "SKILL.md")
                if os.path.isfile(p):
                    out.append({"plugin": pjson.get("name", d), "version": pjson.get("version"), "id": sid, "path": p,
                                "marketplace": meta.get("marketplace_name"), "dir": d})
    return out


def walk_synced_skills(root):
    """~/.claude/skills/synced/<org_account>/<id>/SKILL.md plus manifest.json metadata."""
    out = []
    if not os.path.isdir(root):
        return out
    for acct in sorted(os.listdir(root)):
        aroot = os.path.join(root, acct)
        if not os.path.isdir(aroot):
            continue
        meta = {}
        mp = os.path.join(aroot, "manifest.json")
        if os.path.isfile(mp):
            try:
                for s in json.load(open(mp)).get("skills", []):
                    meta[s.get("name")] = s
            except (ValueError, OSError):
                pass
        for sid, p in walk_mount(aroot).items():
            m = meta.get(sid, {})
            out.append({"id": sid, "path": p, "account": acct, "updatedAt": m.get("updatedAt"), "backingPluginId": m.get("backingPluginId")})
    return out


def walk_cowork_skills(app_support):
    out = []
    root = os.path.join(app_support, "local-agent-mode-sessions", "skills-plugin")
    if not os.path.isdir(root):
        return out
    for org in sorted(os.listdir(root)):
        oroot = os.path.join(root, org)
        if not os.path.isdir(oroot):
            continue
        for acct in sorted(os.listdir(oroot)):
            sroot = os.path.join(oroot, acct, "skills")
            for sid, p in walk_mount(sroot).items():
                out.append({"id": sid, "path": p, "org": org, "account": acct})
    return out


def walk_cowork_plugins(app_support):
    out = []
    root = os.path.join(app_support, "local-agent-mode-sessions")
    if not os.path.isdir(root):
        return out
    for acct in sorted(os.listdir(root)):
        aroot = os.path.join(root, acct)
        if not os.path.isdir(aroot) or acct == "skills-plugin":
            continue
        for org in sorted(os.listdir(aroot)):
            rpm = os.path.join(aroot, org, "rpm")
            if not os.path.isdir(rpm):
                continue
            for pid in sorted(os.listdir(rpm)):
                pj = os.path.join(rpm, pid, ".claude-plugin", "plugin.json")
                if not os.path.isfile(pj):
                    continue
                pjson = json.load(open(pj))
                for sid, p in walk_mount(os.path.join(rpm, pid, "skills")).items():
                    out.append({"id": sid, "path": p, "plugin": pjson.get("name"), "version": pjson.get("version"), "pluginId": pid, "org": org, "account": acct})
    return out


# -------------------------------------------------------------------- classify
def classify_copy(canon_entry, path, pipeline_mount):
    """State of one copy against its canonical. pipeline_mount: the location is one the
    producer writes (a DEPLOYED COPY header and manifest are expected there)."""
    text = read_text(path)
    body_sha = hashlib.sha256(body_of(text).encode("utf-8", "surrogateescape")).hexdigest()
    same = body_sha == canon_entry["bodySha256"]
    hdr = deployed_header(text)
    rewritten = bool(REWRITE.search(text)) and not REWRITE.search(read_text(canon_entry["abs"]))
    rec = {"path": path, "sha256": sha256_file(path), "version": version_of(text), "deployedHeader": hdr,
           "rewritten": rewritten}
    if pipeline_mount:
        if hdr:
            canon_label = f"{canon_entry['repo']} {canon_entry['path']}"
            if hdr["canonical"] != canon_label:
                rec["state"] = "ORPHAN"
                rec["detail"] = f"header names {hdr['canonical']!r}, canonical for this id is {canon_label!r}"
                return rec
            ms = manifest_state(os.path.dirname(path))
            rec["manifest"] = ms
            if ms != "ok":
                rec["state"] = "HAND-EDITED"
                rec["detail"] = f"checksums.sha256 {ms}"
            elif same:
                rec["state"] = "CURRENT"
            else:
                rec["state"] = "STALE"
                rec["detail"] = f"pipeline copy at {hdr['stamp']} (deployed {hdr['deployedAt']}), canonical is {canon_entry['version'] or 'tree-stamped'}"
        else:
            rec["manifest"] = manifest_state(os.path.dirname(path))
            rec["state"] = "UNTRACKED-COPY" if same else "UNTRACKED-COPY-STALE"
            rec["detail"] = "no DEPLOYED COPY header; not produced by the pipeline"
    else:
        rec["state"] = "CURRENT" if same else "STALE"
    if rewritten:
        rec["detail"] = (rec.get("detail", "") + "; Claude-to-Codex text rewrite detected").strip("; ")
    return rec


def run_audit(args):
    eps = os.path.abspath(args.eps)
    aura = os.path.abspath(args.aura) if args.aura else None
    home = os.path.abspath(args.home)
    app = os.path.abspath(args.app_support) if args.app_support else os.path.join(home, "Library", "Application Support", "Claude")
    codex_home = os.path.abspath(args.codex_home) if args.codex_home else os.path.join(home, ".codex")
    canon = load_canonical(eps, aura, args.graph)
    only = set(args.only.split(",")) if args.only else None
    installed = enabled_claude_plugins(home)
    codex_enabled = enabled_codex_plugins(codex_home)
    local_plugin_names = {k.split("@")[0] for k in installed}

    copies = defaultdict(list)  # id -> list of {surface, ...}

    def add(sid, surface, rec, loads=True, **extra):
        rec = dict(rec)
        rec.update({"surface": surface, "loads": loads})
        rec.update(extra)
        copies[sid].append(rec)

    def consider(sid):
        return sid in canon and (only is None or sid in only)

    # user mounts and repo mounts (pipeline mounts)
    for sid, p in walk_mount(os.path.join(home, ".claude", "skills")).items():
        if consider(sid):
            add(sid, "claude-code-user-mount", classify_copy(canon[sid], p, True))
    for sid, p in walk_mount(os.path.join(home, ".agents", "skills")).items():
        if consider(sid):
            add(sid, "codex-user-mount", classify_copy(canon[sid], p, True))
    if aura:
        for sid, p in walk_mount(os.path.join(aura, ".claude", "skills")).items():
            if consider(sid):
                c = canon[sid]
                if c["repo"] == "aura" and os.path.abspath(p) == os.path.abspath(c["abs"]):
                    add(sid, "claude-code-project-mount", {"path": p, "sha256": c["sha256"], "version": c["version"], "state": "CANONICAL", "deployedHeader": None, "rewritten": False})
                else:
                    add(sid, "claude-code-project-mount", classify_copy(c, p, True))
        for sid, p in walk_mount(os.path.join(aura, ".agents", "skills")).items():
            if consider(sid):
                add(sid, "codex-repo-mount", classify_copy(canon[sid], p, True))
    # plugin caches
    for e in walk_plugin_cache(os.path.join(home, ".claude", "plugins", "cache")):
        if consider(e["id"]):
            loads = installed.get(f"{e['plugin']}@{e['marketplace']}") == e["version"]
            add(e["id"], "claude-code-plugin-cache", classify_copy(canon[e["id"]], e["path"], False), loads=loads,
                plugin=e["plugin"], pluginVersion=e["version"], marketplace=e["marketplace"])
    for e in walk_plugin_cache(os.path.join(codex_home, "plugins", "cache")):
        if consider(e["id"]):
            loads = f"{e['plugin']}@{e['marketplace']}" in codex_enabled
            add(e["id"], "codex-plugin-cache", classify_copy(canon[e["id"]], e["path"], False), loads=loads,
                plugin=e["plugin"], pluginVersion=e["version"], marketplace=e["marketplace"])
    # claude.ai sync mirrors (Claude Code side)
    for e in walk_synced_plugins(os.path.join(home, ".claude", "plugins", "synced")):
        if consider(e["id"]):
            # a synced plugin whose name matches a locally installed plugin is not loaded by Claude Code
            # (claude plugin list: "... on this machine has the same name and takes precedence", observed 2026-09-24)
            loads = e["plugin"] not in local_plugin_names
            add(e["id"], "claudeai-org-plugin-sync", classify_copy(canon[e["id"]], e["path"], False), loads=loads,
                plugin=e["plugin"], pluginVersion=e["version"], marketplace=e["marketplace"],
                shadowedBy=(f"{e['plugin']}@local" if not loads else None))
    for e in walk_synced_skills(os.path.join(home, ".claude", "skills", "synced")):
        if consider(e["id"]):
            add(e["id"], "claudeai-account-skills-sync", classify_copy(canon[e["id"]], e["path"], False),
                updatedAt=e["updatedAt"], backingPluginId=e["backingPluginId"])
    for e in walk_synced_skills(os.path.join(home, ".agents", "skills", "synced")):
        if consider(e["id"]):
            add(e["id"], "codex-synced-mirror", classify_copy(canon[e["id"]], e["path"], False))
    # Cowork caches
    for e in walk_cowork_skills(app):
        if consider(e["id"]):
            add(e["id"], "cowork-account-skills", classify_copy(canon[e["id"]], e["path"], False), org=e["org"], account=e["account"])
    for e in walk_cowork_plugins(app):
        if consider(e["id"]):
            add(e["id"], "cowork-org-plugins", classify_copy(canon[e["id"]], e["path"], False), plugin=e["plugin"], pluginVersion=e["version"])

    # findings
    findings = []
    per_skill = {}
    for sid in sorted(canon):
        if only is not None and sid not in only:
            continue
        c = canon[sid]
        cs = copies.get(sid, [])
        loaded = [r for r in cs if r["loads"]]
        # duplicate identity per client: more than one loaded copy in one client
        dups = {}
        for client in ("claude-code", "codex", "cowork"):
            lc = [r for r in loaded if SURFACES[r["surface"]]["client"] == client]
            if len(lc) > 1:
                dups[client] = [{"surface": r["surface"], "path": r["path"], "version": r["version"], "state": r["state"]} for r in lc]
                versions = {r["sha256"] for r in lc}
                findings.append({"id": sid, "kind": "DUPLICATE-IDENTITY", "client": client,
                                 "detail": f"{len(lc)} copies load in {client} ({'same bytes' if len(versions) == 1 else str(len(versions)) + ' distinct contents'})"})
        if c["status"] == "retired" and loaded:
            for r in loaded:
                findings.append({"id": sid, "kind": "RETIRED-LOADING", "surface": r["surface"], "path": r["path"], "detail": "graph status retired but a copy still loads"})
        for r in cs:
            if r["state"] in ("STALE", "HAND-EDITED", "ORPHAN", "UNTRACKED-COPY", "UNTRACKED-COPY-STALE") and (r["loads"] or r["state"] == "ORPHAN"):
                findings.append({"id": sid, "kind": r["state"], "surface": r["surface"], "path": r["path"], "detail": r.get("detail", "")})
            if r.get("rewritten"):
                findings.append({"id": sid, "kind": "REWRITTEN", "surface": r["surface"], "path": r["path"], "detail": "text substitution of the canonical (Claude replaced by Codex); never a legitimate adaptation"})
        per_skill[sid] = {"canonical": {k: c[k] for k in ("repo", "path", "version", "status", "plugin")} | {"sha256": c["sha256"][:12]},
                          "copies": [{k: (v[:12] if k == "sha256" and isinstance(v, str) else v) for k, v in r.items() if k != "deployedHeader"} for r in cs],
                          "duplicates": dups}
    # orphans: pipeline copies in the local mounts whose id no canonical owns
    for mount, surface in ((os.path.join(home, ".claude", "skills"), "claude-code-user-mount"), (os.path.join(home, ".agents", "skills"), "codex-user-mount")):
        for sid, p in walk_mount(mount).items():
            if sid in canon:
                continue
            hdr = deployed_header(read_text(p))
            if hdr:
                findings.append({"id": sid, "kind": "ORPHAN", "surface": surface, "path": p, "detail": f"DEPLOYED COPY header names {hdr['canonical']!r} but no canonical skill owns this id"})
    result = {"schema": SCHEMA_AUDIT, "eps": eps, "aura": aura, "home": home, "canonicalCount": len(canon),
              "surfacesObserved": LOCAL_SURFACES, "skills": per_skill, "findings": findings,
              "summary": {"findings": len(findings), "byKind": dict(sorted(((k, sum(1 for f in findings if f["kind"] == k)) for k in {f["kind"] for f in findings})))}}
    if args.json:
        with open(args.json, "w") as f:
            json.dump(result, f, indent=2)
    # human output
    for sid, rec in per_skill.items():
        if args.quiet and not any(f["id"] == sid for f in findings):
            continue
        print(f"{sid} [{rec['canonical']['repo']} {rec['canonical']['path']} {rec['canonical']['version'] or ''} status={rec['canonical']['status']}]")
        for r in rec["copies"]:
            flag = "" if r["loads"] else " (inert)"
            rw = " REWRITTEN" if r.get("rewritten") else ""
            print(f"  {r['surface']}: {r['state']}{flag}{rw} {r.get('version') or ''} {r['path']}")
    print(f"audit-surfaces: {len(canon)} canonical skill(s), {len(findings)} finding(s)" + (f" {result['summary']['byKind']}" if findings else ""))
    return 1 if findings and not args.report_only else 0


# --------------------------------------------------------------------- receipt
def receipt_template(args):
    eps = os.path.abspath(args.eps)
    aura = os.path.abspath(args.aura) if args.aura else None
    canon = load_canonical(eps, aura, args.graph)
    sid = args.skill
    if sid not in canon:
        raise SystemExit(f"FATAL: {sid} is not a canonical skill in {eps}" + (f" or {aura}" if aura else ""))
    c = canon[sid]
    tmpl = {
        "schema": SCHEMA_RECEIPT,
        "skill": sid,
        "canonical": {"repo": c["repo"], "path": c["path"], "commit": "<git rev-parse of the merged main this release was built from>", "skillmdSha256": c["sha256"], "version": c["version"]},
        "packaged": [{"kind": "claudeai-upload-zip | plugin-version | none", "artifact": "<path or plugin@version>", "sha256": "<zip sha256 or null>", "builtFrom": "<commit>"}],
        "surfaces": {k: {"intended": None, "reason": "<why this surface is or is not owed>",
                         "installed": None, "discovered": None, "behaviorTested": None, "disposition": None}
                     for k in SURFACES},
        "evidenceSlots": {
            "installed": {"verifiedAt": "YYYY-MM-DD", "method": "deploy-skill --verify | claude plugin update | manual upload | NORTH upload", "evidence": "<path or receipt>"},
            "discovered": {"verifiedAt": "YYYY-MM-DD", "method": "claude plugin list | claude skill list | codex app-server skills/list | ListSkills | NORTH report", "evidence": "<path or receipt>"},
            "behaviorTested": {"verifiedAt": "YYYY-MM-DD", "fixture": "<fixture id>", "result": "pass | fail", "evidence": "<path>"},
        },
    }
    print(json.dumps(tmpl, indent=2))
    return 0


def receipt_check(args):
    eps = os.path.abspath(args.eps)
    aura = os.path.abspath(args.aura) if args.aura else None
    canon = load_canonical(eps, aura, args.graph)
    try:
        rc = json.load(open(args.receipt))
    except (OSError, ValueError) as e:
        raise SystemExit(f"FATAL: cannot read receipt {args.receipt}: {e}")
    problems = []
    if rc.get("schema") != SCHEMA_RECEIPT:
        problems.append(f"schema must be {SCHEMA_RECEIPT}, got {rc.get('schema')!r}")
    sid = rc.get("skill")
    if sid not in canon:
        problems.append(f"skill {sid!r} has no canonical home in eps" + (" or aura" if aura else "") + " (missing canonical home)")
        print("\n".join("FAIL: " + p for p in problems))
        return 1
    c = canon[sid]
    if c["status"] == "retired":
        problems.append(f"{sid} is retired in the graph; a retired skill has no release, it has removals")
    can = rc.get("canonical") or {}
    if can.get("path") != c["path"] or (can.get("repo") or "").lower() != c["repo"]:
        problems.append(f"receipt canonical {can.get('repo')} {can.get('path')} does not match live canonical {c['repo']} {c['path']}")
    if can.get("skillmdSha256") and can.get("skillmdSha256") != c["sha256"]:
        problems.append(f"receipt canonical SKILL.md sha256 {str(can.get('skillmdSha256'))[:12]} differs from live canonical {c['sha256'][:12]} (stale receipt or canonical moved)")
    if not re.fullmatch(r"[0-9a-f]{7,40}", str(can.get("commit", ""))):
        problems.append("receipt canonical.commit must be the merged commit hash the release was built from")
    packaged = rc.get("packaged") or []
    surfaces = rc.get("surfaces") or {}
    missing = [k for k in SURFACES if k not in surfaces]
    if missing:
        problems.append("every surface key must be present and decided (intended true or false with a reason): missing " + ", ".join(missing))
    # live audit of local surfaces for this skill
    audit_args = argparse.Namespace(eps=args.eps, aura=args.aura, home=args.home, app_support=args.app_support, codex_home=args.codex_home,
                                    graph=args.graph, only=sid, json=None, quiet=True, report_only=True)
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        run_audit(audit_args)
    live = {}
    # re-run collection to get structured copies (cheap for one skill)
    audit_json = os.path.join(os.path.dirname(os.path.abspath(args.receipt)), f".{sid}.audit.tmp.json") if args.live_json is None else args.live_json
    audit_args.json = audit_json
    with contextlib.redirect_stdout(io.StringIO()):
        run_audit(audit_args)
    live = json.load(open(audit_json)).get("skills", {}).get(sid, {})
    if args.live_json is None:
        try:
            os.remove(audit_json)
        except OSError:
            pass
    live_by_surface = defaultdict(list)
    for r in live.get("copies", []):
        live_by_surface[r["surface"]].append(r)

    rows = []
    for key in SURFACES:
        s = surfaces.get(key)
        if not isinstance(s, dict):
            rows.append((key, "UNDECIDED", "no entry"))
            continue
        intended = s.get("intended")
        if intended not in (True, False):
            problems.append(f"{key}: intended must be true or false (with a reason), got {intended!r}")
            rows.append((key, "UNDECIDED", "intended not decided"))
            continue
        if not str(s.get("reason") or "").strip():
            problems.append(f"{key}: reason is required")
        live_copies = live_by_surface.get(key, [])
        live_loaded = [r for r in live_copies if r.get("loads")]
        if not intended:
            if live_loaded and not str(s.get("disposition") or "").strip():
                problems.append(f"{key}: not intended, yet a copy loads there ({live_loaded[0]['state']} {live_loaded[0]['path']}); a disposition is required")
            rows.append((key, "NOT INTENDED", (s.get("disposition") or "no copy present") if not live_loaded else f"copy present: {live_loaded[0]['state']} -> {s.get('disposition') or 'DISPOSITION MISSING'}"))
            continue
        # ladder for an intended surface
        state = "CANONICAL"
        note = []
        needs_package = key in ("claudeai-account-skills-sync", "cowork-account-skills", "claude-chat", "chatgpt-north")
        has_package = any(p.get("sha256") or p.get("kind") == "plugin-version" for p in packaged) if packaged else False
        if needs_package and not has_package:
            note.append("no package recorded")
        else:
            state = "PACKAGED"
            inst = s.get("installed")
            if isinstance(inst, dict) and inst.get("verifiedAt") and inst.get("method"):
                # local surfaces must also verify live
                if SURFACES[key]["local"]:
                    if not live_loaded:
                        note.append("receipt says installed but no loaded copy exists locally")
                    elif any(r["state"] not in ("CURRENT", "CANONICAL") for r in live_loaded):
                        note.append("receipt says installed but a loaded copy is " + ", ".join(sorted({r['state'] for r in live_loaded if r['state'] not in ('CURRENT', 'CANONICAL')})))
                    else:
                        state = "INSTALLED"
                else:
                    state = "INSTALLED"
                if state == "INSTALLED":
                    disc = s.get("discovered")
                    if isinstance(disc, dict) and disc.get("verifiedAt") and disc.get("method"):
                        state = "DISCOVERED"
                        beh = s.get("behaviorTested")
                        if isinstance(beh, dict) and beh.get("verifiedAt") and beh.get("result") == "pass":
                            state = "COMPLETE"
                        elif isinstance(beh, dict) and beh.get("result") == "fail":
                            note.append("behavior fixture failed")
                        else:
                            note.append("no passed behavior fixture")
                    else:
                        note.append("no discovery receipt")
            else:
                note.append("no installed receipt")
        rows.append((key, state, "; ".join(note)))
        if state != "COMPLETE":
            problems.append(f"{key}: intended surface reached {state} only ({'; '.join(note)})")
    width = max(len(k) for k in SURFACES)
    print(f"release receipt: {sid} ({c['repo']} {c['path']} {c['version'] or ''})")
    for key, state, note in rows:
        print(f"  {key.ljust(width)}  {state.ljust(14)}  {note}")
    if problems:
        print("receipt-check: NOT COMPLETE")
        for p in problems:
            print(f"  FAIL: {p}")
        return 1
    print("receipt-check: COMPLETE, every intended surface installed, discovered and behavior tested; every unintended copy dispositioned")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="skill-lifecycle.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--eps", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."), help="expert-partners-skills checkout (default: this repo)")
        p.add_argument("--aura", default=os.environ.get("AURA_PATH"), help="aura checkout for Aura-native canonicals and repo mounts (default: $AURA_PATH)")
        p.add_argument("--graph", default=None, help="skills-graph.json path (default: <eps>/tools/skill-map/skills-graph.json)")
        p.add_argument("--home", default=os.path.expanduser("~"), help="home directory holding .claude, .agents (default: $HOME)")
        p.add_argument("--app-support", default=None, help="Claude desktop Application Support dir (default: <home>/Library/Application Support/Claude)")
        p.add_argument("--codex-home", default=None, help="Codex home (default: <home>/.codex)")

    a = sub.add_parser("audit", help="classify every local copy of every canonical skill")
    common(a)
    a.add_argument("--only", default=None, help="comma-separated skill ids")
    a.add_argument("--json", default=None, help="write the machine-readable audit here")
    a.add_argument("--quiet", action="store_true", help="print only skills with findings")
    a.add_argument("--report-only", action="store_true", help="exit 0 even with findings")
    a.set_defaults(func=run_audit)

    r = sub.add_parser("receipt-check", help="validate a release receipt and compute the state each surface reached")
    common(r)
    r.add_argument("receipt")
    r.add_argument("--live-json", default=None, help="also write the live audit for the skill here")
    r.set_defaults(func=receipt_check)

    t = sub.add_parser("receipt-template", help="print a receipt skeleton with every surface key")
    common(t)
    t.add_argument("skill")
    t.set_defaults(func=receipt_template)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
