"""Add a fourth bucket for the biggest launches, and check it three ways.

`size_trend.py` found the trend is real (rank correlation -0.638, permutation p=0.0094) and that
the five comparables above 320,000 viewers want c=0.80, consistently across leave-one-out folds.

This asks what happens to the middle: if 320,000+ gets its own factor, the 30,000-320,000 range
needs one too, and the answer there is not c=0.80 (those comparables climb). So:

  - fit c per sub-bucket on the large range;
  - leave one out within each, since a fit on five points is worth only what it survives;
  - then score the whole entry with the fourth bucket added, through main.py itself.

Read-only on the repository.
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from band_check import LEVELS  # noqa: E402
from score_entry import KIT, comparables  # noqa: E402

Z = [-1.645, -0.674, 0.0, 0.674, 1.645]
CS = [round(x * 0.05, 2) for x in range(10, 41)]


def loss(p1, c, s0, s1, truth):
    total, n = 0.0, 0
    for h in range(2, 25):
        y = truth.get(h)
        if y is None or y <= 0:
            continue
        y = max(float(y), 1.0)
        sigma = s0 + s1 * math.sqrt(h - 1)
        for tau, z in zip(LEVELS, Z):
            q = max(p1 * c * math.exp(z * sigma), 1.0)
            d = math.log(y) - math.log(q)
            total += 2 * max(tau * d, (tau - 1) * d)
            n += 1
    return total / n


def fit(rows, band):
    return min((sum(loss(r["p1"], c, band[0], band[1], r["truth"]) for r in rows) / len(rows), c)
               for c in CS)


def loo(rows, band):
    picks, held = [], 0.0
    for i, h in enumerate(rows):
        rest = rows[:i] + rows[i + 1:]
        _, c = fit(rest, band)
        picks.append(c)
        held += loss(h["p1"], c, band[0], band[1], h["truth"])
    return picks, held / len(rows)


def main():
    rows = comparables(KIT)
    plans = [
        ("30,000-320,000", 30_000, 320_000, (0.25, 0.10)),
        ("320,000+", 320_000, 10 ** 12, (0.25, 0.10)),
        ("100,000-320,000", 100_000, 320_000, (0.25, 0.10)),
    ]
    for label, lo, hi, band in plans:
        sub = [r for r in rows if lo <= r["p1"] < hi]
        if len(sub) < 3:
            print("%s: n=%d, too few" % (label, len(sub)))
            continue
        m, c = fit(sub, band)
        picks, held = loo(sub, band)
        flat = sum(loss(r["p1"], 1.00, band[0], band[1], r["truth"]) for r in sub) / len(sub)
        uniq = sorted(set(picks))
        print("%s (n=%d) band %.2f/%.2f" % (label, len(sub), band[0], band[1]))
        print("   best c=%.2f (%.6f)   flat c=1.00 (%.6f)" % (c, m, flat))
        print("   loo picks: %s   held-out %.6f"
              % (", ".join("%.2f x%d" % (u, picks.count(u)) for u in uniq), held))
        print()


if __name__ == "__main__":
    main()
