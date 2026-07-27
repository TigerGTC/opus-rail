#!/usr/bin/env python3
"""Render a benchmark results.json as a grouped-bar SVG (three panels:
output tokens, cost, wall time). Stdlib only; deterministic; the SVG is a
static figure meant for the README, generated from committed raw results.

Usage: python3 bench/chart.py bench/results/<run>/results.json [out.svg]
"""
import json
import pathlib
import sys

ARM_ORDER = ["baseline", "rail", "rail-plus"]
ARM_LABEL = {"baseline": "Opus 5 (isolated)", "rail": "opus-rail",
             "rail-plus": "opus-rail plus"}
# Categorical palette, fixed order, validated (dataviz six checks, light surface).
ARM_COLOR = {"baseline": "#3b82f6", "rail": "#e8572a", "rail-plus": "#7c3aed"}

SURFACE = "#fcfcfb"
INK, MUTED, GRID = "#1f2937", "#6b7280", "#e5e7eb"

PANEL_W, PANEL_H, PAD_L, PAD_R, GROUP_GAP, BAR_W, BAR_GAP = 780, 150, 60, 20, 46, 22, 2
TOP = 108


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;")


def bar_path(x, y0, y1, w, r=4):
    """Baseline-anchored bar with rounded data-end (top) only."""
    h = y0 - y1
    r = min(r, h, w / 2)
    return ("M%.1f %.1f L%.1f %.1f Q%.1f %.1f %.1f %.1f L%.1f %.1f "
            "Q%.1f %.1f %.1f %.1f L%.1f %.1f Z") % (
        x, y0, x, y1 + r, x, y1, x + r, y1, x + w - r, y1,
        x + w, y1, x + w, y1 + r, x + w, y0)


def panel(cells, tasks, metric, title, fmt, y_off):
    out = ["<text x='%d' y='%d' fill='%s' font-size='13' font-weight='600'>%s</text>"
           % (PAD_L, y_off - 8, INK, esc(title))]
    vals = {(c["task"], c["arm"]): c.get(metric) for c in cells}
    vmax = max((v for v in vals.values() if isinstance(v, (int, float))), default=1)
    base_y = y_off + PANEL_H
    for frac in (0.5, 1.0):
        gy = base_y - PANEL_H * frac * 0.92
        out.append("<line x1='%d' y1='%.1f' x2='%d' y2='%.1f' stroke='%s'/>"
                   % (PAD_L, gy, PANEL_W - PAD_R, gy, GRID))
        out.append("<text x='%d' y='%.1f' fill='%s' font-size='10' "
                   "text-anchor='end'>%s</text>"
                   % (PAD_L - 6, gy + 3, MUTED, esc(fmt(vmax * frac))))
    out.append("<line x1='%d' y1='%.1f' x2='%d' y2='%.1f' stroke='%s' "
               "stroke-width='1'/>" % (PAD_L, base_y, PANEL_W - PAD_R, base_y, MUTED))
    group_w = len(ARM_ORDER) * (BAR_W + BAR_GAP)
    for ti, task in enumerate(tasks):
        gx = PAD_L + 30 + ti * (group_w + GROUP_GAP + 60)
        for ai, arm in enumerate(ARM_ORDER):
            v = vals.get((task, arm))
            if not isinstance(v, (int, float)):
                continue
            x = gx + ai * (BAR_W + BAR_GAP)
            h = PANEL_H * 0.92 * (v / vmax if vmax else 0)
            y1 = base_y - max(h, 2)
            failed = not next(c for c in cells
                              if c["task"] == task and c["arm"] == arm)["passed"]
            op = "0.35" if failed else "1"
            out.append("<path d='%s' fill='%s' fill-opacity='%s'/>"
                       % (bar_path(x, base_y, y1, BAR_W), ARM_COLOR[arm], op))
            out.append("<text x='%.1f' y='%.1f' fill='%s' font-size='9' "
                       "text-anchor='middle'>%s</text>"
                       % (x + BAR_W / 2, y1 - 4, MUTED,
                          esc(fmt(v) + (" ✗" if failed else ""))))
        out.append("<text x='%.1f' y='%.1f' fill='%s' font-size='11' "
                   "text-anchor='middle'>%s</text>"
                   % (gx + group_w / 2, base_y + 16, INK, esc(task)))
    return out


def render(cells, tasks, title, panels, dst):
    H = TOP + len(panels) * (PANEL_H + 58) + 20
    svg = ["<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d' "
           "viewBox='0 0 %d %d' font-family='-apple-system,Segoe UI,sans-serif'>"
           % (PANEL_W, H, PANEL_W, H),
           "<rect width='%d' height='%d' fill='%s' rx='8'/>" % (PANEL_W, H, SURFACE),
           "<text x='%d' y='28' fill='%s' font-size='16' font-weight='700'>%s</text>"
           % (PAD_L, INK, esc(title)),
           "<text x='%d' y='46' fill='%s' font-size='11'>Faded bar + ✗ = task "
           "tests failed for that run. Source: results.json in this directory."
           "</text>" % (PAD_L, MUTED)]
    lx = PAD_L
    for arm in ARM_ORDER:
        svg.append("<rect x='%d' y='58' width='10' height='10' rx='2' fill='%s'/>"
                   % (lx, ARM_COLOR[arm]))
        label = ARM_LABEL[arm]
        svg.append("<text x='%d' y='67' fill='%s' font-size='11'>%s</text>"
                   % (lx + 14, INK, esc(label)))
        lx += 14 + 7 * len(label) + 24
    y = TOP
    for metric, ptitle, fmt in panels:
        svg += panel(cells, tasks, metric, ptitle, fmt, y)
        y += PANEL_H + 58
    svg.append("</svg>")
    dst.write_text("\n".join(svg))
    print("wrote %s" % dst)


def main():
    src = pathlib.Path(sys.argv[1])
    out_dir = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else src.parent
    cells = json.load(open(src))
    for c in cells:
        c["n_dispatches"] = len(c.get("dispatches") or [])
    tasks = sorted({c["task"] for c in cells})
    knum = lambda v: "%dk" % round(v / 1000) if v >= 1000 else "%d" % v
    render(cells, tasks,
           "opus-rail benchmark — efficiency, three arms, identical tasks",
           [("tokens_out", "Output tokens (whole session)", knum),
            ("cost_usd", "Cost (USD)", lambda v: "$%.2f" % v),
            ("wall_s", "Wall time (seconds)", lambda v: "%ds" % v)],
           out_dir / "chart-efficiency.svg")
    render(cells, tasks,
           "opus-rail benchmark — behavior, three arms, identical tasks",
           [("n_dispatches", "Subagent dispatches (delegation)", lambda v: "%d" % v),
            ("main_edits", "Direct Edit/Write by the main loop (lower = more delegation)",
             lambda v: "%d" % v),
            ("final_context_tokens", "Orchestrator context on its final turn (tokens)",
             knum)],
           out_dir / "chart-behavior.svg")


if __name__ == "__main__":
    main()
