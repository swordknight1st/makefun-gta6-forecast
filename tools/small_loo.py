"""Which band the small-first-hour cohort wants, checked leave-one-out.

main.py hands a case whose first hour is under 100,000 viewers the house baseline's band
(0, 0.15). That fallback was never fitted, only inherited, so this fits it: leave-one-out
over the 21 small comparables, refitting (S0, S1) per fold, and comparing the held-out mean
with the baseline band and with the large-cohort band.

Two things are worth knowing before changing it: whether a small first hour wants a very
different band, and whether the choice is stable enough to beat the baseline out of sample.

Read-only: prints a table, writes nothing.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from band_check import SMALL, day_rows, loss  # noqa: E402

KIT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..",
                                                        "gta6-twitch-ccu-forecast-01-kit")
IN_DIR = os.path.join(KIT, "input")

GRID = [(s0 / 100.0, s1 / 100.0) for s0 in range(0, 41, 5) for s1 in range(6, 31, 2)]
FIXED = [
    ("house 0.00/0.15", 0.00, 0.15),
    ("large 0.25/0.08", 0.25, 0.08),
    ("small 0.05/0.14", 0.05, 0.14),
    ("small 0.00/0.20", 0.00, 0.20),
]


def small_rows():
    import json
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
        if p1 is None or p1 >= SMALL or p1 < 1:
            continue
        out.append({"name": comp.get("name") or "?", "p1": float(p1), "truth": day})
    return sorted(out, key=lambda r: r["p1"])


def pooled(rows, s0, s1):
    vals = [loss(r["p1"], s0, s1, r["truth"]) for r in rows]
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals)


def main():
    rows = small_rows()
    print("small cohort: %d comparables with 1 <= first hour < %d" % (len(rows), SMALL))
    print("pooled loss:")
    for name, s0, s1 in FIXED:
        print("  %-18s %.6f" % (name, pooled(rows, s0, s1)))
    best = min((pooled(rows, s0, s1), s0, s1) for s0, s1 in GRID)
    print("  %-18s %.6f  (best on the grid)" % ("fitted %.2f/%.2f" % (best[1], best[2]), best[0]))

    print("\nleave-one-out: the fold refits the whole grid on the other %d" % (len(rows) - 1))
    tot_fit = tot_house = tot_large = 0.0
    picks = {}
    for i, held in enumerate(rows):
        rest = rows[:i] + rows[i + 1:]
        _, s0, s1 = min((pooled(rest, a, b), a, b) for a, b in GRID)
        picks[(s0, s1)] = picks.get((s0, s1), 0) + 1
        tot_fit += loss(held["p1"], s0, s1, held["truth"])
        tot_house += loss(held["p1"], 0.00, 0.15, held["truth"])
        tot_large += loss(held["p1"], 0.25, 0.08, held["truth"])
    n = len(rows)
    print("  held-out mean, fold-fitted   %.6f" % (tot_fit / n))
    print("  held-out mean, house band    %.6f" % (tot_house / n))
    print("  held-out mean, large band    %.6f" % (tot_large / n))
    print("  fold picks: " + ", ".join("%.2f/%.2f x%d" % (k[0], k[1], v) for k, v in sorted(picks.items(), key=lambda kv: -kv[1])[:6]))


if __name__ == "__main__":
    main()
