"""Score the real entry with a centre factor, through main.py itself.

`centre_fit.py` found one number per bucket helps out of sample: c=0.90 at 30,000+, 1.50
between 5,000 and 30,000, 2.00 below that. This runs those through the shipped entry (writes
the .in files, runs `python -P -s main.py`, scores the .out files) with and without the
factor, so the gain is measured on the code that ships rather than on a formula beside it.

It patches a copy of main.py in a temp directory: the repository is untouched, and the patch
is the three lines that turn `centre = p1` into `centre = p1 * c`.

Read-only on the repository.
"""

import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from band_check import LEVELS  # noqa: E402
from score_entry import REPO, KIT, comparables  # noqa: E402

FACTORS = {"S0, S1 = 0.25, 0.10": 0.90, "W0, W1 = 0.40, 0.20": 1.50, "V0, V1 = 0.80, 0.50": 2.00}


def patched_source(with_factor):
    text = open(os.path.join(REPO, "main.py"), encoding="utf-8").read()
    if not with_factor:
        return text
    # forecast_hour takes p1 and builds every quantile from it; multiply there, once.
    old = "    sigma = s0 + s1 * math.sqrt(h - 1)"
    new = ("    sigma = s0 + s1 * math.sqrt(h - 1)\n"
           "    p1 = p1 * CENTRE\n")
    text = text.replace(old, new, 1)
    lines = []
    for line in text.split("\n"):
        lines.append(line)
        if line.startswith("V0, V1 ="):
            for key, c in FACTORS.items():
                pass
            lines.append("CENTRE = 1.0")
    text = "\n".join(lines)
    # each band gets its factor by the bucket it belongs to; do it in band() by returning it
    text = text.replace(
        '    if p1 >= SMALL:\n        return (S0, S1)\n    if p1 >= MID:\n        return (W0, W1)\n    return (V0, V1)',
        '    global CENTRE\n'
        '    if p1 >= SMALL:\n        CENTRE = 0.90\n        return (S0, S1)\n'
        '    if p1 >= MID:\n        CENTRE = 1.50\n        return (W0, W1)\n'
        '    CENTRE = 2.00\n    return (V0, V1)')
    return text


def run(rows, with_factor):
    work = tempfile.mkdtemp(prefix="gta6-centre-")
    in_dir, out_dir = os.path.join(work, "in"), os.path.join(work, "out")
    os.makedirs(in_dir)
    os.makedirs(out_dir)
    path = os.path.join(work, "main.py")
    open(path, "w", encoding="utf-8").write(patched_source(with_factor))
    for i, r in enumerate(rows):
        json.dump({"schema": "makefun/twitch-ccu-case/v1", "id": "c%02d" % i, "levels": LEVELS,
                   "known": [{"hour": 1, "viewers": int(round(r["p1"]))}],
                   "forecast": [{"hour": h} for h in range(2, 25)]},
                  open(os.path.join(in_dir, "c%02d.in" % i), "w", encoding="utf-8"))
    env = dict(os.environ, MAKEFUN_INPUT_DIR=in_dir, MAKEFUN_OUTPUT_DIR=out_dir)
    p = subprocess.run([sys.executable, "-P", "-s", path], env=env, capture_output=True, text=True)
    if p.returncode != 0:
        shutil.rmtree(work, ignore_errors=True)
        raise SystemExit("main.py failed: " + p.stderr[-1200:])
    total, items = 0.0, 0
    per = {}
    for i, r in enumerate(rows):
        body = json.load(open(os.path.join(out_dir, "c%02d.out" % i), encoding="utf-8"))
        t, n = 0.0, 0
        for row in body["hours"]:
            y = r["truth"].get(row["hour"])
            if y is None or y <= 0:
                continue
            y = max(float(y), 1.0)
            for tau, q in zip(LEVELS, row["q"]):
                d = math.log(y) - math.log(max(float(q), 1.0))
                t += 2 * max(tau * d, (tau - 1) * d)
                n += 1
        if n:
            per[i] = t / n
            total += t
            items += n
    shutil.rmtree(work, ignore_errors=True)
    return total / items, per


def main():
    rows = comparables(KIT)
    flat, _ = run(rows, False)
    shaped, per = run(rows, True)
    print("37 comparables, scored through main.py:")
    print("  flat centre (shipped)          %.6f" % flat)
    print("  centre factor 0.90 / 1.50 / 2.00  %.6f" % shaped)
    print("  change %+.6f (%.1f%%)" % (shaped - flat, 100.0 * (shaped - flat) / flat))
    coh = [per[i] for i, r in enumerate(rows) if r["p1"] >= 30_000]
    print("  30,000+ cohort (n=%d) %.6f" % (len(coh), sum(coh) / len(coh)))


if __name__ == "__main__":
    main()
