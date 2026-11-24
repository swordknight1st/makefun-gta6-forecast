# Post-mortem: what this entry did, and where it lost

The final is resolved. This entry (submission `01a1eb3b-89c1-720a-b376-1e49fb200497`, commit
`1738309`) placed **6433 of 11,568** with pinball loss **0.224327**, typical miss **41.38%**,
90% coverage **1.0**. The house persistence baseline placed 8327 with loss 0.349, so the work
here beat it by 36% and was prize-eligible — but 20 places pay and the last one took 0.102.

`main.py` is left exactly as submitted. This file records what was learned, so the next entry
starts from the diagnosis rather than from scratch.

## The scoreboard, as context

| rank | loss | typical miss | coverage 90 |
|---|---|---|---|
| 1 | 0.0663 | 9.41% | 1.00 |
| 100 | 0.1020 | 15.86% | 1.00 |
| 1,000 | 0.1330 | 23.45% | 1.00 |
| 3,000 | 0.1580 | 25.23% | 0.35 |
| **6,433 (this entry)** | **0.2243** | **41.38%** | **1.00** |
| 8,327 (house baseline) | 0.3490 | 65.32% | 0.57 |

Two things to read off it. First, coverage 1.0 with a 41% miss is a **centre** failure, not a
band failure: the 90% interval always contained the truth, so the band was if anything too
wide. Second, rank 3,000 held a band that covered only 35% of hours and still beat this entry:
an over-wide band costs pinball loss at every level, so a wide band is not free insurance.

## What was right

The direction of the centre. This entry shipped `c=0.75` for launches above 200,000 viewers
(the largest cohort decays after the unlock), and its typical miss of 41.38% beat the flat
centre's 65.32% by 24 points. The measured trend behind that choice held up: over the 16
comparables above 100,000 viewers, the rank correlation of log(viewers) with
log(hour 24 / hour 1) is −0.638, permutation p = 0.0094.

## What was wrong, and the reasoning error behind it

The model had **one constant factor per size bucket** and no shape. The single-player,
100,000+ comparables — the segment Grand Theft Auto VI belongs to — average a ratio of about
0.79 of hour 1 across the day, which is close to the 0.75 that shipped. So the *level* was
right. What a constant cannot express is that the day is not flat around that average:

```
hour   2     3     4     5     6     7     8     9    10    11    12    13
     0.89  0.68  0.56  0.66  0.63  0.58  0.55  0.50  0.47  0.50  0.57  0.62

hour  14    15    16    17    18    19    20    21    22    23    24
     0.74  0.77  0.88  1.02  1.06  1.26  1.16  1.20  1.15  1.05  1.11
```

The audience halves by hour 10 and comes back to 1.26 by hour 19. A flat centre at 0.75 is
wrong by 60% at both ends; that is where the 41% miss comes from.

This was known and rejected, and the rejection was a mistake in method. `tools/shape_fit.py`
compared a per-hour curve against a flat centre, but the two arms were not treated alike: the
curve arm refitted a 221-point (S0, S1) grid inside every fold (`fit_band(rest, curve)`), while
the flat arm kept the shipped bands, fixed. The curve therefore paid for a joint 23-parameter
plus 221-point search and the flat centre did not, and it lost:
0.790958 against 0.714627. That comparison measured the cost of refitting the band, not the
value of the shape.

`tools/segment_shape.py` holds the band fixed at `0.25/0.10` for both arms and refits only the
centre. With that asymmetry removed, the per-hour curve wins in **every** segment:

| segment | per-hour curve | one constant | difference |
|---|---|---|---|
| single-player, 100,000+ (n=9, GTA VI's) | 0.212518 | 0.247722 | −14.1% |
| single-player, 30,000+ (n=14) | 0.281735 | 0.330031 | −14.6% |
| single-player only (n=22) | 0.757904 | 0.829346 | −8.6% |
| all 37 | 0.822802 | 0.908415 | −9.4% |

The two entries that finished first and third say the same thing in their titles: rank 1 is a
"tier/rolling WLS log-ratio ensemble", rank 3 a "Stretched single-player midnight launch
curve". Shape, segmented by launch type, was the winning idea.

## What it would have been worth

Scaling the segment's measured gain onto the final score — a rough extrapolation, not a
measurement — puts the curve near `0.224 × (0.212518 / 0.247722) ≈ 0.19`, which on the table
above is around rank 5,000 rather than 6,433. Better, and still nowhere near the top 100.

So the shape was not the only gap, and probably not the largest. To reach a 10% miss the centre
has to be within 10% at every hour, which needs the *level* of the curve as well as its form,
and this entry's level came from one number per bucket chosen on 5-9 comparables. A weighted
fit over the full comparable set, per tier, is the obvious next step; the winners' "WLS
log-ratio ensemble" is exactly that.

## What to keep

- `tools/score_entry.py` scores the real entry end to end, writing .in files and running
  `python -P -s main.py` as the grader does. Every other tool computes a formula; this one
  scores the artifact.
- `tools/check_out.py` holds the .out contract and the byte-for-byte determinism check.
- The habit that caught three of this session's own errors: an arm of a comparison that is
  not substituted the same way as the other arm is not a comparison. `score_entry.py`'s cut
  substitution had silently matched nothing after the constants changed, and its baseline arm
  had kept the shipped centre factors; both were found only by noticing that a number that
  should have been stable had moved.
