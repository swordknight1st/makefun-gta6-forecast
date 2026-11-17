"""Does a bigger launch decay instead of climbing? Test the trend before trusting it.

`bimodal.py` shows weekday explains nothing, but size looks monotone: the six comparables above
320,000 viewers have a median hour-24 / hour-1 of 0.87 (they decay from a huge hour-1 spike),
while the ten between 114,000 and 166,000 sit at 1.38 (they build through the day). GTA VI is
expected above all of them, so this matters: it would put the centre factor below 1.0 where
main.py currently ships 1.00.

Two tests, because n=6 is small:

  1. rank correlation between log(p1) and log(h24/h1) over the 100,000+ cohort, with the
     permutation p-value, so the trend has a number rather than an eyeball;
  2. leave-one-out: fit c on the big sub-cohort per fold, score the held-out big one, and
     compare with c=1.00 on the same row.

Read-only: prints numbers.
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


def spearman(xs, ys):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = ranks(xs), ranks(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    dy = math.sqrt(sum((b - my) ** 2 for b in ry))
    return num / (dx * dy) if dx and dy else 0.0


def main():
    rows = [r for r in comparables(KIT) if r["p1"] >= 100_000]
    xs = [math.log(r["p1"]) for r in rows]
    ys = [math.log(max((r["truth"].get(24) or 1) / r["p1"], 1e-9)) for r in rows]
    rho = spearman(xs, ys)
    # permutation p-value: how often a random relabelling is at least this extreme
    extreme = 0
    total = 0
    for perm in itertools.permutations(range(len(ys)), len(ys)) if len(ys) <= 7 else ():
        total += 1
        if abs(spearman(xs, [ys[i] for i in perm])) >= abs(rho):
            extreme += 1
    if total == 0:
        # 16! is too many to enumerate: sample instead, deterministically
        import random
        rng = random.Random(20261117)
        total = 20000
        for _ in range(total):
            perm = ys[:]
            rng.shuffle(perm)
            if abs(spearman(xs, perm)) >= abs(rho):
                extreme += 1
    print("rank correlation of log(p1) with log(h24/h1) over %d at 100,000+: rho=%.3f" % (len(rows), rho))
    print("  permutation p=%.4f over %d relabellings" % (extreme / total, total))

    big = [r for r in rows if r["p1"] >= 320_000]
    print("\nbig sub-cohort (320,000+, n=%d):" % len(big))
    print("  p1 and h24/h1: " + ", ".join("%.0f:%.2f" % (r["p1"], (r["truth"].get(24) or 0) / r["p1"]) for r in big))
    fits = []
    held = {c: 0.0 for c in (1.00,)}
    picks = []
    for i, h in enumerate(big):
        rest = big[:i] + big[i + 1:]
        best = min((sum(loss(r["p1"], c, r["truth"]) for r in rest) / len(rest), c) for c in CS)
        picks.append(best[1])
    print("  leave-one-out picks: " + ", ".join("%.2f" % p for p in picks))
    for c in (0.80, 0.85, 0.90, 0.95, 1.00):
        v = sum(loss(r["p1"], c, r["truth"]) for r in big) / len(big)
        print("  c=%.2f -> full-sample %.6f" % (c, v))
    # held-out with the fold's own pick
    tot = 0.0
    tot1 = 0.0
    for i, h in enumerate(big):
        rest = big[:i] + big[i + 1:]
        best = min((sum(loss(r["p1"], c, r["truth"]) for r in rest) / len(rest), c) for c in CS)
        tot += loss(h["p1"], best[1], h["truth"])
        tot1 += loss(h["p1"], 1.00, h["truth"])
    print("  held-out mean: fold-fitted %.6f   c=1.00 %.6f" % (tot / len(big), tot1 / len(big)))


if __name__ == "__main__":
    main()
