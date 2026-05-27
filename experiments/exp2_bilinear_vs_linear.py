"""
Experiment 2 — Bilinear (2D) vs collapsed-dimension (1D) interpolation.

Compares two flavors of 1D approximation against the bilinear reference, on
n=100 log-uniform (input_slew, output_load) samples per LUT (drawn strictly
inside the LUT range, no extrapolation):

  1D-nearest : interpolates only along the load axis, on the LUT row whose
               characterized slew is closest to the query slew (a generous
               1D baseline — it still "uses" the slew dimension as a
               row selector).
  1D-row0    : interpolates only along the load axis, always on row 0
               (minimum characterized slew). This corresponds to a naive
               engine that ignores the slew dimension entirely.

Both quantify what is lost by collapsing the slew dimension. The first is
a lower bound on the error of any 1D scheme; the second is its upper bound.
The paper's quoted ~19.8% / ~45.2% figures match the row-0 baseline, which
is the worst-case 1D scheme and the one that motivates 2D as a functional
requirement.
"""
from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt

from common import (LIB_PATH, RESULTS_DIR, FIGURES_DIR, TARGET_CELLS,
                    LUT_KINDS, SEED, save_json, save_csv, banner)
from library.library import Library


N_SAMPLES = 100
EPS = 1e-9


def log_uniform_in(lo, hi, n, rng):
    return np.exp(rng.uniform(np.log(lo + EPS), np.log(hi - EPS), size=n))


def _stats(arr):
    return {
        "n": int(arr.size),
        "mean_pct": float(arr.mean() * 100.0),
        "median_pct": float(np.median(arr) * 100.0),
        "p95_pct": float(np.quantile(arr, 0.95) * 100.0),
        "max_pct": float(arr.max() * 100.0),
    }


def run():
    banner("EXPERIMENT 2 — Bilinear vs collapsed-dimension interpolation")
    rng = np.random.default_rng(SEED)
    lib = Library(str(LIB_PATH))

    rows = []
    per_cell = {}

    for cell_name in TARGET_CELLS:
        cell = lib.findCell(cell_name)
        nearest_errs = []
        row0_errs = []

        for arc in cell.timing_arcs:
            arc_label = f"{arc.related_pin}->{arc.output_pin}"

            for lut_name in LUT_KINDS:
                lut = arc.luts[lut_name]
                s_lo, s_hi = lut.index_1[0], lut.index_1[-1]
                c_lo, c_hi = lut.index_2[0], lut.index_2[-1]

                slews = log_uniform_in(s_lo, s_hi, N_SAMPLES, rng)
                loads = log_uniform_in(c_lo, c_hi, N_SAMPLES, rng)

                for s, c in zip(slews, loads):
                    v_2d = lut.lookup(s, c)["value"]
                    v_near = lut.lookup_1d(c, input_slew=s)["value"]
                    v_row0 = lut.lookup_1d_fixed_row(c, row=0)["value"]

                    rel_near = abs(v_near - v_2d) / abs(v_2d) if v_2d != 0 else 0.0
                    rel_row0 = abs(v_row0 - v_2d) / abs(v_2d) if v_2d != 0 else 0.0

                    nearest_errs.append(rel_near)
                    row0_errs.append(rel_row0)
                    rows.append({
                        "cell": cell_name,
                        "arc": arc_label,
                        "lut": lut_name,
                        "input_slew_ns": s,
                        "output_load_fF": c,
                        "bilinear": v_2d,
                        "linear_1d_nearest": v_near,
                        "linear_1d_row0": v_row0,
                        "rel_error_nearest": rel_near,
                        "rel_error_row0": rel_row0,
                    })

        per_cell[cell_name] = {
            "n_samples": len(nearest_errs),
            "nearest_row": _stats(np.asarray(nearest_errs)),
            "row0":        _stats(np.asarray(row0_errs)),
        }
        sn = per_cell[cell_name]["nearest_row"]
        s0 = per_cell[cell_name]["row0"]
        print(f"  {cell_name:10s}  "
              f"nearest: mean={sn['mean_pct']:6.2f}%  max={sn['max_pct']:6.2f}%  | "
              f"row0:    mean={s0['mean_pct']:6.2f}%  max={s0['max_pct']:6.2f}%")

    all_near = np.asarray([r["rel_error_nearest"] for r in rows])
    all_row0 = np.asarray([r["rel_error_row0"] for r in rows])
    overall = {
        "n": int(all_near.size),
        "nearest_row": _stats(all_near),
        "row0":        _stats(all_row0),
    }
    print(f"\n  OVERALL    "
          f"nearest: mean={overall['nearest_row']['mean_pct']:.2f}%  "
          f"max={overall['nearest_row']['max_pct']:.2f}%  | "
          f"row0:    mean={overall['row0']['mean_pct']:.2f}%  "
          f"max={overall['row0']['max_pct']:.2f}%")

    by_lut = {}
    for kind in LUT_KINDS:
        sub_n = np.asarray([r["rel_error_nearest"] for r in rows if r["lut"] == kind])
        sub_0 = np.asarray([r["rel_error_row0"]    for r in rows if r["lut"] == kind])
        by_lut[kind] = {"nearest_row": _stats(sub_n), "row0": _stats(sub_0)}

    save_json({"per_cell": per_cell, "overall": overall, "by_lut": by_lut,
               "n_samples_per_lut": N_SAMPLES},
              "exp2_summary")
    save_csv(rows, "exp2_bilinear_vs_1d")

    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    positions_near = np.arange(len(TARGET_CELLS)) * 2.5
    positions_row0 = positions_near + 0.9

    data_near = [[r["rel_error_nearest"] * 100 for r in rows if r["cell"] == c]
                 for c in TARGET_CELLS]
    data_row0 = [[r["rel_error_row0"] * 100 for r in rows if r["cell"] == c]
                 for c in TARGET_CELLS]

    bp1 = ax.boxplot(data_near, positions=positions_near, widths=0.75,
                     patch_artist=True, showfliers=False)
    bp2 = ax.boxplot(data_row0, positions=positions_row0, widths=0.75,
                     patch_artist=True, showfliers=False)
    for p in bp1["boxes"]: p.set_facecolor("#a8c8e6"); p.set_edgecolor("black")
    for p in bp2["boxes"]: p.set_facecolor("#e6a8a8"); p.set_edgecolor("black")
    for m in bp1["medians"] + bp2["medians"]: m.set_color("black")

    ax.set_xticks(positions_near + 0.45)
    ax.set_xticklabels(TARGET_CELLS)
    ax.set_ylabel("Relative error vs bilinear (%)")
    ax.set_title("Exp. 2 — Cost of collapsing the slew dimension\n"
                 f"({N_SAMPLES} log-uniform samples per LUT)")
    ax.grid(True, alpha=0.3, axis="y")

    from matplotlib.patches import Patch
    ax.legend(handles=[
        Patch(facecolor="#a8c8e6", edgecolor="black", label="1D nearest-row"),
        Patch(facecolor="#e6a8a8", edgecolor="black", label="1D row-0 (worst-case 1D)"),
    ], loc="upper right")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "exp2_boxplot.png", dpi=160)
    plt.close(fig)

    fig2, ax2 = plt.subplots(figsize=(7.6, 4.3))
    slews = np.array([r["input_slew_ns"] for r in rows])
    rels = np.array([r["rel_error_row0"] * 100 for r in rows])
    ax2.scatter(slews, rels, s=8, alpha=0.35, color="#b53737", edgecolors="none")
    ax2.set_xscale("log")
    ax2.set_xlabel("Query input slew (ns)")
    ax2.set_ylabel("Relative error of 1D row-0 vs bilinear (%)")
    ax2.set_title("Exp. 2 — 1D row-0 error grows with separation\n"
                  "from the minimum characterized slew")
    ax2.grid(True, alpha=0.3)
    fig2.tight_layout()
    fig2.savefig(FIGURES_DIR / "exp2_error_vs_slew.png", dpi=160)
    plt.close(fig2)

    print(f"\n  results: exp2_summary.json, exp2_bilinear_vs_1d.csv")
    print(f"  figures: exp2_boxplot.png, exp2_error_vs_slew.png")
    return overall


if __name__ == "__main__":
    run()
