"""Score candidate bands on the comparables the practice cases ship, leave-one-out.

For each comparable with a first-hour print of at least SMALL viewers, hour 1 is the
print and hours 2..24 are the truth; a candidate (S0, S1) forecasts every one of those
hours and pays the contest's pinball loss, 2 * max(tau*d, (tau-1)*d) with
d = ln(y) - ln(q_tau). Reported per comparable, and pooled.

The kit's sealed practice answers are not in input/, so the comparables are the only
ground truth this machine holds: they are the same launches the practice cases come from,
minus the practice's own four.

Read-only: prints numbers, writes nothing.
"""

import json
import math
import os
import sys

KIT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..",
                                                        "gta6-twitch-ccu-forecast-01-kit")
IN_DIR = os.path.join(KIT, "input")

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.645, -0.674, 0.0, 0.674, 1.645]
SMALL = 100_000
CAP = 1_000_000_000

CANDIDATES = [
    ("house baseline   S0=0.00 S1=0.15", 0.00, 0.15),
    ("tuned            S0=0.10 S1=0.12", 0.10, 0.12),
    ("wider band       S0=0.10 S1=0.15", 0.10, 0.15),
    ("narrower band    S0=0.00 S1=0.12", 0.00, 0.12),
    ("narrower band    S0=0.05 S1=0.12", 0.05, 0.12),
    ("wide             S0=0.10 S1=0.18", 0.10, 0.18),
    ("very narrow      S0=0.00 S1=0.10", 0.00, 0.10),
]


def round2(x):
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if value.is_integer() else value


def hourly_index(rows):
    """hour -> viewers, by `from` minus the series' own first point (an hour grid)."""
    if not rows:
        return {}
    first = rows[0].get("from")
    out = {}
    for row in rows:
        frm = row.get("from")
        viewer = row.get("viewers")
        if frm is None or viewer is None or first is None:
            continue
        h = int(round((_ts(frm) - _ts(first)) / 3600.0)) + 1
        out[h] = float(viewer)
    return out


def _ts(iso):
    import datetime
    return datetime.datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=datetime.timezone.utc).timestamp()


def day_rows(comp):
    """The comparable's release-day rows: hour h of day_start + (h-1) h, h = 1..24."""
    start = _ts(comp["day_start"])
    by_hour = {}
    for row in comp.get("hourly") or []:
        frm = row.get("from")
        if frm is None:
            continue
        off = (_ts(frm) - start) / 3600.0
        if 0 <= off < 24:
            by_hour[int(off) + 1] = row.get("viewers")
    return by_hour


def quantiles(p1, h, s0, s1):
    sigma = s0 + s1 * math.sqrt(h - 1)
    row = []
    for z in Z:
        q = p1 * math.exp(z * sigma)
        q = min(max(q, 1.0), CAP)
        row.append(round2(q))
    for i in range(1, 5):
        if row[i] < row[i - 1]:
            row[i] = row[i - 1]
    return row


def loss(p1, s0, s1, truth):
    total = 0.0
    items = 0
    for h in range(2, 25):
        y = truth.get(h)
        if y is None:
            continue
        y = max(float(y), 1.0)
        qs = quantiles(p1, h, s0, s1)
        for tau, q in zip(LEVELS, qs):
            d = math.log(y) - math.log(max(float(q), 1.0))
            total += 2 * max(tau * d, (tau - 1) * d)
            items += 1
    return (total / items) if items else None


def main():
    cases = sorted(n for n in os.listdir(IN_DIR) if n.endswith(".in"))
    comps = json.load(open(os.path.join(IN_DIR, cases[0]), encoding="utf-8"))["comparables"]
    seen = set()
    pooled = {name: [0.0, 0] for name, _, _ in CANDIDATES}
    rows = []
    for comp in comps:
        key = (comp.get("name"), comp.get("day_start"))
        if key in seen:
            continue
        seen.add(key)
        day = day_rows(comp)
        p1 = day.get(1)
        if p1 is None or p1 < SMALL:
            continue
        line = [comp.get("name") or "?", comp.get("day_start"), "%.0f" % p1]
        for name, s0, s1 in CANDIDATES:
            v = loss(p1, s0, s1, day)
            line.append("--" if v is None else "%.6f" % v)
            if v is not None:
                pooled[name][0] += v
                pooled[name][1] += 1
        rows.append(line)

    head = ["name", "day_start", "p1"] + [name for name, _, _ in CANDIDATES]
    widths = [max(len(str(r[i])) for r in ([head] + rows)) for i in range(len(head))]
    fmt = "  ".join("{:<%d}" % w for w in widths)
    print(fmt.format(*head))
    for r in rows:
        print(fmt.format(*[str(x) for x in r]))
    print()
    print("pooled mean pinball loss over %d comparables with p1 >= %d:" % (len(rows), SMALL))
    for name, _, _ in CANDIDATES:
        s, n = pooled[name]
        print("  %-34s %.6f  (n=%d)" % (name, s / n if n else float("nan"), n))


if __name__ == "__main__":
    main()
