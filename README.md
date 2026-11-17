# gta6 forecast: what is here and why

The entry for make.fun's `gta6-twitch-ccu-forecast-01`: forecast Twitch concurrent viewers
in the Grand Theft Auto VI category for hours 2..24 of 2026-11-19, as five quantiles an
hour, from hour 1's print.

## main.py

`q_tau(h) = p1 * exp(z_tau * (S0 + S1 * sqrt(h - 1)))`, rounded half up to 2 decimals,
with `z = (-1.645, -0.674, 0, 0.674, 1.645)`, `S0 = 0.10`, `S1 = 0.12` when hour 1's
print is at least 100,000 viewers, and the house baseline's `S0 = 0`, `S1 = 0.15` below
that. Standard library only, Python 3.13 compatible, reads `MAKEFUN_INPUT_DIR` and writes
`MAKEFUN_OUTPUT_DIR`.

The centre stays flat: hour 1's print for every hour. A cross-game median ratio curve
loses on pinball loss at every pool size, because launch-day shapes differ more between
games than a flat centre's error costs.

## tools/

All three are read-only and standard library only.

- `tools/band_check.py KIT` scores candidate bands on the 38 comparables the practice
  cases ship, i.e. the contest's own loss on launches whose first hour is at least
  100,000 viewers. The tuned pair is the winner of that table:
  `S0=0.10, S1=0.12` 0.257621 against the house baseline's 0.261137 over the same 16
  comparables (1.3% better), with `S0=0.10, S1=0.15` 0.260750 and
  `S0=0.05, S1=0.12` 0.260469 in third.
- `tools/small_check.py KIT` does the same for first hours under 100,000 viewers, the
  fallback's own cohort (21 comparables). There the baseline band pays 1.438994, the
  tuned pair 1.441285, and `S0=0.05, S1=0.14` 1.433877: the cohort lumps three regimes
  together (3,000-viewer indies, 40,000-viewer consoles, 90,000-viewer shooters), so no
  single band wins it, and the fallback stays the house baseline's: with the fallback in
  place main.py is never worse on this cohort than the block the house graded at 0.387.
- `tools/check_out.py OUT_DIR [--golden DIR]` holds each .out to the case contract
  (one key `hours`, 23 rows, hours 2..24 once, five finite numbers above 0 and at most
  1e9, non-decreasing, at most 65,536 bytes) and, with `--golden`, compares two runs
  byte for byte. Exit status 1 on any failure.

## Reproducing a local run

```
export MAKEFUN_INPUT_DIR=<kit>/input
export MAKEFUN_OUTPUT_DIR=out
python3 -P -s main.py
python3 tools/check_out.py out
```

Four practice files in, four .out files out, 23 rows each. The practice set ships no
sealed answers in `input/`, so `tools/band_check.py` and `tools/small_check.py` score the
comparables instead: they are this machine's only ground truth, and the same rule the
competition grades by.

## Known limits

- The 1.3% gain is small by construction: one band, chosen on 16 comparables. It is an
  honest win over the house baseline on the cohort GTA VI belongs to, not a reshaping.
- The final case has no history at all beyond hour 1, so nothing here consumes `history`,
  `streams` or `categories_hourly`; a model that reads them cannot be validated on a
  practice case that nulls them.
- Rounding follows the starter's `round2` (half up on the scaled value), so every .out
  stays in the starter's number format.
