# CFON\* Colorings of Kneser Graphs

Oct 3, 2026 · @Shrey

This repository holds the results of a mathematics research project, some of it prepared for ISEF, on partial conflict-free open-neighborhood (CFON\*) colorings of Kneser graphs K(n, κ). It disproves a conjecture of Bhyravarapu, Hartmann, Hoang, Kalyanasundaram and Reddy that K(n, κ) needs κ + 1 colors for every n ≥ 2κ + 1.

## Main results

- The conjecture fails at (n, κ) = (5,2), (6,2), (7,3), (8,3), (9,3), (10,3) and (11,3). The smallest counterexample is the Petersen graph K(5,2), which needs 2 colors, not 3.
- For κ = 2 the exact value is 2 when n = 5 or 6, and 3 for every n ≥ 7.
- One color is never enough when n ≥ 2κ + 1, so every such Kneser graph needs at least 2.

Full statements and proofs are in `paper/`. The table of values and the SAT method are in `RESULTS.md`.

## Repository contents

| Folder | Contents |
| --- | --- |
| `paper/` | LaTeX source and compiled PDF of the write-up |
| `counterexamples/` | PDFs and documents showing each counterexample coloring |
| `code/` | SAT encoding, solver scripts and the coloring checker |
| `certificates/` | Saved colorings, plus CNF formulas and DRAT proofs for the cases with no valid coloring |

## Running the code

Requires Python 3 and PySAT (`pip install python-sat`). Checking the DRAT proofs requires [drat-trim](https://github.com/marijnheule/drat-trim).

```bash
# arguments: n, κ, number of colors
python code/sat.py 5 2 2    # finds a 2-coloring of K(5,2)
python code/sat.py 7 2 2    # reports that K(7,2) has no 2-coloring
python code/reproduce.py    # re-checks every result
```

## Reference

S. Bhyravarapu, T. A. Hartmann, H. P. Hoang, S. Kalyanasundaram, I. V. Reddy. *Conflict-Free Coloring: Graphs of Bounded Clique-Width and Intersection Graphs.* [arXiv:2105.08693](https://arxiv.org/abs/2105.08693). The conjecture is stated in Section 8.
