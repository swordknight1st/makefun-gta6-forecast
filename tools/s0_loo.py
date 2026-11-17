"""Hold S1 at its minimum and let leave-one-out choose S0 (refit per fold, for real).

`sweep.py` puts the pooled minimum of S1 at 0.08. This fixes S1 and asks whether S0 = 0.25
is a real held-out choice: for every held-out comparable the fold refits S0 on the other 15,
then scores the held-out one. A per-fold pick that is always the same value, and a held-out
curve that bottoms out at the same S0 as the pooled curve, is a real choice; a per-fold pick
that wanders is noise.

The held-out loss is reported for the fold's own pick and, beside it, for two fixed
candidates, so the comparison is one number per row and not a column of duplicates.

Read-only: prints a table, writes nothing.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from band_check import loss  # noqa: E402
from sweep import load  # noqa: E402

S1 = 0.08
S0S = [x / 100.0 for x in range(0, 46, 5)]
CURRENT = (0.10, 0.12)
CANDIDATE = (0.25, 0.08)
HOUSE = (0.00, 0.15)


def fold_pick(fit_rows):
    """S0 that minimises the pooled loss on the fitting rows, at this S1."""
    best = None
    for s0 in S0S:
        m = sum(loss(r["p1"], s0, S1, r["truth"]) for r in fit_rows) / len(fit_rows)
        if best is None or m < best[0] - 1e-12:
            best = (m, s0)
    return best[1]


def main():
    rows = load()
    print("leave-one-out over S0 at S1=%.2f, %d comparables" % (S1, len(rows)))
    print("%-42s %8s %6s %9s %9s %9s %9s"
          % ("held out", "p1", "pick", "loo pick", "candidate", "current", "house"))
    loo = cand = cur = hou = 0.0
    for i, held in enumerate(rows):
        rest = rows[:i] + rows[i + 1:]
        s0 = fold_pick(rest)
        a = loss(held["p1"], s0, S1, held["truth"])
        b = loss(held["p1"], *CANDIDATE, held["truth"])
        c = loss(held["p1"], *CURRENT, held["truth"])
        d = loss(held["p1"], *HOUSE, held["truth"])
        loo += a
        cand += b
        cur += c
        hou += d
        print("%-42s %8.0f %6.2f %9.6f %9.6f %9.6f %9.6f"
              % (held["name"][:42], held["p1"], s0, a, b, c, d))
    n = len(rows)
    print("\nmean held-out loss  loo-pick %.6f   candidate(%.2f/%.2f) %.6f   current %.6f   house %.6f"
          % (loo / n, CANDIDATE[0], CANDIDATE[1], cand / n, cur / n, hou / n))

    print("\npooled, all %d:" % n)
    for name, s0, s1 in (("house", *HOUSE), ("current", *CURRENT),
                         ("candidate 0.20/0.08", 0.20, S1), ("candidate 0.25/0.08", 0.25, S1),
                         ("candidate 0.30/0.08", 0.30, S1)):
        m = sum(loss(r["p1"], s0, s1, r["truth"]) for r in rows) / n
        print("  %-22s %.6f" % (name, m))


if __name__ == "__main__":
    main()
