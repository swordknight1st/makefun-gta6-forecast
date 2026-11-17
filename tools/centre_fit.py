"""Does a single multiplicative centre offset beat a flat centre of 1.0?

The full ratio curve overfits (leave-one-out worse than flat, see shape_fit.py). But the whole
curve moves in one direction late in the day, so one number -- a constant factor c applied to
every hour, q_tau(h) = p1 * c * exp(...) -- may survive where 23 numbers did not. This fits c
per fold at three candidate values and reports the held-out loss, per bucket, so the answer
is not one pooled average hiding opposite signs.

It also asks the honest question in the other direction: if the launch is smaller, does it
grow more by the end of the day (a bigger c), as the ratios suggest?

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
CS = [0.80, 0.90, 1.00, 1.10, 1.20, 1.35, 1.50, 1.75, 2.00]
BANDS = [(0.25, 0.10), (0.30, 0.14), (0.40, 0.20), (0.50, 0.26), (0.80, 0.50)]


def loss_with(p1, c, s0, s1, truth):
    total, n = 0.0, 0
    centre = math.log(p1) + math.log(c)
    for h in range(2, 25):
        y = truth.get(h)
        if y is None or y <= 0:
            continue
        y = max(float(y), 1.0)
        sigma = s0 + s1 * math.sqrt(h - 1)
        for tau, z in zip(LEVELS, Z):
            q = max(math.exp(centre + z * sigma), 1.0)
            d = math.log(y) - math.log(q)
            total += 2 * max(tau * d, (tau - 1) * d)
            n += 1
    return total / n if n else None


def fit(rows, lo, hi):
    best = None
    for c in CS:
        for s0, s1 in BANDS:
            vals = [loss_with(r["p1"], c, s0, s1, r["truth"]) for r in rows if lo <= r["p1"] < hi]
            vals = [v for v in vals if v is not None]
            if not vals:
                continue
            m = sum(vals) / len(vals)
            if best is None or m < best[0]:
                best = (m, c, s0, s1)
    return best


BUCKETS = [(30_000, 10 ** 12, "30,000+"), (5_000, 30_000, "5,000-30,000"), (0, 5_000, "under 5,000")]


def main():
    rows = comparables(KIT)
    print("leave-one-out: one centre factor and one band, per bucket")
    print("%-16s %3s %-22s %10s %10s" % ("bucket", "n", "fold pick", "fold", "shipped"))
    totals = {"fold": [0.0, 0], "ship": [0.0, 0]}
    for lo, hi, label in BUCKETS:
        sub = [r for r in rows if lo <= r["p1"] < hi]
        if len(sub) < 3:
            continue
        picks = {}
        for i, held in enumerate(sub):
            rest = sub[:i] + sub[i + 1:]
            _, c, s0, s1 = fit(rest, 0, 10 ** 12)
            picks[(c, s0, s1)] = picks.get((c, s0, s1), 0) + 1
            a = loss_with(held["p1"], c, s0, s1, held["truth"])
            shipped = {0: (0.80, 0.50), 1: (0.40, 0.20), 2: (0.25, 0.10)}[
                next(k for k, (blo, bhi, _) in enumerate(BUCKETS) if blo <= held["p1"] < bhi)]
            b = loss_with(held["p1"], 1.0, shipped[0], shipped[1], held["truth"])
            totals["fold"][0] += a
            totals["fold"][1] += 1
            totals["ship"][0] += b
            totals["ship"][1] += 1
            print("%-16s %3d c=%.2f %.2f/%.2f        %10.6f %10.6f"
                  % (label if i == 0 else "", len(sub), c, s0, s1, a, b))
        top = ", ".join("c=%.2f %.2f/%.2f x%d" % (k[0], k[1], k[2], v)
                        for k, v in sorted(picks.items(), key=lambda kv: -kv[1])[:3])
        print("   fold picks: " + top)
    print("\nheld-out means: with a fitted factor %.6f   shipped (flat, no factor) %.6f"
          % (totals["fold"][0] / totals["fold"][1], totals["ship"][0] / totals["ship"][1]))

    print("\nfull-sample fit per bucket, for reference:")
    for lo, hi, label in BUCKETS:
        sub = [r for r in rows if lo <= r["p1"] < hi]
        if len(sub) < 3:
            continue
        m, c, s0, s1 = fit(sub, 0, 10 ** 12)
        print("  %-16s n=%2d  c=%.2f band %.2f/%.2f  loss %.6f" % (label, len(sub), c, s0, s1, m))


if __name__ == "__main__":
    main()
