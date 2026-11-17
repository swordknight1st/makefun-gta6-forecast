"""gta6-twitch-ccu-forecast-01 entry (MIT, see LICENSE): calibrated persistence.

Forecast: every hour of release day draws p1 viewers, the first hour's print, with a
log-normal band whose width grows like a random walk's:

    q_tau(h) = p1 * exp(z_tau * (S0 + S1 * sqrt(h - 1)))

z_tau is the standard normal's quantile at 0.05 / 0.25 / 0.50 / 0.75 / 0.95
(-1.645, -0.674, 0, 0.674, 1.645).

The shape is deliberately flat. A leave-one-out cross-validation over the 38 launch
comparables the case ships (37 with a usable first hour) showed that replacing the
flat centre with a cross-game median ratio curve is *worse* on pinball loss at every
pool size: launch-day shapes differ too much between games (rolling midnight unlocks,
premium early access, free-to-play), and the resulting centre error costs more than the
flat centre's. What does help is the band. On the 16 comparables whose first hour is at
least 100,000 viewers -- the cohort Grand Theft Auto VI, the largest launch in the set,
belongs to -- the house baseline's S0=0, S1=0.15 scores a mean pinball loss of 0.261137,
and S0=0.10, S1=0.12 scores 0.257621. That 1.3% is the whole gain, and it is the only
change made here.

Below 100,000 viewers the tuned band is not what the comparison supports, so a small
first hour falls back to the house baseline's S0=0, S1=0.15.

Reads every <id>.in in the input directory and writes <id>.out beside it.
"""

import json
import math
import os
import sys

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.645, -0.674, 0.0, 0.674, 1.645]

# Tuned on the 16 comparables with a first hour of at least 100,000 viewers.
S0, S1 = 0.10, 0.12
# The house baseline's band, used when the first hour is small.
B1 = 0.15
SMALL = 100_000

CAP = 1_000_000_000


def band(p1):
    """(S0, S1) for this case: the tuned pair for a large launch, the baseline's otherwise."""
    return (S0, S1) if p1 >= SMALL else (0.0, B1)


def forecast_hour(p1, h, s0, s1):
    """The five quantiles of hour h, at the levels in LEVELS order."""
    sigma = s0 + s1 * math.sqrt(h - 1)
    row = []
    for z in Z:
        q = p1 * math.exp(z * sigma)
        if q < 1.0:
            q = 1.0
        elif q > CAP:
            q = CAP
        row.append(q)
    # Keep the row non-decreasing after the clamps.
    for i in range(1, 5):
        if row[i] < row[i - 1]:
            row[i] = row[i - 1]
    return row


def first_hour(case):
    """Hour 1's print from the case's `known` rows; a print below 1 counts as 1."""
    known = case.get("known") or []
    p1 = None
    for row in known:
        if row.get("hour") == 1 and row.get("viewers") is not None:
            p1 = float(row["viewers"])
            break
    if p1 is None and known:
        for row in known:
            if row.get("viewers") is not None and (p1 is None or row["viewers"] < p1):
                p1 = float(row["viewers"])
    if p1 is None:
        p1 = 1.0
    return max(p1, 1.0)


def main():
    in_dir = INPUT_DIR
    out_dir = OUTPUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    names = sorted(n for n in os.listdir(in_dir) if n.endswith(".in"))
    if not names:
        sys.exit("no .in file in " + in_dir)
    for name in names:
        case = json.load(open(os.path.join(in_dir, name), encoding="utf-8"))
        p1 = first_hour(case)
        s0, s1 = band(p1)
        hours = []
        wanted = [r.get("hour") for r in (case.get("forecast") or []) if r.get("hour")]
        if not wanted:
            wanted = list(range(2, 25))
        for h in sorted(set(wanted)):
            if 2 <= h <= 24:
                hours.append({"hour": h, "q": forecast_hour(p1, h, s0, s1)})
        out = {"hours": hours}
        path = os.path.join(out_dir, name[:-3] + ".out")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, separators=(",", ":"))
        print("%s: p1=%.0f  s0=%.2f s1=%.2f  %d hours -> %s" % (
            name, p1, s0, s1, len(hours), path))


if __name__ == "__main__":
    main()
