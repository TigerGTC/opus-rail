import pathlib
import subprocess
import sys

import triage

LINES = pathlib.Path("sample.log").read_text().splitlines()


def test_count_by_level():
    assert triage.count_by_level(LINES) == {"ERROR": 4, "WARN": 3, "INFO": 2}


def test_count_ignores_garbage():
    assert "garbage" not in "".join(triage.count_by_level(LINES))


def test_worst_offenders():
    assert triage.worst_offenders(LINES, "ERROR") == ["db timeout", "disk full"]


def test_worst_offenders_ties_alpha():
    lines = ["WARN b b", "WARN a a", "WARN b b", "WARN a a"]
    assert triage.worst_offenders(lines, "WARN", top_n=2) == ["a a", "b b"]


def test_main_prints_sorted_counts():
    out = subprocess.run([sys.executable, "triage.py", "sample.log"],
                         capture_output=True, text=True, timeout=30).stdout
    assert out.splitlines() == ["ERROR=4", "INFO=2", "WARN=3"]
