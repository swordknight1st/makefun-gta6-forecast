"""What the small-first-hour cohort actually looks like, case by case.

`small_loo.py` says the small cohort wants S0=0.40, S1=0.30, a band far wider than anything
the large cohort supports, with pooled loss above 1.25 where the large cohort sits near 0.25.
A loss that high means the forecast is off by factors, not percentages, so this prints each
small comparable's hour-1 print, its hour-24 print, the ratio between them, and the loss the
house band pays: a few tiny launches whose viewers collapse to a handful drag the mean, and
that is a different problem from a band being too narrow.

Read-only: prints a table, writes nothing.
"""

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from band_check import loss  # noqa: E402
from small_loo import small_rows  # noqa: E402


def main():
    rows = small_rows()
    print("%-40s %7s %7s %7s %8s %9s %9s"
          % ("comparable", "p1", "p12", "p24", "p24/p1", "house", "large"))
    for r in rows:
        t = r["truth"]
        p12 = t.get(12)
        p24 = t.get(24)
        ratio = (p24 / r["p1"]) if p24 and r["p1"] else float("nan")
        print("%-40s %7.0f %7.0f %7.0f %8.3f %9.6f %9.6f"
              % (r["name"][:40], r["p1"], p12 or 0, p24 or 0, ratio,
                 loss(r["p1"], 0.00, 0.15, t), loss(r["p1"], 0.25, 0.08, t)))

    # split by first-hour size: tiny launches behave nothing like mid-size ones
    for lo, hi, label in ((1, 1000, "under 1,000"), (1000, 10000, "1,000-10,000"),
                          (10000, 100000, "10,000-100,000")):
        band_rows = [r for r in rows if lo <= r["p1"] < hi]
        if not band_rows:
            continue
        for name, s0, s1 in (("house 0.00/0.15", 0.00, 0.15), ("wide 0.40/0.30", 0.40, 0.30),
                             ("wide 0.25/0.20", 0.25, 0.20)):
            vals = [loss(r["p1"], s0, s1, r["truth"]) for r in band_rows]
            vals = [v for v in vals if v is not None]
            print("\n  %s (n=%d) %-16s %.6f" % (label, len(band_rows), name, sum(vals) / len(vals)))


if __name__ == "__main__":
    main()
