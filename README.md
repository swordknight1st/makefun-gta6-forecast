# gta6 forecast: what is here and why

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/swordknight1st/makefun-gta6-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/swordknight1st/makefun-gta6-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

The entry for make.fun's [GTA VI launch-day Twitch viewer bounty](https://make.fun/bounty/gta6-twitch-ccu-forecast-01):
forecast Twitch concurrent viewers in the Grand Theft Auto VI category for hours 2..24 of
2026-11-19, as five quantiles an hour, from hour 1's print.

## main.py

`q_tau(h) = p1 * c * exp(z_tau * (S0 + S1 * sqrt(h - 1)))`, rounded half up to 2 decimals,
with `z = (-1.645, -0.674, 0, 0.674, 1.645)`, and a band plus a centre factor that depend on
how big the launch is:

| first hour | centre `c` | band `S0/S1` |
|---|---|---|
| 200,000 + | 0.75 | 0.25 / 0.10 |
| 30,000 – 200,000 | 1.00 | 0.25 / 0.10 |
| 5,000 – 30,000 | 1.50 | 0.40 / 0.20 |
| under 5,000 | 2.00 | 0.80 / 0.50 |

Standard library only, Python 3.13 compatible, reads `MAKEFUN_INPUT_DIR` and writes
`MAKEFUN_OUTPUT_DIR`.

Why the band widens: how much a band helps depends on how much hour 1 already tells you. Over
the comparables the practice cases ship, the hour-24 / hour-1 ratio sits in 0.5–8 above
30,000 viewers, reaches 2.4–7 between 5,000 and 30,000, and reaches 65–1,088 below 5,000 —
the last of those is pre-launch noise, not a launch, and only a very wide band says so.

Why the centre moves, and in which direction: a launch does not hold its hour-1 audience all
day, and bigger launches lose it rather than gain. Above 200,000 viewers the comparables fall
to a median 0.52 of hour 1 by hour 12 and recover only to 0.87 by hour 24 — the biggest
launches put everyone in front of the stream at the unlock and then lose them to the game.
Below 5,000 the opposite happens, because hour 1 there is mostly pre-launch warm-up. The trend
is measured, not assumed: over the 16 comparables above 100,000 viewers the rank correlation
of log(viewers) with log(hour 24 / hour 1) is **−0.638**, permutation **p = 0.0094**.

Scored through the entry's own .out files over all 37 comparables: **0.633590** against the
house baseline's 0.929650. Over the 6 at 200,000+ viewers — the cohort GTA VI belongs to —
**0.184294** against 0.225488.

Why one factor per bucket and not a curve: a full 23-hour median ratio curve cuts in-sample
log error from 1.1421 to 1.0544 and still loses out of sample (0.790958 against 0.714627 for
one factor per bucket). The curve fits noise that one number does not.

Nothing here is trusted on in-sample numbers alone. The 200,000 factor is 0.75 by 4 of 6
leave-one-out folds, and the cut is not sharp: boundaries anywhere from 150,000 to 500,000 all
fit 0.75–0.80. The 30,000–200,000 bucket keeps `c=1.00` because 12 of 18 folds pick it, and
the under-5,000 bucket ships 2.00 rather than the 8.0 its grid reaches, since all eight of
those comparables are pre-launch shapes.

The cuts and bands were chosen by a leave-one-out over 10,000 layouts, and all 37 folds
picked that pair of cuts and those three bands (32 exactly, 5 with the upper cut at 60,000),
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
- `tools/bimodal.py`, `tools/size_trend.py`, `tools/fourth_bucket.py`,
  `tools/cut_stability.py` are the check on the 200,000+ bucket: weekday explains nothing,
  size does (rank correlation with a permutation p-value), the factor survives leave-one-out
  inside the bucket, and the cut is a plateau from 150,000 to 500,000 rather than a spike.
- `tools/losers.py` prints every comparable sorted by how much the shipped band costs
  against the house baseline, so a regression is one command away.

## Known limits

- The gain is a mean, not a per-case promise: it beats the house baseline on 27 of 37
  comparables overall, and loses by up to 0.037 on the ones whose audience barely moves all
  day (Diablo IV, the Call of Duty launches, Final Fantasy VII Rebirth), where any band is
  too wide and any centre factor is wrong. It wins big on the ones that fall hard after the
  unlock.
- The 200,000+ factor rests on six comparables. The trend behind it is significant across all
  16 above 100,000 (p = 0.0094) and the cut is a plateau, but six points is still six
  points: if GTA VI holds its audience instead of decaying, that factor is the single largest
  source of loss in this entry.
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
