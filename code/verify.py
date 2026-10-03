"""
Independent checker for CFON* colorings of Kneser graphs.

    python code/verify.py FILE.json [FILE.json ...]
    python code/verify.py --table FILE.json      also print the check at every vertex

This script deliberately shares no code with sat.py. It rebuilds the graph from
the definition and tests the CFON* condition at every vertex, so a coloring it
accepts is valid regardless of how the coloring was found.

Input format (only colored vertices are listed; all others have color 0):

    {
      "n": 5,
      "kappa": 2,
      "colors": 2,
      "coloring": {"2,3": 1, "2,4": 1, "3,5": 1, "4,5": 1, "2,5": 2, "3,4": 2}
    }
"""

import itertools
import json
import sys


def check(n, kappa, colors, coloring, table=False):
    """Return a list of problems. An empty list means the coloring is valid."""
    problems = []

    # The coloring must use real vertices and real colors.
    for vertex, color in coloring.items():
        if (len(vertex) != kappa or len(set(vertex)) != kappa
                or not all(1 <= element <= n for element in vertex)):
            problems.append(f"{set(vertex)} is not a {kappa}-subset of 1..{n}")
        if not (isinstance(color, int) and 1 <= color <= colors):
            problems.append(f"{set(vertex)} has color {color}, outside 1..{colors}")
    if problems:
        return problems

    vertices = [frozenset(s) for s in itertools.combinations(range(1, n + 1), kappa)]
    for v in vertices:
        # Count how often each color appears on the neighbors of v.
        # The neighbors of v are the vertices disjoint from v.
        tally = {}
        for w in vertices:
            if not (v & w):
                color = coloring.get(w, 0)
                if color != 0:
                    tally[color] = tally.get(color, 0) + 1
        seen_once = sorted(c for c, count in tally.items() if count == 1)
        if table:
            name = "{" + ",".join(map(str, sorted(v))) + "}"
            counts = "  ".join(f"color {c}: {tally.get(c, 0)}" for c in range(1, colors + 1))
            verdict = f"sees {seen_once[0]} exactly once" if seen_once else "FAILS"
            print(f"    {name:<14} own color {coloring.get(v, 0)}    {counts}    {verdict}")
        if not seen_once:
            problems.append(f"vertex {sorted(v)} sees no color exactly once")
    return problems


def check_file(path, table=False):
    with open(path) as f:
        data = json.load(f)
    n, kappa, colors = data["n"], data["kappa"], data["colors"]
    coloring = {frozenset(int(e) for e in key.split(",")): value
                for key, value in data["coloring"].items()}
    if len(coloring) != len(data["coloring"]):
        return n, kappa, colors, ["the same vertex is listed twice"]
    return n, kappa, colors, check(n, kappa, colors, coloring, table)


def main():
    args = sys.argv[1:]
    table = "--table" in args
    paths = [a for a in args if a != "--table"]
    if not paths:
        print(__doc__)
        sys.exit(2)

    all_valid = True
    for path in paths:
        n, kappa, colors, problems = check_file(path, table)
        if problems:
            all_valid = False
            print(f"INVALID  K({n},{kappa}) with {colors} color(s)   {path}")
            for problem in problems:
                print(f"         {problem}")
        else:
            print(f"VALID    K({n},{kappa}) with {colors} color(s)   {path}")
    sys.exit(0 if all_valid else 1)


if __name__ == "__main__":
    main()
