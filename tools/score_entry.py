"""Score main.py itself on the comparables, not a re-derivation of its formula.

Every other tool here recomputes `p1 * exp(z * (S0 + S1*sqrt(h-1)))` from band numbers it
holds, which can drift from what ships. This calls the real entry point: it writes one .in
file per comparable into a temp input directory, runs `main.py` as the grader does
(`python -P -s`), reads back the .out files, and scores them against the comparable's
recorded hours.

Two bands arrive through flags so a change can be compared against the shipped file before
it is committed: `--baseline-band 0.0,0.15` reproduces the house baseline's band through the
same code path, `--old 0.10,0.12,100000` the band an earlier revision shipped.

Read-only on the repository: the temp input/output live under the system temp directory.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
# tools/ sits inside the repository; the kit sits beside the repository, not inside it.
KIT = os.path.join(os.path.dirname(REPO), "gta6-twitch-ccu-forecast-01-kit")

from band_check import LEVELS, day_rows  # noqa: E402


def comparables(kit):
    in_dir = os.path.join(kit, "input")
    cases = sorted(n for n in os.listdir(in_dir) if n.endswith(".in"))
    comps = json.load(open(os.path.join(in_dir, cases[0]), encoding="utf-8"))["comparables"]
    seen, out = set(), []
    for comp in comps:
        key = (comp.get("name"), comp.get("day_start"))
        if key in seen:
            continue
        seen.add(key)
        day = day_rows(comp)
        p1 = day.get(1)
        if p1 is None or p1 < 1:
            continue
        out.append({"name": comp.get("name") or "?", "day_start": comp.get("day_start"),
                    "p1": float(p1), "truth": day})
    return out


def score(rows, out_dir):
    """Mean pinball loss over every (case, hour, level), skipping hours with no print.

    Per-case losses are keyed by the case's slug, not by the comparable's name: two
    comparables can share a name (a re-release, a remaster) and keying on the name would let
    the later one overwrite the earlier one's loss.
    """
    total, items = 0.0, 0
    per_case = {}
    for r in rows:
        path = os.path.join(out_dir, r["slug"] + ".out")
        body = json.load(open(path, encoding="utf-8"))
        case_total, case_items = 0.0, 0
        for row in body["hours"]:
            y = r["truth"].get(row["hour"])
            if y is None or y <= 0:
                continue
            y = max(float(y), 1.0)
            for tau, q in zip(LEVELS, row["q"]):
                d = __import__("math").log(y) - __import__("math").log(max(float(q), 1.0))
                case_total += 2 * max(tau * d, (tau - 1) * d)
                case_items += 1
        if case_items:
            per_case[r["slug"]] = case_total / case_items
            total += case_total
            items += case_items
    return total / items if items else float("nan"), per_case


def run_entry(rows, band_override, scheme=None):
    """Run the entry over one .in per comparable and score the .out files it writes.

    band_override is (S0, S1, cut): every band set to that pair and both cuts to `cut`.
    scheme is (cut1, cut2, (S0,S1), (W0,W1), (V0,V1)): the three bands and both cuts given
    outright, which is what a search over band layouts needs.
    """
    work = tempfile.mkdtemp(prefix="gta6-score-")
    in_dir = os.path.join(work, "in")
    out_dir = os.path.join(work, "out")
    os.makedirs(in_dir)
    os.makedirs(out_dir)
    source = os.path.join(REPO, "main.py")
    if band_override is not None or scheme is not None:
        text = open(source, encoding="utf-8").read()
        if scheme is not None:
            cut1, cut2, a, w, v = scheme
        else:
            s0, s1, cut = band_override
            cut1, cut2, a, w, v = cut, cut, (s0, s1), (s0, s1), (s0, s1)
        # Every band gets the override and every cut moves with it: leaving one band where it
        # was made an arm of a comparison secretly score a different band. The cuts are matched
        # by name and any number, so a later edit to their values cannot silently no-op this.
        for name, pair in (("S0, S1 =", a), ("W0, W1 =", w), ("V0, V1 =", v)):
            start = text.index(name)
            end = text.index("\n", start)
            text = text[:start] + "%s %.2f, %.2f" % (name, pair[0], pair[1]) + text[end:]
        text, n1 = re.subn(r"^SMALL = [\d_]+$", "SMALL = %d" % max(cut1, cut2), text, flags=re.M)
        text, n2 = re.subn(r"^BIG = [\d_]+$", "BIG = %d" % (10 ** 12), text, flags=re.M)
        text, n3 = re.subn(r"^MID = [\d_]+$", "MID = %d" % min(cut1, cut2), text, flags=re.M)
        # The centre factors move with the arm too: a "house baseline" that kept the shipped
        # factors would be scoring a different model and flattering the comparison.
        text, n4 = re.subn(r"^C[0-3], C0, C1, C2 = .*$", "C3, C0, C1, C2 = 1.00, 1.00, 1.00, 1.00",
                           text, flags=re.M)
        if n1 != 1 or n3 != 1 or n4 != 1:
            shutil.rmtree(work, ignore_errors=True)
            raise SystemExit("score_entry: could not substitute the model (SMALL %d, MID %d, BIG %d, C %d)"
                             % (n1, n3, n2, n4))
        source = os.path.join(work, "main.py")
        open(source, "w", encoding="utf-8").write(text)
    for i, r in enumerate(rows):
        r["slug"] = "c%02d" % i
        case = {"schema": "makefun/twitch-ccu-case/v1", "id": r["slug"],
                "levels": LEVELS, "known": [{"hour": 1, "viewers": int(round(r["p1"]))}],
                "forecast": [{"hour": h} for h in range(2, 25)]}
        json.dump(case, open(os.path.join(in_dir, r["slug"] + ".in"), "w", encoding="utf-8"))
    env = dict(os.environ, MAKEFUN_INPUT_DIR=in_dir, MAKEFUN_OUTPUT_DIR=out_dir)
    proc = subprocess.run([sys.executable, "-P", "-s", source], env=env,
                          capture_output=True, text=True)
    if proc.returncode != 0:
        shutil.rmtree(work, ignore_errors=True)
        raise SystemExit("main.py failed: " + proc.stderr[-800:])
    value, per_case = score(rows, out_dir)
    shutil.rmtree(work, ignore_errors=True)
    cohort = [per_case[r["slug"]] for r in rows if r["p1"] >= 10_000 and r["slug"] in per_case]
    return (value, (sum(cohort) / len(cohort) if cohort else float("nan"))), per_case


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kit", default=KIT)
    ap.add_argument("--min-viewers", type=float, default=0.0,
                    help="score only comparables whose first hour is at least this")
    args = ap.parse_args()
    rows = [r for r in comparables(args.kit) if r["p1"] >= args.min_viewers]

    shipped, per_ship = run_entry(rows, None)
    print("%-14s %d comparables, first hour >= %.0f" % ("shipped", len(rows), args.min_viewers))
    print("  mean pinball loss (the entry's own .out files): %.6f" % shipped[0])

    house, per_house = run_entry(rows, (0.0, 0.15, 10 ** 12))
    old, per_old = run_entry(rows, (0.10, 0.12, 100_000))
    print("  house baseline band through the same code:      %.6f" % house[0])
    print("  the band this entry shipped before (0.10/0.12): %.6f" % old[0])

    by_slug = {r["slug"]: r["name"] for r in rows}
    better = sum(1 for k in per_ship if per_ship[k] < per_house[k] - 1e-12)
    print("  beats the house baseline on %d of %d comparables" % (better, len(per_ship)))
    worse = [(by_slug[k], per_ship[k] - per_house[k]) for k in per_ship
             if per_ship[k] > per_house[k] + 1e-12]
    if worse:
        print("  loses on %d: " % len(worse) + ", ".join("%s (%+.4f)" % (k, d) for k, d in
                                                       sorted(worse, key=lambda kv: -kv[1])[:8]))


if __name__ == "__main__":
    main()
