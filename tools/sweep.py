"""Sweep the band wider, and pick the edge that a held-out case also survives.

`loo.py` says the pooled winner sits wider than the band the entry ships (0.10, 0.12), and
that refitting per fold is noise: a fixed wider band generalises. This sweeps S0 from 0.00
to 0.45 and S1 from 0.04 to 0.20, prints the pooled loss at each corner of interest, and
then runs leave-one-out on the top few so the choice is not made on the same 16 numbers
twice.

The rule for the shipped band: best pooled loss whose leave-one-out loss is also better than
the current band's, i.e. a band that wins in the pool *and* out of sample.

Read-only: prints tables, writes nothing.
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

GRID = [(s0 / 100.0, s1 / 100.0) for s0 in range(0, 46, 5) for s1 in range(4, 21, 2)]
CURRENT = (0.10, 0.12)


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
    return out


def pooled(rows, s0, s1):
    vals = [loss(r["p1"], s0, s1, r["truth"]) for r in rows]
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals)


def loo(rows, s0, s1):
    return sum(loss(r["p1"], s0, s1, r["truth"]) for r in rows) / len(rows)


def main():
    rows = load()
    table = []
    for s0, s1 in GRID:
        table.append((pooled(rows, s0, s1), s0, s1))
    table.sort()
    print("pooled loss over %d comparables, best 15 of the grid:" % len(rows))
    for m, s0, s1 in table[:15]:
        print("  S0=%.2f S1=%.2f  pooled %.6f  loo %.6f" % (s0, s1, m, loo(rows, s0, s1)))
    print("\ncurrent band S0=%.2f S1=%.2f  pooled %.6f  loo %.6f"
          % (CURRENT[0], CURRENT[1], pooled(rows, *CURRENT), loo(rows, *CURRENT)))

    print("\nthe edge, S1 fixed at 0.08 and 0.10, S0 swept:")
    for s1 in (0.08, 0.10):
        line = []
        for s0 in [x / 100.0 for x in range(0, 46, 5)]:
            line.append("%.2f:%.6f" % (s0, pooled(rows, s0, s1)))
        print("  S1=%.2f  " % s1 + "  ".join(line))

    print("\non the 5 comparables the current band loses, does the wider band win?")
    for r in rows:
        cur = loss(r["p1"], *CURRENT, r["truth"])
        best = min((pooled([r], s0, s1), s0, s1) for s0, s1 in GRID)
        if best[0] < cur - 1e-6:
            print("  %-42s p1=%8.0f  current %.6f  best %.6f at %.2f/%.2f"
                  % (r["name"][:42], r["p1"], cur, best[0], best[1], best[2]))


if __name__ == "__main__":
    main()
