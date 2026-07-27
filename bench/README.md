# bench — isolated Opus 5 vs opus-rail, measured

A harness that runs the same tasks against two arms in fresh sandboxes:

- **`baseline`** — isolated Opus 5: `claude --model claude-opus-5 --print`, no
  rails injected (headless sessions get no first-prompt injection by design).
- **`rail`** — the opus-rail workflow: `claude --model opus --print` with a
  pre-generated `--session-id` whose model flag is written before launch, so the
  hook delivers the real rails + routing check exactly as in interactive use.
  Requires the full system installed (`full/INSTALL.md`).

Each run gets a fresh temp workdir with the task's files, one prompt, and an
objective check (`python3 run_tests.py`, plain asserts, no test framework). The
harness records, per run:

| metric | source |
|---|---|
| pass/fail | the task's tests, exit code |
| wall time, cost, turns, token usage | `--output-format json` |
| subagent dispatches (by type, prompt size) | session transcript |
| direct Edit/Write by the main loop | session transcript |
| main-loop model (verifies arm isolation) | session transcript |

## Run it

```bash
python3 bench/run.py                 # all tasks, both arms, 1 rep
python3 bench/run.py --tasks kv-ttl-store --reps 3
python3 bench/run.py --arms rail     # one arm only
```

Results land in `bench/results/run-<stamp>/` as `results.json` plus a
`summary.md` table. Runs consume real API/subscription usage — start with one
task before launching the full suite.

## Honest methodology notes

- **What this measures:** whether the opus-rail *workflow* (4.8 orchestrating,
  scoped Opus 5 dispatches) beats *isolated Opus 5* on the same tasks — on
  correctness first, then efficiency (tokens, cost, orchestrator context).
- **Arm isolation is verified, not assumed:** every run's transcript is checked
  for which model actually drove the main loop; runs that resolve to the wrong
  model are flagged `arm_violation` and must be discarded.
- **Installed agents are visible to both arms.** If the baseline chooses to
  delegate, that's recorded (dispatch counts per arm are in the results) — the
  comparison is between *entry points*, with behavior fully observable.
- **Small n is a pilot, not a claim.** Two tasks at one rep validate the
  harness; statistical statements need more tasks and ≥3 reps per cell. Task
  outcomes are binary and noisy; prefer adding tasks over adding reps.
- **Tasks are original to this repo** and use only the Python stdlib, so
  neither arm needs dependencies and checks can't flake on environment.

## Adding a task

```
bench/tasks/<name>/
  prompt.txt      what the session is asked to do
  files/          copied into the sandbox before the run
  expected.md     (optional) notes on what a correct solution contains
```

Every sandbox also receives `run_tests.py` (from `bench/harness/`), which
discovers `test_*` functions in `test_*.py` files and exits non-zero on any
failure — that exit code is the pass/fail verdict.
