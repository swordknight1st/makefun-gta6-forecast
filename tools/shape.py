"""What the comparables' hour-by-hour shape actually looks like, against a flat centre.

The entry's centre is hour 1's print for every hour. That is a strong claim: a launch usually
decays after the first hour and partly recovers at prime time. This measures the truth:

  - the median of y_h / y_1 across comparables, hour by hour (the shape a ratio curve would
    capture), and its spread (how much comparables disagree);
  - the same restricted to the 10,000+ cohort GTA VI belongs to;
  - what a log-ratio curve fitted on the group would cost against the flat centre, by
    leave-one-out.

Read-only: prints tables, writes nothing.
"""

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from band_check import LEVELS  # noqa: F401  (kept for parity)
from score_entry import KIT, comparables  # noqa: E402


def log_ratio(r, h):
    y = r["truth"].get(h)
    if y is None or y <= 0:
        return None
    return math.log(max(float(y), 1.0)) - math.log(r["p1"])


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0


def main():
    rows = comparables(KIT)
    for label, group in (("all 37", rows), ("10,000+", [r for r in rows if r["p1"] >= 10_000])):
        print("\n%s (n=%d): y_h / y_1, median and inter-quartile spread" % (label, len(group)))
        print("  %-5s %8s %9s %9s %9s %9s" % ("hour", "median", "q25", "q75", "IQR", "vs flat"))
        for h in range(1, 25):
            vals = [log_ratio(r, h) for r in group]
            vals = [v for v in vals if v is not None]
            if not vals:
                continue
            vals.sort()
            m = median(vals)
            q25 = vals[int(0.25 * (len(vals) - 1))]
            q75 = vals[int(0.75 * (len(vals) - 1))]
            print("  %-5d %8.4f %9.4f %9.4f %9.4f %9.4f"
                  % (h, math.exp(m), math.exp(q25), math.exp(q75), q75 - q25, m))

    # leave-one-out: a per-hour median ratio fitted on the others, vs the flat centre
    print("\nleave-one-out: per-hour median ratio curve vs flat centre, on log error")
    for label, lo in (("all 37", 0), ("10,000+", 10_000)):
        group = [r for r in rows if r["p1"] >= lo]
        flat = 0.0
        curve = 0.0
        n = 0
        for i, held in enumerate(group):
            rest = group[:i] + group[i + 1:]
            for h in range(2, 25):
                y = held["truth"].get(h)
                if y is None or y <= 0:
                    continue
                y = max(float(y), 1.0)
                lr = [log_ratio(r, h) for r in rest]
                lr = [v for v in lr if v is not None]
                if not lr:
                    continue
                pred = math.log(held["p1"]) + median(lr)
                flat += abs(math.log(y) - math.log(held["p1"]))
                curve += abs(math.log(y) - pred)
                n += 1
        print("  %-8s flat %.4f   median-ratio curve %.4f   (%d hours)" % (label, flat / n, curve / n, n))


if __name__ == "__main__":
    main()
