"""Is the 100,000+ cohort two shapes or one?

The 16 comparables above 100,000 viewers disagree a lot about the day: some end near half of
hour 1 (ELDEN RING 0.72, Cyberpunk 0.55), one ends at twice (Monster Hunter Wilds 2.09). Before
adding a second regime for that cohort, this checks whether the disagreement has a visible
cause that would generalise -- the weekday of the release day, whether the day_start is the
real unlock, platforms -- or whether it is just spread.

Nothing is fitted here on purpose: a split fitted on 16 points and then scored on the same 16
points is how the earlier full ratio curve looked good and lost out of sample.

Read-only: prints a table.
"""

import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from score_entry import KIT, comparables  # noqa: E402

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def weekday_of(r):
    try:
        d = datetime.datetime.strptime(r["day_start"][:10], "%Y-%m-%d")
    except Exception:
        return None
    return WEEKDAYS[d.weekday()]


def main():
    rows = [r for r in comparables(KIT) if r["p1"] >= 100_000]
    rows.sort(key=lambda r: -r["p1"])
    print("%-40s %9s %-4s %6s %6s %6s %6s" % ("comparable", "p1", "day", "h4/h1", "h12/h1", "h19/h1", "h24/h1"))
    for r in rows:
        t = r["truth"]
        f = lambda h: (t.get(h) or 0) / r["p1"]
        print("%-40s %9.0f %-4s %6.2f %6.2f %6.2f %6.2f"
              % (r["name"][:40], r["p1"], weekday_of(r) or "?", f(4), f(12), f(19), f(24)))

    print("\nby weekday of the release day:")
    groups = {}
    for r in rows:
        groups.setdefault(weekday_of(r), []).append(r)
    for day, group in sorted(groups.items(), key=lambda kv: str(kv[0])):
        h24 = sorted(((r["truth"].get(24) or 0) / r["p1"]) for r in group)
        print("  %-4s n=%2d  h24/h1: %s" % (day, len(group), ", ".join("%.2f" % x for x in h24)))

    print("\nby size within the cohort:")
    for lo, hi in ((100_000, 200_000), (200_000, 400_000), (400_000, 10 ** 12)):
        group = [r for r in rows if lo <= r["p1"] < hi]
        if not group:
            continue
        h24 = sorted(((r["truth"].get(24) or 0) / r["p1"]) for r in group)
        h12 = sorted(((r["truth"].get(12) or 0) / r["p1"]) for r in group)
        print("  %7d-%-7s n=%2d  h12/h1 %s | h24/h1 %s"
              % (lo, hi if hi < 10 ** 12 else "+", len(group),
                 " ".join("%.2f" % x for x in h12), " ".join("%.2f" % x for x in h24)))


if __name__ == "__main__":
    main()
