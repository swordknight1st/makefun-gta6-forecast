"""Would segmenting have made the shape curve win? The post-mortem, run as evidence.

The final is resolved and this entry placed 6433 of 11,568 (loss 0.224327, typical miss
41.38%, coverage 1.0). The winners' titles say what they did: rank 1 "tier/rolling WLS
log-ratio ensemble", rank 3 "Stretched single-player midnight launch curve". Shape, segmented
by launch type.

`shape_fit.py` rejected a per-hour ratio curve because its leave-one-out loss was worse than a
flat centre's. But that fit pooled all 37 comparables -- pre-launch indies, live-service
shooters and single-player console launches -- into one median. Segmenting is exactly what the
winners did, and it is testable here.

This asks: inside a segment, does a per-hour median ratio curve beat one constant factor, out
of sample? Segments are built from the `platforms` field and a hand-checked list of
single-player titles, since the game's shape follows its audience (people who buy a
single-player game go and play it; live-service audiences keep watching the meta).

Read-only: prints tables.
"""

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

# Checked by hand against each game's release: single-player, console-first launches. GTA VI
# is one of these (single-player, PS5/Xbox, rolling midnight unlock).
SINGLE = {
    "ELDEN RING", "Resident Evil Requiem", "Hogwarts Legacy", "Cyberpunk 2077",
    "Ghost of Yōtei", "Ghost of Yotei", "Black Myth: Wukong", "Hollow Knight: Silksong",
    "007 First Light", "The Legend of Zelda: Tears of the Kingdom", "Starfield",
    "Kingdom Come: Deliverance II", "Assassin's Creed Shadows", "DOOM: The Dark Ages",
    "Clair Obscur: Expedition 33", "Death Stranding 2: On the Beach",
    "FINAL FANTASY VII REBIRTH", "The Last of Us Part II", "Ghost of Tsushima",
    "Stellar Blade", "Saros", "Forza Horizon 5", "Forza Horizon 6",
}


def is_single(r):
    return r["name"] in SINGLE


def ratio(r, h):
    y = r["truth"].get(h)
    if y is None or y <= 0:
        return None
    return math.log(max(float(y), 1.0)) - math.log(r["p1"])


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0


def curve_of(rows):
    out = {}
    for h in range(2, 25):
        vals = [ratio(r, h) for r in rows]
        vals = [v for v in vals if v is not None]
        if vals:
            out[h] = median(vals)
    return out


def loss_curve(p1, curve, truth):
    total, n = 0.0, 0
    for h in range(2, 25):
        y = truth.get(h)
        if y is None or y <= 0:
            continue
        y = max(float(y), 1.0)
        centre = math.log(p1) + curve.get(h, 0.0)
        sigma = BAND[0] + BAND[1] * math.sqrt(h - 1)
        for tau, z in zip(LEVELS, Z):
            q = max(math.exp(centre + z * sigma), 1.0)
            d = math.log(y) - math.log(q)
            total += 2 * max(tau * d, (tau - 1) * d)
            n += 1
    return total / n if n else None


def loss_const(p1, c, truth):
    total, n = 0.0, 0
    for h in range(2, 25):
        y = truth.get(h)
        if y is None or y <= 0:
            continue
        y = max(float(y), 1.0)
        centre = math.log(p1) + math.log(c)
        sigma = BAND[0] + BAND[1] * math.sqrt(h - 1)
        for tau, z in zip(LEVELS, Z):
            q = max(math.exp(centre + z * sigma), 1.0)
            d = math.log(y) - math.log(q)
            total += 2 * max(tau * d, (tau - 1) * d)
            n += 1
    return total / n if n else None


def best_c(rows):
    return min((sum(loss_const(r["p1"], c, r["truth"]) for r in rows) / len(rows), c) for c in CS)


def report(label, rows):
    if len(rows) < 4:
        print("%s: n=%d, too few" % (label, len(rows)))
        return
    curve_tot = const_tot = 0.0
    picks = []
    for i, held in enumerate(rows):
        rest = rows[:i] + rows[i + 1:]
        curve = curve_of(rest)
        _, c = best_c(rest)
        picks.append(c)
        curve_tot += loss_curve(held["p1"], curve, held["truth"])
        const_tot += loss_const(held["p1"], c, held["truth"])
    n = len(rows)
    uniq = sorted(set(picks))
    print("%s (n=%d)" % (label, n))
    print("   leave-one-out: per-hour curve %.6f   one constant %.6f   curve %s by %+.6f"
          % (curve_tot / n, const_tot / n, "WINS" if curve_tot < const_tot else "loses",
             curve_tot / n - const_tot / n))
    print("   fold picks of the constant: " + ", ".join("%.2f x%d" % (u, picks.count(u)) for u in uniq))
    full = curve_of(rows)
    print("   full-sample curve (log ratio by hour): " +
          " ".join("%d:%.3f" % (h, full[h]) for h in sorted(full)))
    print()


def main():
    rows = comparables(KIT)
    single = [r for r in rows if is_single(r)]
    print("segment sizes: %d single-player of %d comparables\n" % (len(single), len(rows)))
    report("all 37", rows)
    report("single-player only", single)
    report("single-player, 100,000+", [r for r in single if r["p1"] >= 100_000])
    report("single-player, 30,000+", [r for r in single if r["p1"] >= 30_000])
    report("non-single (live-service etc.)", [r for r in rows if not is_single(r)])


if __name__ == "__main__":
    main()
