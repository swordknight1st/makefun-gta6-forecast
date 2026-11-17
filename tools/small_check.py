"""Small first hours on the same comparables: the fallback band against the tuned one.

main.py hands a comparable whose hour-1 print is under 100,000 viewers the house
baseline's band (S0=0, S1=0.15), because the 16 comparables that set the tuned pair all
sit above that floor. This prints the loss of both bands on the comparables below the
floor, pooled and one by one, so the fallback can be judged on its own cohort.

Read-only: prints numbers, writes nothing.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from band_check import SMALL, day_rows, loss  # noqa: E402

KIT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..",
                                                        "gta6-twitch-ccu-forecast-01-kit")
IN_DIR = os.path.join(KIT, "input")

BANDS = [
    ("fallback  S0=0.00 S1=0.15", 0.00, 0.15),
    ("tuned     S0=0.10 S1=0.12", 0.10, 0.12),
    ("middle    S0=0.05 S1=0.14", 0.05, 0.14),
    ("mid-narrow S0=0.05 S1=0.12", 0.05, 0.12),
    ("bare      S0=0.00 S1=0.13", 0.00, 0.13),
]


def main():
    cases = sorted(n for n in os.listdir(IN_DIR) if n.endswith(".in"))
    comps = json.load(open(os.path.join(IN_DIR, cases[0]), encoding="utf-8"))["comparables"]
    seen = set()
    pooled = {name: [0.0, 0] for name, _, _ in BANDS}
    rows = []
    for comp in comps:
        key = (comp.get("name"), comp.get("day_start"))
        if key in seen:
            continue
        seen.add(key)
        day = day_rows(comp)
        p1 = day.get(1)
        if p1 is None or p1 >= SMALL:
            continue
        line = [comp.get("name") or "?", comp.get("day_start"), "%.0f" % p1]
        for name, s0, s1 in BANDS:
            v = loss(p1, s0, s1, day)
            line.append("--" if v is None else "%.6f" % v)
            if v is not None:
                pooled[name][0] += v
                pooled[name][1] += 1
        rows.append(line)
    if not rows:
        print("no comparable below the floor")
        return
    head = ["name", "day_start", "p1"] + [n for n, _, _ in BANDS]
    widths = [max(len(str(r[i])) for r in ([head] + rows)) for i in range(len(head))]
    fmt = "  ".join("{:<%d}" % w for w in widths)
    print(fmt.format(*head))
    for r in rows:
        print(fmt.format(*[str(x) for x in r]))
    print()
    print("pooled mean pinball loss over %d comparables with p1 < %d:" % (len(rows), SMALL))
    for name, _, _ in BANDS:
        s, n = pooled[name]
        print("  %-28s %.6f  (n=%d)" % (name, s / n if n else float("nan"), n))


if __name__ == "__main__":
    main()
