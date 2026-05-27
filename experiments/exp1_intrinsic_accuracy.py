"""
Experiment 1 — Numerical stability near LUT nodes, edges, and the clamp
transition.

The bilinear engine has three regions where naive implementations commonly
break: (1) exact LUT nodes (off-by-one errors in bisect indexing produce
"jumps" when the query coordinate equals a tabulated index); (2) LUT edges
(the four sides of the rectangle, where one fractional coordinate u or v is
0 or 1 by construction); and (3) the clamp boundary (the transition between
strict interpolation just inside the LUT and constant-edge extension just
outside). A correct NLDM engine must be continuous across all three.

This experiment quantifies the discontinuity at each region with three
sub-tests. Each sub-test reports a maximum and mean jump (absolute and
relative). A correct engine produces O(eps) jumps that scale linearly with
the perturbation eps; any non-trivial residual at eps -> 0 would signal a
bug in index handling, clamping logic, or floating-point comparison.

Coverage: all 28 LUTs in the target subset (4 cells x ~7 arcs x 4 LUTs each).
"""
from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt

from common import (LIB_PATH, RESULTS_DIR, FIGURES_DIR, TARGET_CELLS,
                    LUT_KINDS, save_json, save_csv, banner)
from library.library import Library


# perturbaciones relativas a probar
EPSILONS = [1e-3, 1e-6, 1e-9, 1e-12]


def _iter_luts(lib):
    """Itera por todas las LUTs de las celdas objetivo."""
    for cell_name in TARGET_CELLS:
        cell = lib.findCell(cell_name)
        for arc in cell.timing_arcs:
            arc_label = f"{arc.related_pin}->{arc.output_pin}"
            for lut_name in LUT_KINDS:
                yield cell_name, arc_label, lut_name, arc.luts[lut_name]


# ──────────────────────────────────────────────────────────────────────────
# Sub-test A — Continuidad en nodos interiores
# ──────────────────────────────────────────────────────────────────────────
def subtest_continuity_at_nodes(lib, rows_out):
    """For every interior node (i,j) and every eps, perturb both axes by
    +eps*range and check that lookup(node+eps) is within O(eps) of the
    tabulated value. A bilinear engine must satisfy this exactly."""
    per_eps = {e: [] for e in EPSILONS}

    for cell, arc, lut_name, lut in _iter_luts(lib):
        idx1, idx2 = lut.index_1, lut.index_2
        r1 = idx1[-1] - idx1[0]
        r2 = idx2[-1] - idx2[0]

        # nodos interiores: evitar el último nodo donde "+eps" empuja al clamp
        for i in range(len(idx1) - 1):
            for j in range(len(idx2) - 1):
                expected = lut.values[i][j]
                if expected == 0:
                    continue

                for eps in EPSILONS:
                    dx, dy = eps * r1, eps * r2
                    v = lut.lookup(idx1[i] + dx, idx2[j] + dy)["value"]
                    abs_jump = abs(v - expected)
                    rel_jump = abs_jump / abs(expected)
                    per_eps[eps].append(rel_jump)
                    rows_out.append({
                        "subtest": "A_continuity_at_nodes",
                        "cell": cell, "arc": arc, "lut": lut_name,
                        "i": i, "j": j, "eps": eps,
                        "expected": expected, "got": v,
                        "abs_jump": abs_jump, "rel_jump": rel_jump,
                    })

    summary = {}
    for eps, errs in per_eps.items():
        arr = np.asarray(errs)
        summary[f"eps_{eps:.0e}"] = {
            "n": int(arr.size),
            "max_rel_jump": float(arr.max()),
            "mean_rel_jump": float(arr.mean()),
            "p99_rel_jump": float(np.quantile(arr, 0.99)),
        }
    return summary, per_eps


# ──────────────────────────────────────────────────────────────────────────
# Sub-test B — Coherencia en los bordes del LUT
# ──────────────────────────────────────────────────────────────────────────
def subtest_continuity_at_edges(lib, rows_out):
    """On each of the 4 LUT sides (e.g. x = idx1[0] fixed, y varying along
    idx2), bilinear interpolation must coincide with 1D linear interpolation
    along that side. This catches bugs that only show up when u=0, u=1, v=0,
    or v=1 (sides of the bilinear rectangle)."""
    # tomamos una rejilla densa de puntos a lo largo de cada lado
    N = 50
    per_side = {"x=idx1[0]": [], "x=idx1[-1]": [],
                "y=idx2[0]": [], "y=idx2[-1]": []}

    for cell, arc, lut_name, lut in _iter_luts(lib):
        idx1, idx2 = lut.index_1, lut.index_2

        sides = [
            ("x=idx1[0]",  idx1[0],
                np.linspace(idx2[0], idx2[-1], N), True),
            ("x=idx1[-1]", idx1[-1],
                np.linspace(idx2[0], idx2[-1], N), True),
            ("y=idx2[0]",  idx2[0],
                np.linspace(idx1[0], idx1[-1], N), False),
            ("y=idx2[-1]", idx2[-1],
                np.linspace(idx1[0], idx1[-1], N), False),
        ]

        for side_name, fixed_val, varying_vals, fixed_is_x in sides:
            # esperado: interpolación lineal 1D a lo largo del lado tabulado
            if fixed_is_x:
                row_idx = (0 if fixed_val == idx1[0] else len(idx1) - 1)
                tab_axis = idx2
                tab_vals = lut.values[row_idx]
            else:
                col_idx = (0 if fixed_val == idx2[0] else len(idx2) - 1)
                tab_axis = idx1
                tab_vals = [lut.values[i][col_idx] for i in range(len(idx1))]

            for q in varying_vals:
                # interp 1D lineal de referencia a lo largo del lado
                expected = float(np.interp(q, tab_axis, tab_vals))
                # consulta bilineal en (x_fixed, q) o (q, y_fixed)
                if fixed_is_x:
                    got = lut.lookup(fixed_val, q)["value"]
                else:
                    got = lut.lookup(q, fixed_val)["value"]
                if expected != 0:
                    rel = abs(got - expected) / abs(expected)
                else:
                    rel = 0.0
                per_side[side_name].append(rel)
                rows_out.append({
                    "subtest": "B_continuity_at_edges",
                    "cell": cell, "arc": arc, "lut": lut_name,
                    "side": side_name, "q": float(q),
                    "expected": expected, "got": got,
                    "rel_jump": rel,
                })

    summary = {}
    for side, errs in per_side.items():
        arr = np.asarray(errs)
        summary[side] = {
            "n": int(arr.size),
            "max_rel_jump": float(arr.max()),
            "mean_rel_jump": float(arr.mean()),
        }
    return summary, per_side


# ──────────────────────────────────────────────────────────────────────────
# Sub-test C — Coherencia en la transición clamp / no-clamp
# ──────────────────────────────────────────────────────────────────────────
def subtest_clamp_transition(lib, rows_out):
    """At every LUT corner (left/right of each axis), compare lookup at
    (border - eps) vs (border + eps). Inside the LUT the engine interpolates;
    outside it clamps to the border value. Both should give nearly the same
    number, with discontinuity only of order O(eps) on the inside side
    (and exactly zero on the outside, since clamping pins to the border)."""
    per_eps_per_corner = {e: [] for e in EPSILONS}

    for cell, arc, lut_name, lut in _iter_luts(lib):
        idx1, idx2 = lut.index_1, lut.index_2
        r1 = idx1[-1] - idx1[0]
        r2 = idx2[-1] - idx2[0]

        # 4 bordes del rectángulo
        borders = [
            ("slew_low",  idx1[0],  r1, True),
            ("slew_high", idx1[-1], r1, True),
            ("load_low",  idx2[0],  r2, False),
            ("load_high", idx2[-1], r2, False),
        ]
        # punto medio del eje perpendicular para fijar la otra coordenada
        s_mid = 0.5 * (idx1[0] + idx1[-1])
        c_mid = 0.5 * (idx2[0] + idx2[-1])

        for border_name, b, span, is_slew in borders:
            for eps in EPSILONS:
                d = eps * span
                if is_slew:
                    v_in  = lut.lookup(b - d, c_mid)["value"]
                    v_out = lut.lookup(b + d, c_mid)["value"]
                else:
                    v_in  = lut.lookup(s_mid, b - d)["value"]
                    v_out = lut.lookup(s_mid, b + d)["value"]
                ref = max(abs(v_in), abs(v_out))
                rel_jump = abs(v_in - v_out) / ref if ref > 0 else 0.0
                per_eps_per_corner[eps].append(rel_jump)
                rows_out.append({
                    "subtest": "C_clamp_transition",
                    "cell": cell, "arc": arc, "lut": lut_name,
                    "border": border_name, "eps": eps,
                    "v_inside": v_in, "v_outside": v_out,
                    "rel_jump": rel_jump,
                })

    summary = {}
    for eps, errs in per_eps_per_corner.items():
        arr = np.asarray(errs)
        summary[f"eps_{eps:.0e}"] = {
            "n": int(arr.size),
            "max_rel_jump": float(arr.max()),
            "mean_rel_jump": float(arr.mean()),
        }
    return summary, per_eps_per_corner


def run():
    banner("EXPERIMENT 1 — Numerical stability near nodes, edges, "
           "and clamp transition")
    lib = Library(str(LIB_PATH))
    rows = []

    print("\n[A] Continuity at LUT nodes (interior)")
    sumA, per_eps_A = subtest_continuity_at_nodes(lib, rows)
    print(f"    {'eps':>8s}  {'n':>5s}  {'max rel jump':>14s}  "
          f"{'mean rel jump':>14s}")
    for eps in EPSILONS:
        s = sumA[f"eps_{eps:.0e}"]
        print(f"    {eps:8.0e}  {s['n']:5d}  {s['max_rel_jump']:14.3e}  "
              f"{s['mean_rel_jump']:14.3e}")

    eps_arr = np.array(EPSILONS)
    max_arr = np.array([sumA[f"eps_{e:.0e}"]["max_rel_jump"] for e in EPSILONS])
    # evita log(0)
    nz = max_arr > 0
    if nz.sum() >= 2:
        slope = np.polyfit(np.log10(eps_arr[nz]), np.log10(max_arr[nz]), 1)[0]
    else:
        slope = float("nan")
    print(f"    Convergence rate (log-log slope): {slope:.3f}   "
          f"(ideal ~ 1.0 for bilinear)")

    print("\n[B] Coherence along LUT edges (4 sides per LUT)")
    sumB, per_side_B = subtest_continuity_at_edges(lib, rows)
    print(f"    {'side':>14s}  {'n':>5s}  {'max rel jump':>14s}  "
          f"{'mean rel jump':>14s}")
    for side, s in sumB.items():
        print(f"    {side:>14s}  {s['n']:5d}  {s['max_rel_jump']:14.3e}  "
              f"{s['mean_rel_jump']:14.3e}")

    print("\n[C] Continuity across the clamp boundary (4 borders per LUT)")
    sumC, per_eps_C = subtest_clamp_transition(lib, rows)
    print(f"    {'eps':>8s}  {'n':>5s}  {'max rel jump':>14s}  "
          f"{'mean rel jump':>14s}")
    for eps in EPSILONS:
        s = sumC[f"eps_{eps:.0e}"]
        print(f"    {eps:8.0e}  {s['n']:5d}  {s['max_rel_jump']:14.3e}  "
              f"{s['mean_rel_jump']:14.3e}")

    max_arr_C = np.array([sumC[f"eps_{e:.0e}"]["max_rel_jump"]
                          for e in EPSILONS])
    nz = max_arr_C > 0
    if nz.sum() >= 2:
        slope_C = np.polyfit(np.log10(eps_arr[nz]),
                             np.log10(max_arr_C[nz]), 1)[0]
    else:
        slope_C = float("nan")
    print(f"    Convergence rate (log-log slope): {slope_C:.3f}   "
          f"(ideal ~ 1.0)")

    save_json({
        "subtest_A_continuity_at_nodes": sumA,
        "subtest_A_log_log_slope": float(slope),
        "subtest_B_edges": sumB,
        "subtest_C_clamp_transition": sumC,
        "subtest_C_log_log_slope": float(slope_C),
        "epsilons": EPSILONS,
    }, "exp1_summary")
    rows_by_subtest = {}
    for r in rows:
        rows_by_subtest.setdefault(r["subtest"], []).append(r)
    for subtest_name, sub_rows in rows_by_subtest.items():
        save_csv(sub_rows, f"exp1_{subtest_name}")

    fig, ax = plt.subplots(figsize=(7.0, 4.6))
    max_A = np.array([sumA[f"eps_{e:.0e}"]["max_rel_jump"] for e in EPSILONS])
    mean_A = np.array([sumA[f"eps_{e:.0e}"]["mean_rel_jump"] for e in EPSILONS])
    max_C = np.array([sumC[f"eps_{e:.0e}"]["max_rel_jump"] for e in EPSILONS])
    mean_C = np.array([sumC[f"eps_{e:.0e}"]["mean_rel_jump"] for e in EPSILONS])

    ax.loglog(eps_arr, max_A,  "o-",  color="#3a6ea5", label="[A] nodes — max")
    ax.loglog(eps_arr, mean_A, "o--", color="#3a6ea5", alpha=0.55,
              label="[A] nodes — mean")
    ax.loglog(eps_arr, max_C,  "s-",  color="#b53737", label="[C] clamp — max")
    ax.loglog(eps_arr, mean_C, "s--", color="#b53737", alpha=0.55,
              label="[C] clamp — mean")
    ref_anchor = max_A[max_A > 0][0] if (max_A > 0).any() else 1.0
    ref_eps0   = eps_arr[max_A > 0][0] if (max_A > 0).any() else eps_arr[0]
    ref_line = ref_anchor * (eps_arr / ref_eps0)
    ax.loglog(eps_arr, ref_line, ":", color="grey",
              label=r"reference $\mathcal{O}(\varepsilon)$")
    ax.set_xlabel(r"Relative perturbation $\varepsilon$")
    ax.set_ylabel("Relative jump")
    ax.set_title("Exp. 1 — Convergence of the bilinear engine\n"
                 "(interior nodes and clamp boundary)")
    ax.grid(True, which="both", alpha=0.3)
    ax.invert_xaxis()  # eps grande a la izquierda, eps -> 0 a la derecha
    ax.legend(fontsize=8.5, loc="lower left")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "exp1_convergence.png", dpi=160)
    plt.close(fig)

    fig2, ax2 = plt.subplots(figsize=(7.0, 3.8))
    sides = list(sumB.keys())
    max_vals = [sumB[s]["max_rel_jump"] for s in sides]
    mean_vals = [sumB[s]["mean_rel_jump"] for s in sides]
    x = np.arange(len(sides))
    w = 0.36
    ax2.bar(x - w/2, max_vals,  w, color="#3a6ea5", edgecolor="black",
            label="max")
    ax2.bar(x + w/2, mean_vals, w, color="#a8c8e6", edgecolor="black",
            label="mean")
    ax2.set_xticks(x)
    ax2.set_xticklabels(sides)
    ax2.set_yscale("log")
    ax2.set_ylabel("Relative jump (1D linear reference)")
    ax2.set_title("Exp. 1 [B] — Bilinear vs 1D linear on each LUT side")
    ax2.grid(True, alpha=0.3, axis="y", which="both")
    ax2.legend()
    fig2.tight_layout()
    fig2.savefig(FIGURES_DIR / "exp1_edges.png", dpi=160)
    plt.close(fig2)

    print(f"\n  results: exp1_summary.json, exp1_A_*.csv, exp1_B_*.csv, exp1_C_*.csv")
    print(f"  figures: exp1_convergence.png, exp1_edges.png")
    return {"A": sumA, "B": sumB, "C": sumC,
            "slope_A": slope, "slope_C": slope_C}


if __name__ == "__main__":
    run()