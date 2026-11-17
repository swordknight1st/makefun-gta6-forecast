"""gta6-twitch-ccu-forecast-01 entry (MIT, see LICENSE): calibrated persistence.

Forecast: every hour of release day draws p1 viewers, the first hour's print, with a
log-normal band whose width grows like a random walk's:

    q_tau(h) = p1 * exp(z_tau * (S0 + S1 * sqrt(h - 1)))

z_tau is the standard normal's quantile at 0.05 / 0.25 / 0.50 / 0.75 / 0.95
(-1.645, -0.674, 0, 0.674, 1.645).

The shape is deliberately flat. A leave-one-out pass over the comparables the practice
cases ship showed that replacing the flat centre with a cross-game median ratio curve is
worse on pinball loss at every pool size: launch-day shapes differ too much between games
(rolling midnight unlocks, premium early access, free-to-play), and the centre error costs
more than a flat centre's does. What does help is the band. Over the comparables whose
first hour is at least 100,000 viewers -- the cohort Grand Theft Auto VI, the largest
launch in the set, belongs to -- the house baseline's S0=0, S1=0.15 gives a mean pinball
loss of 0.261137, and S0=0.10, S1=0.12 gives 0.257621: a 1.3% gain, and the only change
made here.

Below 100,000 viewers that tuned band is not what the comparison supports, so a small
first hour falls back to the house baseline's S0=0, S1=0.15.

Reads every <id>.in in the input directory and writes <id>.out to the output directory,
both named by MAKEFUN_INPUT_DIR / MAKEFUN_OUTPUT_DIR (the grader's /input and /output).
Standard library only: the grader runs python3 -P -s, in a 3.13 container, with no pip.
"""

import json
import math
import os
import sys

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

# The levels each row lists, in the order the row lists them.
LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
# The standard normal's quantile at each level.
Z = [-1.645, -0.674, 0.0, 0.674, 1.645]

# Tuned on the comparables whose first hour is at least 100,000 viewers.
S0, S1 = 0.10, 0.12
# The house baseline's band, kept for first hours below the cohort's floor.
B1 = 0.15
SMALL = 100_000

# The contract's ceiling on any quantile (viewers).
CAP = 1_000_000_000


def round2(x):
    """x rounded to 2 decimals, half up, as the starter's round2 does.

    A whole number comes back as an int, so json.dumps writes 1240 and not 1240.0,
    which keeps every .out byte-identical to the starter's shape.
    """
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if value.is_integer() else value


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
        row.append(round2(q))
    # The clamps can only move a tail inward, but keep the row non-decreasing anyway:
    # the contract rejects a row that steps down, and one rejected row voids the case.
    for i in range(1, len(row)):
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
    if p1 is None:
        # No hour-1 row: the checkpoint's lowest print is the best stand-in for it,
        # since every later hour only drops from the launch's first one.
        for row in known:
            if row.get("viewers") is not None and (p1 is None or row["viewers"] < p1):
                p1 = float(row["viewers"])
    if p1 is None:
        p1 = 1.0
    return max(p1, 1.0)


def forecast_case(case):
    """The whole .out body for one case: 23 rows, hours 2..24, five quantiles each."""
    levels = case.get("levels")
    if levels is not None and levels != LEVELS:
        raise ValueError("this case asks for levels %r, not %r" % (levels, LEVELS))
    p1 = first_hour(case)
    s0, s1 = band(p1)
    wanted = [row.get("hour") for row in (case.get("forecast") or []) if row.get("hour")]
    if not wanted:
        wanted = list(range(2, 25))
    hours = [{"hour": h, "q": forecast_hour(p1, h, s0, s1)} for h in sorted(set(wanted)) if 2 <= h <= 24]
    return {"hours": hours}


def main():
    in_dir = INPUT_DIR
    out_dir = OUTPUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    names = sorted(n for n in os.listdir(in_dir) if n.endswith(".in"))
    if not names:
        sys.exit("no .in file in " + in_dir)
    for name in names:
        with open(os.path.join(in_dir, name), encoding="utf-8") as f:
            case = json.load(f)
        body = forecast_case(case)
        path = os.path.join(out_dir, name[:-3] + ".out")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(body, f, separators=(",", ":"))
        print("%s: %d rows -> %s" % (name, len(body["hours"]), path))


if __name__ == "__main__":
    main()
