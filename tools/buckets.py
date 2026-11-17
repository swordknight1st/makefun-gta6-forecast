"""Fit the band per size bucket instead of one cut at 100,000.

`small_shape.py` shows the small cohort is three regimes, not one: 1,000-10,000 viewers where
the entry's first hour is often pre-launch noise (p24/p1 up to 1,000x), 10,000-100,000 where
persistence mostly holds, and 100,000+ where it holds best. A single band for all of them is
a compromise; this fits each bucket on its own and reports the loss inside the bucket, then
checks each bucket's pick leave-one-out within that bucket.

The candidate rule for main.py: one band per bucket, each fitted only on its own bucket, so
no bucket's band is dragged by another's shape. A bucket whose leave-one-out pick disagrees
with its pooled pick is left on the safer of the two.

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

BUCKETS = [(10_000, 10 ** 12, "10,000 and up"), (1_000, 10_000, "1,000-10,000"), (1, 1_000, "under 1,000")]
GRID = [(s0 / 100.0, s1 / 100.0) for s0 in range(0, 41, 5) for s1 in range(2, 33, 2)]


def all_rows():
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
        if p1 is None or p1 < 1:
            continue
        out.append({"name": comp.get("name") or "?", "p1": float(p1), "truth": day})
    return out


def pooled(rows, s0, s1):
    vals = [loss(r["p1"], s0, s1, r["truth"]) for r in rows]
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals)


def pick(rows):
    return min((pooled(rows, a, b), a, b) for a, b in GRID)


def loo_picks(rows):
    picks = {}
    held = 0.0
    for i in range(len(rows)):
        rest = rows[:i] + rows[i + 1:]
        _, a, b = pick(rest)
        picks[(a, b)] = picks.get((a, b), 0) + 1
        held += loss(rows[i]["p1"], a, b, rows[i]["truth"])
    return picks, held / len(rows)


def main():
    rows = all_rows()
    print("bucketed fit, %d comparables in all\n" % len(rows))
    print("%-16s %3s %9s %-14s %9s %-26s %9s"
          % ("bucket", "n", "pooled", "pooled pick", "pooled loss", "loo picks", "loo held"))
    for lo, hi, label in BUCKETS:
        sub = [r for r in rows if lo <= r["p1"] < hi]
        if len(sub) < 3:
            print("%-16s %3d  too few to fit" % (label, len(sub)))
            continue
        m, a, b = pick(sub)
        picks, held = loo_picks(sub)
        top = ", ".join("%.2f/%.2f x%d" % (k[0], k[1], v) for k, v in sorted(picks.items(), key=lambda kv: -kv[1])[:3])
        print("%-16s %3d %9d %-14s %9.6f %-26s %9.6f"
              % (label, len(sub), sum(1 for r in sub if r["p1"] >= SMALL), "%.2f/%.2f" % (a, b), m, top, held))

    print("\nwhat each bucket's own band costs on the other buckets (transfer):")
    bands = {}
    for lo, hi, label in BUCKETS:
        sub = [r for r in rows if lo <= r["p1"] < hi]
        if len(sub) >= 3:
            _, a, b = pick(sub)
            bands[label] = (a, b)
    heads = ["house 0.00/0.15"] + ["%s %.2f/%.2f" % (k, v[0], v[1]) for k, v in bands.items()]
    print("%-16s " % "fitted on \\ scored on" + " ".join("%-22s" % h for h in heads))
    for lo, hi, label in BUCKETS:
        sub = [r for r in rows if lo <= r["p1"] < hi]
        if not sub:
            continue
        cells = ["%.6f" % pooled(sub, 0.00, 0.15)]
        for _, v in bands.items():
            cells.append("%.6f" % pooled(sub, v[0], v[1]))
        print("%-16s " % label + " ".join("%-22s" % c for c in cells))


if __name__ == "__main__":
    main()
