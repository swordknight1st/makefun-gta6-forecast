"""Leave-one-out over the layout, two stage: shortlist on all the fits, then validate.

Refitting 10,000 layouts inside 37 folds is 370,000 evaluations; the earlier attempt was killed
for time and then crashed on a tuple bug. This does it in two stages:

  1. Score every layout once on all 37 comparables, keep the best SHORTLIST.
  2. For each fold, fit *among the shortlist* on the other 36 and score the held-out one.

That is an honest selection: the shortlist never sees the held-out case, and the comparison
against the fixed layout and the house baseline is on exactly the same held-out rows.

Read-only: prints a table.
"""

import itertools
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from cut_scan import BANDS, CUTS, loss_of, scheme_loss  # noqa: E402
from score_entry import KIT, comparables  # noqa: E402

SHIP = (5_000, 30_000, (0.25, 0.10), (0.40, 0.20), (0.80, 0.50))
HOUSE = (0.00, 0.15)
SHORTLIST = 40


def band_of(p1, layout):
    cut1, cut2, a, b, c = layout
    if p1 >= cut2:
        return a
    if p1 >= cut1:
        return b
    return c


def main():
    rows = comparables(KIT)
    layouts = [(c1, c2, a, b, c) for (c1, c2) in CUTS for a, b, c in itertools.product(BANDS, repeat=3)]
    print("%d comparables, %d layouts, shortlist %d" % (len(rows), len(layouts), SHORTLIST))
    scored = sorted((scheme_loss(rows, *L)[0], L) for L in layouts)
    short = [L for _, L in scored[:SHORTLIST]]
    print("shortlist built on all 37; its best all-37 loss is %.6f" % scored[0][0])

    print("%-38s %8s %-30s %9s %9s %9s"
          % ("held out", "p1", "fold pick", "fold", "shipped", "house"))
    tot = {"fold": 0.0, "ship": 0.0, "house": 0.0}
    picks = {}
    for i, held in enumerate(rows):
        rest = rows[:i] + rows[i + 1:]
        best = min((scheme_loss(rest, *L)[0], L) for L in short)
        L = best[1]
        picks[L] = picks.get(L, 0) + 1
        f = loss_of(held["p1"], band_of(held["p1"], L), held["truth"])
        s = loss_of(held["p1"], band_of(held["p1"], SHIP), held["truth"])
        h = loss_of(held["p1"], HOUSE, held["truth"])
        tot["fold"] += f
        tot["ship"] += s
        tot["house"] += h
        print("%-38s %8.0f %-30s %9.6f %9.6f %9.6f"
              % (held["name"][:38], held["p1"],
                 "%d/%d %.2f/%.2f %.2f/%.2f %.2f/%.2f" % (L[0], L[1], L[2][0], L[2][1],
                                                         L[3][0], L[3][1], L[4][0], L[4][1]),
                 f, s, h))
    n = len(rows)
    print("\nheld-out means:  shortlist-fitted %.6f   shipped %.6f   house %.6f"
          % (tot["fold"] / n, tot["ship"] / n, tot["house"] / n))
    print("\nmost frequent fold picks:")
    for L, v in sorted(picks.items(), key=lambda kv: -kv[1])[:6]:
        print("  cut %5d/%6d  %.2f/%.2f  %.2f/%.2f  %.2f/%.2f   x%d"
              % (L[0], L[1], L[2][0], L[2][1], L[3][0], L[3][1], L[4][0], L[4][1], v))


if __name__ == "__main__":
    main()
