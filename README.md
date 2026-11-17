# gta6 forecast: what is here and why

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/swordknight1st/makefun-gta6-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/swordknight1st/makefun-gta6-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

The entry for make.fun's [GTA VI launch-day Twitch viewer bounty](https://make.fun/bounty/gta6-twitch-ccu-forecast-01):
forecast Twitch concurrent viewers in the Grand Theft Auto VI category for hours 2..24 of
2026-11-19, as five quantiles an hour, from hour 1's print.

## main.py

`q_tau(h) = p1 * exp(z_tau * (S0 + S1 * sqrt(h - 1)))`, rounded half up to 2 decimals,
with `z = (-1.645, -0.674, 0, 0.674, 1.645)` and a band that depends on how big the launch
is: `0.25/0.10` at 30,000 viewers and up, `0.40/0.20` from 5,000 to 30,000, `0.80/0.50`
below that. Standard library only, Python 3.13 compatible, reads `MAKEFUN_INPUT_DIR` and
writes `MAKEFUN_OUTPUT_DIR`.

The centre stays flat: hour 1's print for every hour. A cross-game median ratio curve
loses on pinball loss at every pool size, because launch-day shapes differ more between
games than a flat centre's error costs.

Why three bands: how wide helps depends on how much hour 1 already tells you. Over the
comparables the practice cases ship, the hour-24 / hour-1 ratio sits in 0.5–3 above 10,000
viewers, reaches 5–8 between 1,000 and 10,000, and reaches 65–1,088 below 1,000 — the last
of those is pre-launch noise, not a launch, and only a very wide band says so honestly.
Scored through the entry's own .out files over all 37 comparables: **0.714627** against the
house baseline's 0.929650; over the 28 at 10,000+ viewers, 0.332639 against 0.350833.

The cuts and bands were chosen by a leave-one-out over 10,000 layouts, and all 37 folds
picked this layout (32 exactly, 5 with the upper cut at 60,000), which is why the fixed
layout ships rather than per-fold refits — refitting scored worse out of sample (0.723024).

## Run it

```
export MAKEFUN_INPUT_DIR=<kit>/input
export MAKEFUN_OUTPUT_DIR=out
python3 -P -s main.py
python3 tools/check_out.py out
```

Four practice files in, four .out files out, 23 rows each.

## tools/

Read-only, standard library only, and every one of them takes the kit's path as an argument
or finds it beside the repository.

- `tools/score_entry.py [--min-viewers N]` is the one that matters: it writes one .in per
  comparable, runs the real `main.py` as the grader does (`python -P -s`), and scores the
  .out files it wrote. Every other tool computes a band formula; this one scores the entry.
  `--min-viewers 10000` restricts it to the cohort GTA VI belongs to.
- `tools/check_out.py OUT_DIR [--golden DIR]` holds each .out to the case contract
  (one key `hours`, 23 rows, hours 2..24 once, five finite numbers above 0 and at most
  1e9, non-decreasing, at most 65,536 bytes) and, with `--golden`, compares two runs
  byte for byte. Exit status 1 on any failure.
- `tools/band_check.py`, `tools/small_check.py`, `tools/small_loo.py`,
  `tools/small_shape.py` fit and re-check single bands per cohort, including the
  leave-one-out pass that showed the 10,000+ optimum is a plateau rather than a point.
- `tools/per_case.py`, `tools/loo.py`, `tools/s0_loo.py`, `tools/bootstrap.py`,
  `tools/plateau.py` are the checks behind "wider is real, the exact pair is not": per-case
  wins, leave-one-out, a 400-draw bootstrap of the difference (2.5% – 97.5% wholly below
  zero), and a plateau-centre rule.
- `tools/buckets.py`, `tools/cut_scan.py`, `tools/layout_loo.py` choose the cuts and the
  three bands, in process and through the entry's own arithmetic.
- `tools/losers.py` prints every comparable sorted by how much the shipped band costs
  against the house baseline, so a regression is one command away.

## Known limits

- The gain is a mean, not a per-case promise: it beats the house baseline on 26 of 37
  comparables overall, and loses by up to 0.016 on the ones whose audience barely moves all
  day (Diablo IV, the Call of Duty launches, Final Fantasy VII Rebirth), where any band is
  too wide. It wins big on the ones that multiply during the day.
- The small bands are fitted on 3 and 6 comparables. They help a lot on the comparables that
  are there (Silksong, Black Myth, Helldivers 2 all end 60–1,088x their hour 1) and should
  not be read as more than that.
- The final case has no history at all beyond hour 1, so nothing here consumes `history`,
  `streams` or `categories_hourly`; a model that reads them cannot be validated on a
  practice case that nulls them.
- Rounding follows the starter's `round2` (half up on the scaled value), so every .out
  stays in the starter's number format.
- Hours 2..24 are written whatever the case's forecast list holds: the contract wants 23
  rows, and a .out short of one is scored as if every quantile were hour 1's print.
