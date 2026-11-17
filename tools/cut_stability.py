"""Is the 320,000 cut real, or an artefact of picking the boundary after seeing the data?

The fourth bucket was added because the five comparables above 320,000 viewers decay. A cut
chosen that way can flatter itself: any boundary drawn where the data already looked
different will separate that data. This sweeps the boundary and reports, for each candidate:

  - how many comparables fall above it and what c they fit to,
  - the pooled loss over all 37 with that boundary,
  - whether a leave-one-out within the upper bucket still picks that c.

A real regime shows as a plateau: many nearby cuts give nearly the same score, and the factor
stays stable. An artefact shows as a spike that only the chosen cut achieves.

Read-only: prints a table.
"""

import itertools
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from band_check import LEVELS  # noqa: E402
from score_entry import KIT, comparables  # noqa: E402

Z = [-1.645, -0.674, 0.0, 0.674, 1.645]
CS = [round(x * 0.05, 2) for x in range(10, 41)]
BAND = (0.25, 0.10)


def loss(p1, c, truth):
    total, n = 0.0, 0
    for h in range(2, 25):
        y = truth.get(h)
        if y is None or y <= 0:
            continue
        y = max(float(y), 1.0)
        sigma = BAND[0] + BAND[1] * math.sqrt(h - 1)
        for tau, z in zip(LEVELS, Z):
            q = max(p1 * c * math.exp(z * sigma), 1.0)
            d = math.log(y) - math.log(q)
            total += 2 * max(tau * d, (tau - 1) * d)
            n += 1
    return total / n


def best_c(rows):
    return min((sum(loss(r["p1"], c, r["truth"]) for r in rows) / len(rows), c) for c in CS)


def main():
    rows = comparables(KIT)
    print("%-9s %4s %6s %10s %10s %-22s" % ("cut", "n>=", "c", "upper loss", "loo held", "loo picks"))
    for cut in (150_000, 200_000, 250_000, 300_000, 320_000, 350_000, 400_000, 500_000, 800_000):
        upper = [r for r in rows if r["p1"] >= cut]
        if len(upper) < 3:
            print("%-9d %4d  too few to fit" % (cut, len(upper)))
            continue
        m, c = best_c(upper)
        picks, held = [], 0.0
        for i, h in enumerate(upper):
            rest = upper[:i] + upper[i + 1:]
            _, cc = best_c(rest)
            picks.append(cc)
            held += loss(h["p1"], cc, h["truth"])
        uniq = sorted(set(picks))
        print("%-9d %4d %6.2f %10.6f %10.6f %-22s"
              % (cut, len(upper), c, m, held / len(upper),
                 ",".join("%.2f x%d" % (u, picks.count(u)) for u in uniq)))

    print("\nthe upper bucket's composition at each cut (p1 and h24/h1):")
    for cut in (200_000, 320_000, 400_000):
        upper = [r for r in rows if r["p1"] >= cut]
        print("  %6d: " % cut + ", ".join("%.0f:%.2f" % (r["p1"], (r["truth"].get(24) or 0) / r["p1"])
                                          for r in sorted(upper, key=lambda r: -r["p1"])))


if __name__ == "__main__":
    main()
