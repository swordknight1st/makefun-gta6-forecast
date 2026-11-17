"""Sweep the centre factor per bucket, on the real entry, with leave-one-out.

The first pass fitted c on three coarse buckets and got 0.90 / 1.50 / 2.00. The 30,000+ bucket
barely moved (0.291768 to 0.290089), which says c=0.90 is nearly a no-op there: that bucket's
median hour-24 / hour-1 ratio is about 1.25, because an early decay and a prime-time climb
cancel. This sweeps c finely inside each bucket and reports both the full-sample best and the
leave-one-out best, so the shipped value is one that survives being refitted.

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
CS = [round(x * 0.05, 2) for x in range(12, 45)]  # 0.60 .. 2.20
BANDS = {"30k+": (0.25, 0.10), "5k-30k": (0.40, 0.20), "under5k": (0.80, 0.50)}


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
    return total / n if n else None


def best_c(rows, band):
    return min((sum(loss(r["p1"], c, band[0], band[1], r["truth"]) for r in rows) / len(rows), c)
               for c in CS)


def main():
    rows = comparables(KIT)
    for label, lo, hi in (("30,000+", 30_000, 10 ** 12), ("5,000-30,000", 5_000, 30_000),
                          ("under 5,000", 0, 5_000)):
        sub = [r for r in rows if lo <= r["p1"] < hi]
        band = BANDS["30k+" if lo >= 30_000 else ("5k-30k" if lo >= 5_000 else "under5k")]
        m, c = best_c(sub, band)
        picks = []
        held = 0.0
        for i, h in enumerate(sub):
            rest = sub[:i] + sub[i + 1:]
            _, c2 = best_c(rest, band)
            picks.append(c2)
            held += loss(h["p1"], c2, band[0], band[1], h["truth"])
        uniq = sorted(set(picks))
        print("%s (n=%d) band %.2f/%.2f" % (label, len(sub), band[0], band[1]))
        print("   full-sample c=%.2f loss %.6f" % (c, m))
        print("   loo picks: %s   held-out %.6f"
              % (", ".join("%.2f x%d" % (u, picks.count(u)) for u in uniq), held / len(sub)))
        for cc in (0.85, 0.90, 0.95, 1.00, 1.05, 1.10):
            v = sum(loss(r["p1"], cc, band[0], band[1], r["truth"]) for r in sub) / len(sub)
            print("     c=%.2f -> %.6f" % (cc, v))
        print()


if __name__ == "__main__":
    main()
