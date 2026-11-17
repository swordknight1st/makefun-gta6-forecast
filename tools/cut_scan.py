"""Scan band layouts in process, with the entry's own arithmetic imported, not re-derived.

The subprocess version of this took six thousand launches to finish a tenth of the grid. This
imports `round2`, `forecast_hour` and `band` from the shipped main.py and only substitutes the
bands and cuts, so the numbers are the entry's, computed a hundred times faster.

Two columns decide a scheme: the loss pooled over all 37 comparables, and the loss pooled
over the 10,000+ cohort GTA VI belongs to. Printed: the 15 best by cohort, the 8 best
overall, and how a few hand-picked layouts score.
"""

import importlib.util
import itertools
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from band_check import LEVELS  # noqa: E402
from score_entry import KIT, comparables  # noqa: E402


def load_entry():
    spec = importlib.util.spec_from_file_location("entry", os.path.join(REPO, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ENTRY = load_entry()

BANDS = [(0.00, 0.15), (0.10, 0.14), (0.15, 0.16), (0.20, 0.14), (0.25, 0.10),
         (0.30, 0.12), (0.40, 0.20), (0.40, 0.32), (0.60, 0.40), (0.80, 0.50)]
CUTS = [(0, 1_000), (0, 3_000), (1_000, 10_000), (3_000, 10_000), (1_000, 30_000),
        (3_000, 30_000), (5_000, 30_000), (5_000, 60_000), (10_000, 60_000), (10_000, 100_000)]


def loss_of(p1, band, truth):
    rows = [{"hour": h, "q": ENTRY.forecast_hour(p1, h, band[0], band[1])} for h in range(2, 25)]
    import math
    total, n = 0.0, 0
    for row in rows:
        y = truth.get(row["hour"])
        if y is None or y <= 0:
            continue
        y = max(float(y), 1.0)
        for tau, q in zip(LEVELS, row["q"]):
            d = math.log(y) - math.log(max(float(q), 1.0))
            total += 2 * max(tau * d, (tau - 1) * d)
            n += 1
    return (total / n) if n else None


def scheme_loss(rows, cut1, cut2, a, b, c):
    per = []
    for r in rows:
        if r["p1"] >= cut2:
            band = a
        elif r["p1"] >= cut1:
            band = b
        else:
            band = c
        v = loss_of(r["p1"], band, r["truth"])
        if v is not None:
            per.append((r["p1"], v))
    all37 = sum(v for _, v in per) / len(per)
    coh = [v for p1, v in per if p1 >= 10_000]
    return all37, (sum(coh) / len(coh) if coh else float("nan"))


def main():
    rows = comparables(KIT)
    print("%d comparables, %d at 10,000+" % (len(rows), sum(1 for r in rows if r["p1"] >= 10_000)))
    shipped = scheme_loss(rows, 1_000, 10_000, (0.20, 0.14), (0.40, 0.32), (0.60, 0.40))
    print("shipped (1000/10000, .20/.14 .40/.32 .60/.40): all37 %.6f  cohort %.6f" % shipped)
    house = scheme_loss(rows, 10 ** 9, 10 ** 9, (0.0, 0.15), (0.0, 0.15), (0.0, 0.15))
    print("house baseline band everywhere:                all37 %.6f  cohort %.6f" % house)

    results = []
    for cut1, cut2 in CUTS:
        for a, b, c in itertools.product(BANDS, repeat=3):
            all37, coh = scheme_loss(rows, cut1, cut2, a, b, c)
            results.append((coh, all37, cut1, cut2, a, b, c))

    def show(r):
        coh, all37, cut1, cut2, a, b, c = r
        return ("  cut1=%5d cut2=%6d  big=%.2f/%.2f mid=%.2f/%.2f small=%.2f/%.2f  cohort %.6f  all37 %.6f"
                % (cut1, cut2, a[0], a[1], b[0], b[1], c[0], c[1], coh, all37))

    print("\nbest 15 by the 10,000+ cohort:")
    for r in sorted(results, key=lambda r: r[0])[:15]:
        print(show(r))
    print("\nbest 8 by all 37:")
    for r in sorted(results, key=lambda r: r[1])[:8]:
        print(show(r))


if __name__ == "__main__":
    main()
