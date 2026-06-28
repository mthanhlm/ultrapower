#!/usr/bin/env python3
"""Deterministic structural + release validator for the Ultrapower plugin.

Run from anywhere:  python3 scripts/validate.py
Exit 0 = all checks pass; exit 1 = at least one failure.

Checks:
  - plugin.json / marketplace.json are valid JSON and agree on name + version
  - every skill SKILL.md frontmatter parses and has name + description
  - no user-invocable skills (router model-invocable; `/ultrapower` is an external user alias)
  - read-only specialists declare disallowed-tools; review is context:fork
  - all shared references exist; every ../references/*.md link resolves
  - no stale `up:*` / removed public commands; no packaged hook
  - narrower CodeGraph MCP tools are not hard-wired into any tool list
  - required release files exist
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ok = True
def check(cond, msg):
    global ok
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond: ok = False

def fm(path):
    t = open(path, encoding="utf-8").read()
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", t, re.S)
    return (m.group(1), t[m.end():]) if m else (None, t)

SKILLS = ["run","implement","explore","document","plan","review","codegraph"]
REFS   = ["challenge","comments","verify","safety","codegraph","persistence","contract"]
REQUIRED = ([".claude-plugin/plugin.json",".claude-plugin/marketplace.json","README.md",
             "LICENSE","CHANGELOG.md","skills/run/scripts/codegraph-ensure.sh"]
            + [f"skills/{s}/SKILL.md" for s in SKILLS]
            + [f"skills/references/{r}.md" for r in REFS])

print("== required files ==")
for rel in REQUIRED:
    check(os.path.isfile(os.path.join(ROOT, rel)), f"exists: {rel}")

print("\n== manifests ==")
pj = json.load(open(os.path.join(ROOT,".claude-plugin/plugin.json")))
mj = json.load(open(os.path.join(ROOT,".claude-plugin/marketplace.json")))
check(pj.get("name")=="ultrapower", 'plugin.json name == "ultrapower"')
check("hooks" not in pj, "plugin.json has no hooks field")
check(mj["plugins"][0]["name"]=="ultrapower", "marketplace plugin name == ultrapower")
check(pj.get("version")==mj["plugins"][0].get("version"),
      f'versions agree ({pj.get("version")} == {mj["plugins"][0].get("version")})')

print("\n== no packaged hook / agent ==")
check(not os.path.isdir(os.path.join(ROOT,"hooks")), "no hooks/ dir")
check(not os.path.isdir(os.path.join(ROOT,"agents")), "no agents/ dir (review consolidated)")
check(not os.path.isdir(os.path.join(ROOT,"commands")), "no commands/ dir")

print("\n== skill frontmatter + visibility ==")
public = []
for s in SKILLS:
    f, _ = fm(os.path.join(ROOT, f"skills/{s}/SKILL.md"))
    check(f is not None, f"{s}: frontmatter parses")
    check(re.search(rf"^name:\s*{s}\b", f, re.M) is not None, f"{s}: name matches dir")
    check("description:" in f, f"{s}: has description")
    if "user-invocable: false" not in f: public.append(s)
check(public == [], f"no user-invocable plugin skills (entry is the /ultrapower alias): {public}")
check("argument-hint:" in fm(os.path.join(ROOT,"skills/run/SKILL.md"))[0], "router has argument-hint")

print("\n== read-only enforcement ==")
for s in ["explore","review"]:
    f,_ = fm(os.path.join(ROOT,f"skills/{s}/SKILL.md"))
    check(re.search(r"disallowed-tools:.*(Write|Edit)", f) is not None, f"{s}: disallowed-tools blocks edits")
    # Regression guard for the explore->implement/document blocker: a read-only
    # specialist MUST run forked so its restriction can't leak into the parent turn.
    check("context: fork" in f, f"{s}: runs in a forked (isolated) context (no tool-restriction leak)")

print("\n== reference link resolution (../references/NAME.md) ==")
link = re.compile(r"\.\./references/([A-Za-z0-9_]+)\.md")
for s in SKILLS:
    body = open(os.path.join(ROOT,f"skills/{s}/SKILL.md"),encoding="utf-8").read()
    for name in sorted(set(link.findall(body))):
        tgt = os.path.normpath(os.path.join(ROOT,f"skills/{s}","..","references",name+".md"))
        check(os.path.isfile(tgt), f"{s} -> ../references/{name}.md resolves")
# references that link to siblings (contract.md)
for r in REFS:
    body = open(os.path.join(ROOT,f"skills/references/{r}.md"),encoding="utf-8").read()
    for name in sorted(set(re.findall(r"\]\(([A-Za-z0-9_]+)\.md\)", body))):
        check(os.path.isfile(os.path.join(ROOT,"skills/references",name+".md")),
              f"references/{r}.md -> {name}.md resolves")

print("\n== anti-regression greps ==")
def grep_all(needle):
    hits=[]
    for d,_,fs in os.walk(ROOT):
        if "/.git" in d or "/.codegraph" in d: continue
        for fn in fs:
            if fn == "CHANGELOG.md": continue  # history doc may cite the old /up:* names
            if fn.endswith((".md",".json")):
                for i,l in enumerate(open(os.path.join(d,fn),encoding="utf-8",errors="ignore"),1):
                    if needle in l: hits.append(f"{os.path.relpath(os.path.join(d,fn),ROOT)}:{i}")
    return hits
for n in ["/up:","up:ultrapower","/ultrapower:go","/ultrapower:status","guard.sh"]:
    h=grep_all(n); check(not h, f"no '{n}': " + (", ".join(h) if h else "none"))

print("\n== no narrower CodeGraph MCP tool hard-wired in a tool list ==")
bad=[]
for s in SKILLS:
    f,_ = fm(os.path.join(ROOT,f"skills/{s}/SKILL.md"))
    for line in f.splitlines():
        if re.match(r"\s*(allowed-tools|disallowed-tools|tools):", line):
            for t in ["codegraph_impact","codegraph_callers","codegraph_callees",
                      "codegraph_search","codegraph_node","codegraph_status","codegraph_files"]:
                if t in line: bad.append(f"{s}: {line.strip()}")
check(not bad, "no impact/callers/callees/search in frontmatter tool lists: " + (", ".join(bad) if bad else "none"))

print("\n== RESULT:", "ALL OK" if ok else "FAILURES PRESENT", "==")
sys.exit(0 if ok else 1)
