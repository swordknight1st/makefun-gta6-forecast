"""The comparables where a wider band loses, and what each of them did in hour 1.

`score_entry.py` shows the shipped band beats the house baseline on 25 of 28 comparables from
10,000 viewers up, but loses badly on a few: Resident Evil Requiem by 0.28, Clair Obscur by
0.23, Halo Infinite by 0.03. A band that widens the tails helps a case whose later hours stay
inside the band and hurts one that jumps outside it; this prints, per losing case, hour 1's
print against the centre and the 5% / 95% edges the shipped band draws at the last hour, so
the failure mode is visible rather than assumed.

Read-only: prints a table, writes nothing.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from band_check import LEVELS  # noqa: E402
from score_entry import KIT, comparables  # noqa: E402
SHIP = (0.20, 0.14)
WIDE = (0.40, 0.32)
HOUSE = (0.00, 0.15)
Z = [-1.645, -0.674, 0.0, 0.674, 1.645]


def band_of(p1):
    if p1 >= 10_000:
        return SHIP
    return WIDE


def loss_case(p1, s0, s1, truth):
    total, n = 0.0, 0
    import math
    for h in range(2, 25):
        y = truth.get(h)
        if y is None or y <= 0:
            continue
        y = max(float(y), 1.0)
        for tau, z in zip(LEVELS, Z):
            q = p1 * math.exp(z * (s0 + s1 * (h - 1) ** 0.5))
            q = max(q, 1.0)
            d = math.log(y) - math.log(q)
            total += 2 * max(tau * d, (tau - 1) * d)
            n += 1
    return total / n if n else float("nan")


def main():
    rows = comparables(KIT)
    print("%-38s %7s %7s %7s %7s %7s  %8s"
          % ("comparable", "p1", "h24", "ratio", "shipped", "house", "delta"))
    rows.sort(key=lambda r: loss_case(r["p1"], *band_of(r["p1"]), r["truth"])
              - loss_case(r["p1"], *HOUSE, r["truth"]), reverse=True)
    for r in rows:
        s0, s1 = band_of(r["p1"])
        a = loss_case(r["p1"], s0, s1, r["truth"])
        b = loss_case(r["p1"], *HOUSE, r["truth"])
        h24 = r["truth"].get(24)
        ratio = (h24 / r["p1"]) if h24 and r["p1"] else float("nan")
        print("%-38s %7.0f %7.0f %7.2f %7.4f %7.4f  %+8.4f"
              % (r["name"][:38], r["p1"], h24 or 0, ratio, a, b, a - b))

    print("\nwhat the shipped band claims at hour 24 for the three worst losses:")
    for r in rows[:3]:
        s0, s1 = band_of(r["p1"])
        sigma = s0 + s1 * (24 - 1) ** 0.5
        lo = r["p1"] * __import__("math").exp(-1.645 * sigma)
        hi = r["p1"] * __import__("math").exp(1.645 * sigma)
        print("  %-38s p1=%7.0f  h24 truth=%7.0f   5%%=%.0f  95%%=%.0f  %s"
              % (r["name"][:38], r["p1"], r["truth"].get(24) or 0, lo, hi,
                 "inside" if lo <= (r["truth"].get(24) or 0) <= hi else "OUTSIDE"))


if __name__ == "__main__":
    main()
