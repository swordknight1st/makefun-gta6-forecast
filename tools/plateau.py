"""Pick the centre of the plateau, not the spike.

Every grid search so far returns a single argmin that moves with the sample: 0.25/0.08 on the
16 large comparables, 0.30/0.06 under bootstrap refits, 0.25/0.12 or 0.20/0.14 on the 28
comparables from 10,000 viewers up. When the argmin moves but the neighbourhood does not, the
honest choice is the centre of the region that is statistically indistinguishable from the
best: every (S0, S1) whose pooled loss is within TOLERANCE of the minimum, averaged.

This prints that centre per bucket, the size of the region, and how the centre scores against
the spike it replaces, on the same rows and under leave-one-out.

Read-only: prints tables, writes nothing.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from band_check import loss  # noqa: E402
from buckets import BUCKETS, GRID, all_rows, pooled  # noqa: E402

TOLERANCE = 0.001


def plateau(rows, tol=TOLERANCE):
    scored = [(pooled(rows, a, b), a, b) for a, b in GRID]
    best = min(scored)
    region = [(a, b) for m, a, b in scored if m <= best[0] + tol]
    c0 = sum(a for a, _ in region) / len(region)
    c1 = sum(b for _, b in region) / len(region)
    return best, region, c0, c1


def loo_fixed(rows, s0, s1):
    return sum(loss(r["p1"], s0, s1, r["truth"]) for r in rows) / len(rows)


def main():
    rows = all_rows()
    for lo, hi, label in BUCKETS:
        sub = [r for r in rows if lo <= r["p1"] < hi]
        if len(sub) < 3:
            continue
        best, region, c0, c1 = plateau(sub)
        print("%s (n=%d)" % (label, len(sub)))
        print("  spike   %.2f/%.2f  pooled %.6f" % (best[1], best[2], best[0]))
        print("  plateau %d cells within %.3f, centre %.31f/%.31f" % (len(region), TOLERANCE, c0, c1))
        print("  centre  %.2f/%.2f  pooled %.6f  loo %.6f"
              % (round(c0, 2), round(c1, 2), pooled(sub, c0, c1), loo_fixed(sub, c0, c1)))
        print("  house   0.00/0.15  pooled %.6f  loo %.6f\n"
              % (pooled(sub, 0.00, 0.15), loo_fixed(sub, 0.00, 0.15)))

    print("rounded candidates worth checking by hand:")
    for s0, s1 in ((0.20, 0.12), (0.20, 0.14), (0.25, 0.10), (0.25, 0.12), (0.15, 0.14), (0.15, 0.16)):
        big = [r for r in rows if r["p1"] >= 10000]
        print("  %.2f/%.2f  10k+ %.6f  loo %.6f" % (s0, s1, pooled(big, s0, s1), loo_fixed(big, s0, s1)))


if __name__ == "__main__":
    main()
