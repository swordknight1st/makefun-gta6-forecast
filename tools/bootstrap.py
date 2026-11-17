"""How much of the band's gain survives a smaller pool?

The band was chosen on 16 comparables, and the contest scores exactly one case. A gain of
0.0035 with n=16 is small enough that its sign can flip on a different draw. This bootstraps:
resample the 16 with replacement 400 times at each pool size, refit the band inside each
resample, and count how often the refitted band's pooled loss is worse than the current
band's on that same resample. It also reports the plain bootstrap of the *difference*
between candidate (0.25, 0.08) and current (0.10, 0.12), which is the number that matters:
how often the candidate loses.

Read-only: prints numbers, writes nothing. Fixed seed, so two runs agree.
"""

import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from band_check import loss  # noqa: E402
from sweep import load  # noqa: E402

CURRENT = (0.10, 0.12)
CANDIDATE = (0.25, 0.08)
GRID = [(s0 / 100.0, s1 / 100.0) for s0 in range(0, 41, 5) for s1 in range(6, 19, 2)]
DRAWS = 400


def pooled(rows, s0, s1):
    vals = [loss(r["p1"], s0, s1, r["truth"]) for r in rows]
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals)


def best_on(rows):
    best = None
    for s0, s1 in GRID:
        m = pooled(rows, s0, s1)
        if best is None or m < best[0] - 1e-12:
            best = (m, s0, s1)
    return best


def main():
    rows = load()
    rng = random.Random(15485863)

    print("bootstrap of the difference candidate(0.25/0.08) - current(0.10/0.12), n=%d, %d draws"
          % (len(rows), DRAWS))
    diffs = []
    for _ in range(DRAWS):
        sample = [rows[rng.randrange(len(rows))] for _ in rows]
        diffs.append(pooled(sample, *CANDIDATE) - pooled(sample, *CURRENT))
    diffs.sort()
    lo = diffs[int(0.025 * DRAWS)]
    hi = diffs[int(0.975 * DRAWS)]
    print("  mean %+0.6f   median %+0.6f   2.5%% %+0.6f   97.5%% %+0.6f"
          % (sum(diffs) / DRAWS, diffs[DRAWS // 2], lo, hi))
    print("  candidate worse than current in %d of %d draws (%.1f%%)"
          % (sum(1 for d in diffs if d > 0), DRAWS, 100.0 * sum(1 for d in diffs if d > 0) / DRAWS))

    print("\nrefit inside each resample: does the fitted band still land wide?")
    picks = {}
    for _ in range(DRAWS):
        sample = [rows[rng.randrange(len(rows))] for _ in rows]
        _, s0, s1 = best_on(sample)
        picks[(s0, s1)] = picks.get((s0, s1), 0) + 1
    for (s0, s1), n in sorted(picks.items(), key=lambda kv: -kv[1])[:8]:
        print("  S0=%.2f S1=%.2f  chosen in %3d of %d (%.0f%%)" % (s0, s1, n, DRAWS, 100.0 * n / DRAWS))


if __name__ == "__main__":
    main()
