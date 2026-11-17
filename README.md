# gta6 forecast: what is here and why

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/swordknight1st/makefun-gta6-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/swordknight1st/makefun-gta6-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

The entry for make.fun's [GTA VI launch-day Twitch viewer bounty](https://make.fun/bounty/gta6-twitch-ccu-forecast-01):
forecast Twitch concurrent viewers in the Grand Theft Auto VI category for hours 2..24 of
2026-11-19, as five quantiles an hour, from hour 1's print.

## main.py

`q_tau(h) = p1 * c * exp(z_tau * (S0 + S1 * sqrt(h - 1)))`, rounded half up to 2 decimals,
with `z = (-1.645, -0.674, 0, 0.674, 1.645)`, a band and a centre factor that depend on how
big the launch is: `c=1.00, band 0.25/0.10` at 30,000 viewers and up, `c=1.50, 0.40/0.20`
from 5,000 to 30,000, `c=2.00, 0.80/0.50` below that. Standard library only, Python 3.13
compatible, reads `MAKEFUN_INPUT_DIR` and writes `MAKEFUN_OUTPUT_DIR`.

Why the band widens: how much a band helps depends on how much hour 1 already tells you. Over
the comparables the practice cases ship, the hour-24 / hour-1 ratio sits in 0.5–8 above
30,000 viewers, reaches 2.4–7 between 5,000 and 30,000, and reaches 65–1,088 below 5,000 —
the last of those is pre-launch noise, not a launch, and only a very wide band says so.

Why the centre moves: the comparables' median lands at 0.72–0.88 of hour 1 between hours 2
and 12 and 1.6–2.0 by prime time, and the smaller the launch the bigger the day's climb,
because its hour 1 is mostly warm-up. One factor per bucket survives leave-one-out; the full
23-hour median ratio curve does not — it cuts in-sample log error from 1.1421 to 1.0544 and
still loses out of sample (0.790958 against 0.714627 for a flat centre with the same bands),
which is why this ships one number per bucket and not a curve.

Scored through the entry's own .out files over all 37 comparables: **0.639770** against the
house baseline's 0.844342. Over the 23 at 30,000+ viewers, 0.291032 against 0.295274.

The 30,000+ bucket keeps `c=1.00` on purpose: its fitted factor is 0.95 in sample, but
refitting per fold moves it between 0.90 and 0.95 and the held-out loss gets worse, so the
evidence there is nil. Bands past this point are noise too: refitting them per fold on the
100,000+ and 30,000+ cohorts gives held-out losses at or above the shipped layout's
(0.254651 and 0.291126 against 0.256925 and 0.291032).

The cuts and bands were chosen by a leave-one-out over 10,000 layouts, and all 37 folds
picked this pair of cuts and these three bands (32 exactly, 5 with the upper cut at 60,000),
which is why the fixed layout ships rather than per-fold refits — refitting scored worse out
of sample (0.723024).

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
- `tools/shape.py`, `tools/shape_fit.py` measure the real hourly shape and show the full
  ratio curve overfits; `tools/centre_fit.py`, `tools/centre_sweep.py`,
  `tools/bucket_factor.py`, `tools/centre_entry.py` choose the one centre factor per bucket
  and check it leave-one-out.
- `tools/losers.py` prints every comparable sorted by how much the shipped band costs
  against the house baseline, so a regression is one command away.

## Known limits

- The gain is a mean, not a per-case promise: it beats the house baseline on 24 of 37
  comparables overall, and loses by up to 0.02 on the ones whose audience barely moves all
  day (Diablo IV, the Call of Duty launches, Final Fantasy VII Rebirth), where any band is
  too wide and any centre factor is wrong. It wins big on the ones that multiply during the
  day.
- The centre factor is evidence only in the middle and small buckets. For a launch above
  30,000 viewers — which is where GTA VI is expected — the factor is 1.00 and the model is
  the band alone, because that bucket's fitted factor does not survive leave-one-out.
- The small bucket's 2.00 is a bounded extrapolation, not a fit: all eight of its
  comparables are pre-launch shapes, and the factor its grid reaches (8.0) is not credible
  for a launch of any real size.
- The final case has no history at all beyond hour 1, so nothing here consumes `history`,
  `streams` or `categories_hourly`; a model that reads them cannot be validated on a
  practice case that nulls them.
- Rounding follows the starter's `round2` (half up on the scaled value), so every .out
  stays in the starter's number format.
- Hours 2..24 are written whatever the case's forecast list holds: the contract wants 23
  rows, and a .out short of one is scored as if every quantile were hour 1's print.
