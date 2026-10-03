"""
Re-check every computational result in RESULTS.md.

    python code/reproduce.py
    python code/reproduce.py --drat-trim /path/to/drat-trim
    python code/reproduce.py --skip-crosscheck

Three steps:

  1. Colorings.   Every file in certificates/colorings/ is tested against the
                  definition by verify.py.
  2. Proofs.      For every case where no coloring exists, the CNF formula and
                  DRAT proof in certificates/unsat/ are regenerated, and the
                  proof is checked with drat-trim (if it is installed).
  3. Cross-check. On K(5,2) and K(6,2) the number of colorings admitted by the
                  SAT encoding is compared with the number found by testing
                  every possible assignment directly.
"""

import argparse
import glob
import itertools
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sat
import verify

from pysat.solvers import Cadical153

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLORINGS_DIR = os.path.join(ROOT, "certificates", "colorings")
UNSAT_DIR = os.path.join(ROOT, "certificates", "unsat")

# (n, kappa, k): K(n, kappa) has no CFON* coloring with k colors.
UNSAT_CASES = [
    (7, 2, 2), (8, 2, 2), (9, 2, 2),             # 2 colors fail, so the value is 3
    (5, 2, 1), (6, 2, 1), (7, 3, 1), (8, 3, 1),  # 1 color fails, so the value is 2
]

# (n, kappa, k) for the brute-force cross-check of the encoding.
CROSSCHECK_CASES = [(5, 2, 1), (5, 2, 2), (6, 2, 1), (6, 2, 2)]


def step_colorings():
    print("Step 1: colorings")
    ok = True
    paths = sorted(glob.glob(os.path.join(COLORINGS_DIR, "*.json")))
    for path in paths:
        n, kappa, k, problems = verify.check_file(path)
        status = "VALID  " if not problems else "INVALID"
        print(f"  {status}  K({n},{kappa}) with {k} color(s)   {os.path.basename(path)}")
        ok = ok and not problems
    if not paths:
        print("  no coloring files found")
        ok = False
    return ok


def step_proofs(drat_trim):
    print("Step 2: proofs that no coloring exists")
    if drat_trim is None:
        print("  drat-trim not found; proofs will be regenerated but not checked.")
        print("  Install it from https://github.com/marijnheule/drat-trim and rerun,")
        print("  or pass its location with --drat-trim.")
    ok = True
    for n, kappa, k in UNSAT_CASES:
        coloring, cnf_path, drat_path = sat.certify(n, kappa, k, UNSAT_DIR)
        label = f"K({n},{kappa}) with {k} color(s)"
        if coloring is not None:
            print(f"  UNEXPECTED  {label}: the solver found a coloring")
            ok = False
            continue
        if drat_trim is None:
            print(f"  UNSAT, proof not checked   {label}")
            continue
        output = subprocess.run([drat_trim, cnf_path, drat_path],
                                capture_output=True, text=True).stdout
        if "s VERIFIED" in output:
            print(f"  UNSAT, proof VERIFIED      {label}")
        else:
            print(f"  PROOF NOT VERIFIED         {label}")
            ok = False
    return ok


def count_by_brute_force(n, kappa, k):
    """Count CFON* colorings by testing every map from the vertices to {0..k}."""
    vertices, neighbors = sat.kneser_graph(n, kappa)
    count = 0
    for assignment in itertools.product(range(k + 1), repeat=len(vertices)):
        valid = True
        for nbrs in neighbors:
            tally = [0] * (k + 1)
            for w in nbrs:
                tally[assignment[w]] += 1
            if 1 not in tally[1:]:
                valid = False
                break
        if valid:
            count += 1
    return count


def count_by_sat(n, kappa, k):
    """Count the colorings admitted by the encoding.

    Solutions are counted by their x variables only, since those are the
    coloring. Each found coloring is excluded and the solver is run again
    until no coloring is left.
    """
    vertices, neighbors = sat.kneser_graph(n, kappa)
    x_vars = range(1, len(vertices) * k + 1)
    count = 0
    with Cadical153(bootstrap_with=sat.encode(neighbors, k)) as solver:
        while solver.solve():
            count += 1
            model = set(solver.get_model())
            solver.add_clause([-x if x in model else x for x in x_vars])
    return count


def step_crosscheck():
    print("Step 3: encoding against brute force")
    ok = True
    for n, kappa, k in CROSSCHECK_CASES:
        by_sat = count_by_sat(n, kappa, k)
        by_brute_force = count_by_brute_force(n, kappa, k)
        status = "AGREE   " if by_sat == by_brute_force else "DISAGREE"
        print(f"  {status}  K({n},{kappa}) with {k} color(s): "
              f"{by_sat} colorings by SAT, {by_brute_force} by brute force")
        ok = ok and by_sat == by_brute_force
    return ok


def main():
    parser = argparse.ArgumentParser(description="Re-check every computational result.")
    parser.add_argument("--drat-trim", metavar="PATH",
                        help="location of the drat-trim program")
    parser.add_argument("--skip-crosscheck", action="store_true",
                        help="skip step 3")
    args = parser.parse_args()
    drat_trim = args.drat_trim or shutil.which("drat-trim")

    ok = step_colorings()
    ok = step_proofs(drat_trim) and ok
    if not args.skip_crosscheck:
        ok = step_crosscheck() and ok

    print("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
