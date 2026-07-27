#!/usr/bin/env python3
"""opus-rail benchmark: isolated Opus 5 vs the opus-rail workflow.

Each (task, arm, rep) cell runs in a fresh temp sandbox:
  baseline  claude --model claude-opus-5 --print   (no rails: headless sessions
            get no first-prompt injection, and the full id bypasses the pin)
  rail      claude --model opus --print --session-id <uuid>, with the session's
            model flag pre-written so opus-rails.py delivers the real rails and
            routing check exactly as in interactive use (full system required)

Verdict per cell: the task's tests (framework-free asserts) run in the sandbox.
Metrics come from --output-format json plus the session transcript, including a
check of which model ACTUALLY drove the main loop (arm_violation if wrong).

Stdlib only. Results: bench/results/run-<stamp>/{results.json,summary.md}
"""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

BENCH = pathlib.Path(__file__).resolve().parent
CLAUDE_DIR = pathlib.Path.home() / ".claude"
FLAG_DIR = CLAUDE_DIR / ".model-live"
RUN_TIMEOUT_S = 900

ARMS = {
    "baseline": {"model": "claude-opus-5", "seed_flag": False,
                 "expect_model": "claude-opus-5"},
    "rail": {"model": "opus", "seed_flag": True,
             "expect_model": "claude-opus-4-8"},
}


def _claude_supports(flag):
    try:
        out = subprocess.run(["claude", "--help"], capture_output=True,
                             text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return flag in out


def run_cell(task_dir, arm_name, rep, permission_args):
    arm = ARMS[arm_name]
    work = pathlib.Path(tempfile.mkdtemp(prefix="opusrail-bench-"))
    for f in (task_dir / "files").iterdir():
        shutil.copy(f, work / f.name)
    shutil.copy(BENCH / "harness" / "run_tests.py", work / "run_tests.py")
    prompt = (task_dir / "prompt.txt").read_text()

    sid = str(uuid.uuid4())
    cmd = ["claude", "--print", prompt, "--output-format", "json",
           "--model", arm["model"], "--session-id", sid] + permission_args
    if arm["seed_flag"]:
        FLAG_DIR.mkdir(parents=True, exist_ok=True)
        (FLAG_DIR / ("sess-%s" % sid)).write_text(arm["expect_model"])

    t0 = time.time()
    try:
        proc = subprocess.run(cmd, cwd=str(work), capture_output=True,
                              text=True, timeout=RUN_TIMEOUT_S)
        timed_out = False
    except subprocess.TimeoutExpired:
        proc, timed_out = None, True
    wall_s = round(time.time() - t0, 1)

    cell = {"task": task_dir.name, "arm": arm_name, "rep": rep, "wall_s": wall_s,
            "timed_out": timed_out, "workdir": str(work), "session_id": sid}
    if proc is not None:
        try:
            out = json.loads(proc.stdout)
            cell["cost_usd"] = out.get("total_cost_usd")
            cell["num_turns"] = out.get("num_turns")
            cell["usage"] = out.get("usage")
            cell["session_id"] = out.get("session_id", sid)
        except ValueError:
            cell["cli_stdout_tail"] = proc.stdout[-500:]
            cell["cli_stderr_tail"] = proc.stderr[-500:]

    check = subprocess.run([sys.executable, "run_tests.py"], cwd=str(work),
                           capture_output=True, text=True, timeout=120)
    cell["passed"] = check.returncode == 0
    cell["check_tail"] = check.stdout[-300:]
    cell.update(analyze_transcript(cell["session_id"], arm["expect_model"]))
    return cell


def analyze_transcript(session_id, expect_model):
    hits = list((CLAUDE_DIR / "projects").glob("*/%s.jsonl" % session_id))
    if not hits:
        return {"transcript": None}
    info = {"transcript": str(hits[0]), "main_model": "", "dispatches": [],
            "main_edits": 0, "main_tools": {}, "rails_injected": False,
            "routing_check": False}
    for line in hits[0].read_text().splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        s = None
        if d.get("type") == "assistant" and not d.get("isSidechain"):
            if not info["main_model"]:
                info["main_model"] = (d.get("message") or {}).get("model", "")
            for b in (d.get("message") or {}).get("content", []):
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    n = b["name"]
                    info["main_tools"][n] = info["main_tools"].get(n, 0) + 1
                    if n in ("Edit", "Write"):
                        info["main_edits"] += 1
                    if n == "Agent":
                        i = b.get("input", {})
                        info["dispatches"].append(
                            {"subagent_type": i.get("subagent_type"),
                             "prompt_chars": len(i.get("prompt", ""))})
        else:
            s = line
        if s and not info["rails_injected"] and "OPUS RAILS" in s:
            info["rails_injected"] = True
        if s and not info["routing_check"] and "ROUTING CHECK" in s:
            info["routing_check"] = True
    info["arm_violation"] = bool(info["main_model"]) and \
        not info["main_model"].startswith(expect_model)
    return info


def summarize(cells):
    lines = ["| task | arm | pass | wall s | cost $ | turns | dispatches | "
             "main edits | rails | model ok |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for c in sorted(cells, key=lambda c: (c["task"], c["arm"], c["rep"])):
        disp = ",".join("%s(%d)" % (d["subagent_type"], d["prompt_chars"])
                        for d in c.get("dispatches", [])) or "-"
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            c["task"], c["arm"], "PASS" if c["passed"] else "FAIL",
            c["wall_s"], c.get("cost_usd", "?"), c.get("num_turns", "?"),
            disp, c.get("main_edits", "?"),
            "yes" if c.get("rails_injected") else "no",
            "VIOLATION" if c.get("arm_violation") else "ok"))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", nargs="*", default=None)
    ap.add_argument("--arms", nargs="*", default=list(ARMS))
    ap.add_argument("--reps", type=int, default=1)
    args = ap.parse_args()

    task_dirs = [d for d in sorted((BENCH / "tasks").iterdir())
                 if d.is_dir() and (args.tasks is None or d.name in args.tasks)]
    if not task_dirs:
        sys.exit("no tasks matched")
    permission_args = (["--permission-mode", "acceptEdits"]
                       if _claude_supports("--permission-mode") else [])

    out_dir = BENCH / "results" / ("run-%d" % int(time.time()))
    out_dir.mkdir(parents=True)
    cells = []
    for task in task_dirs:
        for arm in args.arms:
            for rep in range(args.reps):
                print("running %s / %s / rep %d ..." % (task.name, arm, rep))
                cell = run_cell(task, arm, rep, permission_args)
                cells.append(cell)
                print("  -> %s in %ss, dispatches=%d, model=%s" % (
                    "PASS" if cell["passed"] else "FAIL", cell["wall_s"],
                    len(cell.get("dispatches", [])), cell.get("main_model")))
                (out_dir / "results.json").write_text(json.dumps(cells, indent=1))
    (out_dir / "summary.md").write_text(summarize(cells) + "\n")
    print("\n" + summarize(cells))
    print("\nresults: %s" % out_dir)


if __name__ == "__main__":
    main()
