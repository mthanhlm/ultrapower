"""Guard the prose↔CLI contract: every scrum_state.py invocation and agent/hook reference in the
command markdown must resolve against the real argparse surface and the real files. A renamed flag
or removed subcommand would otherwise leave the suite green while `/up:run` dies mid-cycle."""
import argparse
import glob
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import scrum_state  # noqa: E402

COMMANDS = sorted(glob.glob(os.path.join(ROOT, "commands", "*.md")))


def _surface():
    parser = scrum_state.build_parser()
    sub = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    surface = {}
    for name, sp in sub.choices.items():
        opts = set()
        for act in sp._actions:
            opts |= set(act.option_strings)
        surface[name] = opts
    return surface


def _join_continuations(text):
    return re.sub(r"\\\n\s*", " ", text)


def _invocations(text):
    """(subcommand, [flags]) for each scrum_state.py invocation — fenced (python3 …) or inline
    (`scrum_state.py plan-next`). Every match's token must be a registered subcommand."""
    out = []
    for line in _join_continuations(text).splitlines():
        if "scrum_state.py" not in line:
            continue
        m = re.search(r"scrum_state\.py\"?\s+([a-z][a-z-]+)", line)
        if not m:
            continue
        # Flags belong to THIS invocation only — stop at the closing backtick so a prose mention
        # after an inline invocation (e.g. "check-tdd` (skip for `--kind refactor`)") isn't attributed.
        tail = line[m.end():].split("`")[0]
        flags = re.findall(r"(--[a-z][a-z-]+)", tail)
        out.append((m.group(1), flags))
    return out


def test_every_command_scrum_state_invocation_resolves():
    surface = _surface()
    seen = 0
    for md in COMMANDS:
        text = open(md).read()
        for sub, flags in _invocations(text):
            seen += 1
            assert sub in surface, f"{os.path.basename(md)}: unknown subcommand '{sub}'"
            for flag in flags:
                assert flag in surface[sub], (
                    f"{os.path.basename(md)}: '{flag}' is not a valid option of '{sub}' "
                    f"(valid: {sorted(surface[sub])})"
                )
    assert seen >= 12, f"expected to find real invocations to check, found {seen}"


def test_referenced_hook_scripts_exist():
    for md in COMMANDS:
        for hook in re.findall(r"hooks/([a-z-]+\.py)", open(md).read()):
            assert os.path.isfile(os.path.join(ROOT, "hooks", hook)), f"missing hook: {hook}"


def test_invoked_agents_exist_by_name():
    agent_names = set()
    for md in glob.glob(os.path.join(ROOT, "agents", "*.md")):
        fm = yaml.safe_load(open(md).read().split("---", 2)[1])
        agent_names.add(fm["name"])
    # the agents the commands invoke by backtick name
    for md in COMMANDS:
        for name in re.findall(r"`(step-planner|navigator|implementer|scrum-master|debate|teacher)`", open(md).read()):
            assert name in agent_names, f"{os.path.basename(md)} invokes agent '{name}' which does not exist"
