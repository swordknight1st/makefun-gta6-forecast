"""Leave-one-out check of the band: does a wider band actually generalise?

`per_case.py` shows the grid's pooled winner is wider (S0=0.20, S1=0.10) than the band the
entry ships (0.10, 0.12). With 16 cases and a 5x7 grid, a pooled winner can be one
comparable's outlier. This runs leave-one-out: for each held-out comparable, fit the band on
the other 15 and score it on the held-out one, then compare
  - the LOO-fitted band per fold,
  - the fixed candidates (house, shipped, wide),
by mean held-out loss and by how often each wins a held-out case.

A band that only wins in-sample and loses under LOO is not a real gain.

Read-only: prints a table, writes nothing.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from band_check import SMALL, day_rows, loss  # noqa: E402

KIT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..",
                                                        "gta6-twitch-ccu-forecast-01-kit")
IN_DIR = os.path.join(KIT, "input")

FIXED = [
    ("house  0.00/0.15", 0.00, 0.15),
    ("shipped 0.10/0.12", 0.10, 0.12),
    ("wide   0.20/0.10", 0.20, 0.10),
    ("wide2  0.15/0.12", 0.15, 0.12),
    ("mid    0.15/0.15", 0.15, 0.15),
]
GRID = [(s0 / 100.0, s1 / 100.0) for s0 in range(0, 26, 5) for s1 in range(6, 23, 2)]


def load():
    cases = sorted(n for n in os.listdir(IN_DIR) if n.endswith(".in"))
    comps = json.load(open(os.path.join(IN_DIR, cases[0]), encoding="utf-8"))["comparables"]
    seen, out = set(), []
    for comp in comps:
        key = (comp.get("name"), comp.get("day_start"))
        if key in seen:
            continue
        seen.add(key)
        day = day_rows(comp)
        p1 = day.get(1)
        if p1 is None or p1 < SMALL:
            continue
        out.append({"name": comp.get("name") or "?", "p1": float(p1), "truth": day})
    return sorted(out, key=lambda r: r["p1"])


def fit(rows):
    best = None
    for s0, s1 in GRID:
        vals = [loss(r["p1"], s0, s1, r["truth"]) for r in rows]
        vals = [v for v in vals if v is not None]
        if not vals:
            continue
        m = sum(vals) / len(vals)
        if best is None or m < best[0]:
            best = (m, s0, s1)
    return best


def main():
    rows = load()
    print("leave-one-out over %d comparables with a first hour of at least %d" % (len(rows), SMALL))
    print("%-42s %8s  %9s  %9s  %9s  %9s" % ("held out", "p1", "loo band", "loo loss", "ship loss", "wire loss"))
    loo_total, ship_total, wide_total, n = 0.0, 0.0, 0.0, 0
    loo_beats_ship = loo_beats_wide = 0
    for i, held in enumerate(rows):
        rest = rows[:i] + rows[i + 1:]
        _, s0, s1 = fit(rest)
        v_loo = loss(held["p1"], s0, s1, held["truth"])
        v_ship = loss(held["p1"], 0.10, 0.12, held["truth"])
        v_wide = loss(held["p1"], 0.20, 0.10, held["truth"])
        if v_loo is None:
            continue
        n += 1
        loo_total += v_loo
        ship_total += v_ship
        wide_total += v_wide
        loo_beats_ship += v_loo < v_ship
        loo_beats_wide += v_loo < v_wide
        print("%-42s %8.0f   %.2f/%.2f  %9.6f  %9.6f  %9.6f"
              % (held["name"][:42], held["p1"], s0, s1, v_loo, v_ship, v_wide))
    print("\nmean held-out loss  loo %.6f   shipped %.6f   wide %.6f"
          % (loo_total / n, ship_total / n, wide_total / n))
    print("loo beats shipped on %d of %d held-out cases; loo beats wide on %d"
          % (loo_beats_ship, n, loo_beats_wide))

    print("\nfixed candidates, pooled over the %d" % len(rows))
    for name, s0, s1 in FIXED:
        vals = [loss(r["p1"], s0, s1, r["truth"]) for r in rows]
        vals = [v for v in vals if v is not None]
        print("  %-20s %.6f" % (name, sum(vals) / len(vals)))


if __name__ == "__main__":
    main()
