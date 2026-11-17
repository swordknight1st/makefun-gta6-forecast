"""Contract check for every .out main.py writes, plus a byte-identity guard.

Checks, per file, exactly what the competition's case contract states: one top-level key
`hours`; 23 rows; hours 2..24 each once; five finite numbers above 0 and at most 1e9 per
row; non-decreasing; at most 65,536 bytes. With --golden DIR it also compares each .out
byte for byte against a second run, so two runs of main.py on one input cannot drift.

Exit status is 1 when anything fails, so a shell can gate on it.
"""

import json
import math
import os
import sys

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
LIMIT = 65_536


def check_file(path):
    problems = []
    raw = open(path, "rb").read()
    if len(raw) > LIMIT:
        problems.append("holds %d bytes, over the %d cap" % (len(raw), LIMIT))
    try:
        body = json.loads(raw.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - report anything the JSON reader rejects
        return ["does not parse as JSON: %s" % exc]
    if not isinstance(body, dict) or set(body) != {"hours"}:
        return ["top level is not exactly the key hours: %r" % (sorted(body) if isinstance(body, dict) else type(body).__name__,)]
    hours = body["hours"]
    if not isinstance(hours, list) or len(hours) != 23:
        return ["rows: %r" % (len(hours) if isinstance(hours, list) else type(hours).__name__,)]
    seen = []
    for row in hours:
        if not isinstance(row, dict) or set(row) != {"hour", "q"}:
            problems.append("a row is not exactly hour and q: %r" % (sorted(row) if isinstance(row, dict) else row,))
            continue
        h, q = row["hour"], row["q"]
        if not isinstance(h, int) or isinstance(h, bool) or not 2 <= h <= 24:
            problems.append("hour %r is not 2..24" % (h,))
        seen.append(h)
        if not isinstance(q, list) or len(q) != 5:
            problems.append("hour %r carries %r quantiles" % (h, q))
            continue
        for v in q:
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                problems.append("hour %d holds a non-number %r" % (h, v))
            elif not math.isfinite(v) or v <= 0 or v > 1e9:
                problems.append("hour %d holds %r, outside (0, 1e9]" % (h, v))
        for a, b in zip(q, q[1:]):
            if isinstance(a, (int, float)) and isinstance(b, (int, float)) and b < a:
                problems.append("hour %d steps down: %r" % (h, q))
                break
    if sorted(seen) != list(range(2, 25)):
        problems.append("hours are not 2..24 once each: %r" % (sorted(seen),))
    return problems


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: check_out.py OUT_DIR [--golden DIR]")
    out_dir = sys.argv[1]
    golden = None
    if "--golden" in sys.argv:
        golden = sys.argv[sys.argv.index("--golden") + 1]
    names = sorted(n for n in os.listdir(out_dir) if n.endswith(".out"))
    if not names:
        sys.exit("no .out file in " + out_dir)
    failed = 0
    for name in names:
        problems = check_file(os.path.join(out_dir, name))
        if golden is not None:
            other = os.path.join(golden, name)
            if not os.path.exists(other):
                problems.append("no %s in %s" % (name, golden))
            elif open(other, "rb").read() != open(os.path.join(out_dir, name), "rb").read():
                problems.append("differs byte for byte from %s" % other)
        print("%-10s %s" % (name, "ok" if not problems else "INVALID: " + "; ".join(problems)))
        failed += bool(problems)
    print("%d of %d files valid" % (len(names) - failed, len(names)))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
