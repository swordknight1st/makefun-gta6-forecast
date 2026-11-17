"""Fit a shape curve and a band together, and check both leave-one-out.

`shape.py` shows a flat centre is wrong: the real median curve dips to 0.72-0.88 of hour 1
between hours 2 and 12, then climbs to 2.0-2.4 by prime time. Fitting a per-hour ratio curve
cuts log error from 1.1421 to 1.0544 over all 37 comparables (0.5246 to 0.4738 over the 28 at
10,000+), which is a much bigger effect than any band ever gave.

This fits the two together: for each fold, take the per-hour median log ratio and a band
S0/S1 fitted on the fitting rows, then score the held-out comparable with

    q_tau(h) = p1 * r_h * exp(z_tau * (S0 + S1 * sqrt(h - 1)))

and compare against the shipped flat-centre layout on the same rows. A shape that only helps
in sample would show as a worse leave-one-out number than the flat centre's.

Read-only: prints a table.
"""

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from band_check import LEVELS  # noqa: E402
from score_entry import KIT, comparables  # noqa: E402

Z = [-1.645, -0.674, 0.0, 0.674, 1.645]
GRID = [(s0 / 100.0, s1 / 100.0) for s0 in range(0, 61, 5) for s1 in range(0, 33, 2)]
FLAT = [(0.25, 0.10), (0.40, 0.20), (0.80, 0.50)]
FLAT_CUTS = (5_000, 30_000)


def ratio(r, h):
    y = r["truth"].get(h)
    if y is None or y <= 0:
        return None
    return math.log(max(float(y), 1.0)) - math.log(r["p1"])


def median_curve(rows):
    curve = {}
    for h in range(2, 25):
        vals = [ratio(r, h) for r in rows]
        vals = [v for v in vals if v is not None]
        vals.sort()
        if vals:
            n = len(vals)
            curve[h] = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2.0
    return curve


def loss_with(p1, curve, s0, s1, truth):
    total, n = 0.0, 0
    for h in range(2, 25):
        y = truth.get(h)
        if y is None or y <= 0:
            continue
        y = max(float(y), 1.0)
        centre = math.log(p1) + curve.get(h, 0.0)
        sigma = s0 + s1 * math.sqrt(h - 1)
        for tau, z in zip(LEVELS, Z):
            q = max(math.exp(centre + z * sigma), 1.0)
            d = math.log(y) - math.log(q)
            total += 2 * max(tau * d, (tau - 1) * d)
            n += 1
    return total / n if n else None


def band_for_flat(p1):
    if p1 >= FLAT_CUTS[1]:
        return FLAT[0]
    if p1 >= FLAT_CUTS[0]:
        return FLAT[1]
    return FLAT[2]


def fit_band(rows, curve):
    best = None
    for s0, s1 in GRID:
        vals = [loss_with(r["p1"], curve, s0, s1, r["truth"]) for r in rows]
        vals = [v for v in vals if v is not None]
        if not vals:
            continue
        m = sum(vals) / len(vals)
        if best is None or m < best[0]:
            best = (m, s0, s1)
    return best


def main():
    rows = comparables(KIT)
    print("leave-one-out: shape + band, against the shipped flat-centre layout")
    print("%-38s %8s %9s %9s %9s" % ("held out", "p1", "shape", "flat", "delta"))
    tot_s = tot_f = 0.0
    n = 0
    for i, held in enumerate(rows):
        rest = rows[:i] + rows[i + 1:]
        curve = median_curve(rest)
        _, s0, s1 = fit_band(rest, curve)
        a = loss_with(held["p1"], curve, s0, s1, held["truth"])
        b0, b1 = band_for_flat(held["p1"])
        b = loss_with(held["p1"], {}, b0, b1, held["truth"])
        if a is None or b is None:
            continue
        tot_s += a
        tot_f += b
        n += 1
        print("%-38s %8.0f %9.6f %9.6f %+9.6f" % (held["name"][:38], held["p1"], a, b, a - b))
    print("\nheld-out means: shape + fitted band %.6f   flat + shipped band %.6f   (%d cases)"
          % (tot_s / n, tot_f / n, n))

    curve = median_curve(rows)
    print("\nfull-sample median log ratio by hour (the curve to ship):")
    print("  " + "  ".join("%d:%.4f" % (h, curve[h]) for h in range(2, 25)))
    _, s0, s1 = fit_band(rows, curve)
    print("  band fitted with that curve on all 37: S0=%.2f S1=%.2f" % (s0, s1))
    # and per bucket
    for lo, hi, label in ((30_000, 10 ** 12, "30,000+"), (5_000, 30_000, "5,000-30,000"), (0, 5_000, "under 5,000")):
        sub = [r for r in rows if lo <= r["p1"] < hi]
        if len(sub) < 3:
            continue
        _, a, b = fit_band(sub, curve)
        vals = [loss_with(r["p1"], curve, a, b, r["truth"]) for r in sub]
        vals = [v for v in vals if v is not None]
        print("  %-14s n=%2d  band %.2f/%.2f  loss %.6f" % (label, len(sub), a, b, sum(vals) / len(vals)))


if __name__ == "__main__":
    main()
