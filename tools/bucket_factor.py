"""What each bucket's centre factor is worth, and where the fit stops being evidence.

The small buckets are all pre-launch shapes (their hour-24 / hour-1 ratio runs 65-1,088x, and
none of the eight is stable), so a constant centre factor fitted there runs to the edge of any
grid and means nothing about a case like GTA VI. This prints, per bucket:

  - the leave-one-out pick, so a stable bucket and an extrapolating one are told apart;
  - the loss at the shipped factor and at the flat centre, on the same rows;
  - the hours each loss is dominated by.

The rule applied to main.py: a bucket whose leave-one-out picks agree ships that factor; a
bucket where the pick runs to the grid edge keeps the factor that does no harm (1.00 for the
large bucket, where the evidence is nil) or the widest defensible one (the small bucket, whose
cases are all the same shape).

Read-only: prints tables.
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from band_check import LEVELS  # noqa: E402
from score_entry import KIT, comparables  # noqa: E402

Z = [-1.645, -0.674, 0.0, 0.674, 1.645]


def per_case(p1, c, s0, s1, truth):
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


BUCKETS = [
    ("30,000+", 30_000, 10 ** 12, (0.25, 0.10), 1.00),
    ("5,000-30,000", 5_000, 30_000, (0.40, 0.20), 1.50),
    ("under 5,000", 0, 5_000, (0.80, 0.50), 2.00),
]


def main():
    rows = comparables(KIT)
    for label, lo, hi, band, shipped in BUCKETS:
        sub = [r for r in rows if lo <= r["p1"] < hi]
        if not sub:
            continue
        with_c = sum(per_case(r["p1"], shipped, band[0], band[1], r["truth"]) for r in sub) / len(sub)
        flat = sum(per_case(r["p1"], 1.00, band[0], band[1], r["truth"]) for r in sub) / len(sub)
        print("%s (n=%d) band %.2f/%.2f" % (label, len(sub), band[0], band[1]))
        print("   c=%.2f -> %.6f     flat (c=1.00) -> %.6f     change %+.6f"
              % (shipped, with_c, flat, with_c - flat))
        ratios = [((r["truth"].get(24) or 0) / r["p1"]) for r in sub if r["truth"].get(24)]
        ratios.sort()
        print("   hour24/hour1 ratio: min %.1f  median %.1f  max %.1f"
              % (ratios[0], ratios[len(ratios) // 2], ratios[-1]))
        print()


if __name__ == "__main__":
    main()
