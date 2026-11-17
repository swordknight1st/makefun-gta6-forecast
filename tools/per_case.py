"""Per-case view of the band choice, and whether bucketing by first-hour size pays.

Pooled mean is what `band_check.py` reports, but the contest scores one case: the final
is a single run over one case whose hour-1 print is unknown until 2026-11-19T01:00Z. A
band that wins the pool can still lose most single cases. So this prints, per comparable:

  - the loss of the house baseline band (0, 0.15) and of the tuned band (0.10, 0.12),
  - which of the two wins that case, and by how much,
  - and, over a grid of (S0, S1), how often each band is the best one on a case.

It also asks the bucketed question honestly: split the 16 large comparables at the median
first hour, fit a band on one half, score it on the other, and compare with the band fitted
on everything. If the split does not beat the single band out of sample, bucketing is noise.

Read-only: prints tables, writes nothing.
"""

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from band_check import SMALL, day_rows, loss, quantiles  # noqa: E402

KIT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..",
                                                        "gta6-twitch-ccu-forecast-01-kit")
IN_DIR = os.path.join(KIT, "input")

BASE = ("house", 0.00, 0.15)
TUNED = ("tuned", 0.10, 0.12)
GRID = [(s0 / 100.0, s1 / 100.0) for s0 in range(0, 21, 5) for s1 in range(8, 21, 2)]


def comparables():
    cases = sorted(n for n in os.listdir(IN_DIR) if n.endswith(".in"))
    comps = json.load(open(os.path.join(IN_DIR, cases[0]), encoding="utf-8"))["comparables"]
    seen = set()
    out = []
    for comp in comps:
        key = (comp.get("name"), comp.get("day_start"))
        if key in seen:
            continue
        seen.add(key)
        day = day_rows(comp)
        p1 = day.get(1)
        if p1 is None:
            continue
        out.append({"name": comp.get("name") or "?", "day": comp.get("day_start"),
                    "p1": float(p1), "truth": day})
    return out


def best_band(rows):
    scored = []
    for s0, s1 in GRID:
        vals = [loss(r["p1"], s0, s1, r["truth"]) for r in rows]
        vals = [v for v in vals if v is not None]
        if vals:
            scored.append((sum(vals) / len(vals), s0, s1))
    scored.sort()
    return scored[0]


def main():
    rows = [r for r in comparables() if r["p1"] >= SMALL]
    rows.sort(key=lambda r: r["p1"])
    print("per case, first hour >= %d (n=%d)" % (SMALL, len(rows)))
    head = "%-42s %9s %9s %9s %9s  %s" % ("comparable", "p1", "house", "tuned", "tuned-house", "winner")
    print(head)
    wins = {"house": 0, "tuned": 0, "tie": 0}
    deltas = []
    for r in rows:
        b = loss(r["p1"], BASE[1], BASE[2], r["truth"])
        t = loss(r["p1"], TUNED[1], TUNED[2], r["truth"])
        d = t - b
        deltas.append(d)
        w = "tie" if abs(d) < 1e-9 else ("tuned" if d < 0 else "house")
        wins[w] += 1
        print("%-42s %9.0f %9.6f %9.6f %+9.6f  %s" % (r["name"][:42], r["p1"], b, t, d, w))
    med = sorted(deltas)[len(deltas) // 2]
    print("\nwins: tuned %d  house %d  tie %d   median delta %+.6f  worst %+.6f  best %+.6f"
          % (wins["tuned"], wins["house"], wins["tie"], med, max(deltas), min(deltas)))

    # how often is each band the per-case best over the grid
    counts = {}
    for r in rows:
        best = min(((loss(r["p1"], s0, s1, r["truth"]) or 9e9), (s0, s1)) for s0, s1 in GRID)
        counts[best[1]] = counts.get(best[1], 0) + 1
    print("\nper-case best band over the grid (how many cases each wins outright):")
    for (s0, s1), n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        print("  S0=%.2f S1=%.2f  %d" % (s0, s1, n))

    # the bucketed question, out of sample: fit low half, score high half, and the reverse
    if len(rows) >= 6:
        half = len(rows) // 2
        low, high = rows[:half], rows[half:]
        for name, fit_set, test_set in (("low half -> high half", low, high),
                                        ("high half -> low half", high, low)):
            m, s0, s1 = best_band(fit_set)
            out = [loss(r["p1"], s0, s1, r["truth"]) for r in test_set]
            out = [v for v in out if v is not None]
            allb = best_band(rows)
            on_test = [loss(r["p1"], allb[1], allb[2], r["truth"]) for r in test_set]
            on_test = [v for v in on_test if v is not None]
            print("\n%s: fitted S0=%.2f S1=%.2f (fit loss %.6f)" % (name, s0, s1, m))
            print("   out of sample, that band:   %.6f" % (sum(out) / len(out)))
            print("   out of sample, all-16 band: %.6f (S0=%.2f S1=%.2f)" % (sum(on_test) / len(on_test), allb[1], allb[2]))


if __name__ == "__main__":
    main()
