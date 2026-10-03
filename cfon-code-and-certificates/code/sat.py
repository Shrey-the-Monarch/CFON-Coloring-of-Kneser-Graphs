"""
CFON* colorings of Kneser graphs by SAT.

Question answered:  can the Kneser graph K(n, kappa) be CFON*-colored with k colors?

    python code/sat.py N KAPPA K                  search and print the answer
    python code/sat.py N KAPPA K --save FILE      also save a found coloring as JSON
    python code/sat.py N KAPPA K --certify DIR    write the CNF formula to DIR and,
                                                  if no coloring exists, a DRAT proof

Definitions
-----------
K(n, kappa): vertices are the kappa-element subsets of {1, ..., n}; two vertices
are adjacent when the subsets are disjoint.

CFON* coloring with k colors: a map C from the vertices to {0, 1, ..., k} such
that every vertex v has some color c in {1, ..., k} that appears on exactly one
neighbor of v. Color 0 means "uncolored".

Encoding
--------
For every vertex v and every color c in {1, ..., k} there are two variables:

    x(v, c)   "v has color c"
    u(v, c)   "c is a color that appears exactly once among the neighbors of v"

A vertex with no x variable true is uncolored. The clauses are:

    (1) each vertex has at most one color:
            NOT x(v, c)  OR  NOT x(v, c')              for all colors c < c'
    (2) each vertex sees some color exactly once:
            u(v, 1) OR ... OR u(v, k)
    (3) u(v, c) forces at least one neighbor of v to have color c:
            NOT u(v, c)  OR  x(w1, c) OR ... OR x(wd, c)
    (4) u(v, c) forces at most one neighbor of v to have color c:
            NOT u(v, c)  OR  NOT x(w, c)  OR  NOT x(w', c)   for all neighbors w < w'

There are no auxiliary variables, so every clause is a direct statement about
the coloring. The formula is satisfiable exactly when a CFON* coloring with k
colors exists.
"""

import argparse
import json
import os
from itertools import combinations

from pysat.solvers import Cadical153, Glucose3


# ----------------------------------------------------------------------------
# The graph
# ----------------------------------------------------------------------------

def kneser_graph(n, kappa):
    """Return (vertices, neighbors) for K(n, kappa).

    vertices  : list of kappa-subsets of {1..n}, as sorted tuples
    neighbors : neighbors[i] is the list of indices j with vertices[j]
                disjoint from vertices[i]
    """
    vertices = list(combinations(range(1, n + 1), kappa))
    neighbors = [[] for _ in vertices]
    for i, j in combinations(range(len(vertices)), 2):
        if not set(vertices[i]) & set(vertices[j]):
            neighbors[i].append(j)
            neighbors[j].append(i)
    return vertices, neighbors


# ----------------------------------------------------------------------------
# The encoding
# ----------------------------------------------------------------------------

def x_var(v, c, k):
    """Variable number of x(v, c): vertex index v (from 0), color c (from 1)."""
    return v * k + c


def u_var(v, c, k, num_vertices):
    """Variable number of u(v, c). The u variables come after all x variables."""
    return num_vertices * k + v * k + c


def encode(neighbors, k):
    """Return the list of clauses for 'this graph has a CFON* coloring with k colors'."""
    V = len(neighbors)
    colors = range(1, k + 1)
    clauses = []
    for v in range(V):
        # (1) at most one color per vertex
        for c1, c2 in combinations(colors, 2):
            clauses.append([-x_var(v, c1, k), -x_var(v, c2, k)])
        # (2) some color is seen exactly once
        clauses.append([u_var(v, c, k, V) for c in colors])
        for c in colors:
            u = u_var(v, c, k, V)
            # (3) at least one neighbor has color c
            clauses.append([-u] + [x_var(w, c, k) for w in neighbors[v]])
            # (4) at most one neighbor has color c
            for w1, w2 in combinations(neighbors[v], 2):
                clauses.append([-u, -x_var(w1, c, k), -x_var(w2, c, k)])
    return clauses


def decode(model, vertices, k):
    """Turn a satisfying assignment into {vertex: color}, colored vertices only."""
    true_vars = {lit for lit in model if lit > 0}
    coloring = {}
    for v, vertex in enumerate(vertices):
        for c in range(1, k + 1):
            if x_var(v, c, k) in true_vars:
                coloring[vertex] = c
    return coloring


# ----------------------------------------------------------------------------
# Solving
# ----------------------------------------------------------------------------

def find_coloring(n, kappa, k):
    """Search for a CFON* coloring of K(n, kappa) with k colors.

    Returns {vertex: color} if one exists and None if the formula is
    unsatisfiable. A None answer is only as trustworthy as the solver; use
    certify() to get a proof that can be checked independently.
    """
    vertices, neighbors = kneser_graph(n, kappa)
    clauses = encode(neighbors, k)
    with Cadical153(bootstrap_with=clauses) as solver:
        if not solver.solve():
            return None
        return decode(solver.get_model(), vertices, k)


def certify(n, kappa, k, directory):
    """Write the CNF formula and, if it is unsatisfiable, a DRAT proof.

    Files written to `directory`:
        K{n}_{kappa}_{k}colors.cnf    the formula, in DIMACS format
        K{n}_{kappa}_{k}colors.drat   the proof (only when unsatisfiable)

    Check the proof with:  drat-trim FILE.cnf FILE.drat

    Glucose 3 is used here because its proofs, as exposed by PySAT, are
    accepted by drat-trim.
    """
    vertices, neighbors = kneser_graph(n, kappa)
    clauses = encode(neighbors, k)
    V = len(vertices)
    num_vars = 2 * V * k

    os.makedirs(directory, exist_ok=True)
    stem = os.path.join(directory, f"K{n}_{kappa}_{k}colors")

    with open(stem + ".cnf", "w") as f:
        f.write(f"c CFON* coloring of the Kneser graph K({n},{kappa}) with {k} color(s)\n")
        f.write(f"c vertices: the {kappa}-subsets of 1..{n} in lexicographic order, numbered from 0\n")
        f.write(f"c x(v,c) = variable v*{k} + c                 'vertex v has color c'\n")
        f.write(f"c u(v,c) = variable {V * k} + v*{k} + c       'v sees color c exactly once'\n")
        f.write(f"p cnf {num_vars} {len(clauses)}\n")
        for clause in clauses:
            f.write(" ".join(map(str, clause)) + " 0\n")

    with Glucose3(bootstrap_with=clauses, with_proof=True) as solver:
        if solver.solve():
            return decode(solver.get_model(), vertices, k), stem + ".cnf", None
        proof = solver.get_proof()

    with open(stem + ".drat", "w") as f:
        for line in proof:
            f.write(line.strip() + "\n")
        # The proof must end by deriving the empty clause.
        if not proof or proof[-1].strip() != "0":
            f.write("0\n")
    return None, stem + ".cnf", stem + ".drat"


# ----------------------------------------------------------------------------
# Saving a coloring
# ----------------------------------------------------------------------------

def save_coloring(path, n, kappa, k, coloring):
    """Save a coloring as JSON. Only colored vertices are listed."""
    data = {
        "n": n,
        "kappa": kappa,
        "colors": k,
        "coloring": {",".join(map(str, vertex)): color
                     for vertex, color in sorted(coloring.items())},
    }
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def format_coloring(coloring):
    return ", ".join("{" + ",".join(map(str, vertex)) + "}: " + str(color)
                     for vertex, color in sorted(coloring.items()))


# ----------------------------------------------------------------------------
# Command line
# ----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Decide whether K(n, kappa) has a CFON* coloring with k colors.")
    parser.add_argument("n", type=int)
    parser.add_argument("kappa", type=int)
    parser.add_argument("k", type=int, help="number of colors")
    parser.add_argument("--save", metavar="FILE",
                        help="save a found coloring as JSON")
    parser.add_argument("--certify", metavar="DIR",
                        help="write the CNF formula and, if unsatisfiable, a DRAT proof to DIR")
    args = parser.parse_args()
    n, kappa, k = args.n, args.kappa, args.k

    if n < 2 * kappa + 1:
        parser.error("need n >= 2*kappa + 1 (otherwise the graph is not connected)")

    label = f"K({n},{kappa}) with {k} color(s)"
    if args.certify:
        coloring, cnf_path, drat_path = certify(n, kappa, k, args.certify)
        print(f"formula written to {cnf_path}")
    else:
        coloring = find_coloring(n, kappa, k)
        drat_path = None

    if coloring is None:
        print(f"{label}: UNSATISFIABLE, no coloring exists")
        if drat_path:
            print(f"proof written to {drat_path}")
            print(f"check it with:  drat-trim {cnf_path} {drat_path}")
    else:
        print(f"{label}: SATISFIABLE, {len(coloring)} vertices colored")
        print(format_coloring(coloring))
        if args.save:
            save_coloring(args.save, n, kappa, k, coloring)
            print(f"coloring saved to {args.save}")
            print(f"check it with:  python code/verify.py {args.save}")


if __name__ == "__main__":
    main()
