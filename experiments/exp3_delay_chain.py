"""
Experiment 3 — Delay-chain propagation.

A three-cell logic path  INV_X1 -> AND2_X1 -> DFF_X1  is analyzed by chaining
the bilinear engine: each stage's output slew becomes the next stage's input
slew, and each stage's load is the input capacitance of the downstream cell.
The chain is swept over a grid of (initial input slew, final load) values to
characterize how the total path delay scales with operating conditions.

A simple sanity check is included: the chain reproduces (exactly) the single
point reported in the project README — initial slew = 40 ps, final load = 0 fF.
"""
from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt

from common import (LIB_PATH, RESULTS_DIR, FIGURES_DIR, save_json, save_csv,
                    banner)
from library.library import Library


CHAIN = ["INV_X1", "AND2_X1", "DFF_X1"]
DOWNSTREAM_PIN = {"AND2_X1": "A1", "DFF_X1": "CK"}


def propagate(lib, initial_slew, final_load):
    """Run the chain and return per-stage and total results."""
    cells = [lib.findCell(name) for name in CHAIN]
    inv, and2, dff = cells

    # cada etapa ve como carga la capacitancia de la entrada de la siguiente
    loads = [
        and2.input_pins[DOWNSTREAM_PIN["AND2_X1"]].capacitance,
        dff.input_pins[DOWNSTREAM_PIN["DFF_X1"]].capacitance,
        final_load,
    ]

    stages = []
    s_in = initial_slew
    total_tp = 0.0

    for cell, c_load in zip(cells, loads):
        cell.compute(input_slew=s_in, output_load=c_load)
        stages.append({
            "cell": cell.name,
            "arc": f"{cell.worst_arc.related_pin}->{cell.worst_arc.output_pin}",
            "input_slew_ns": s_in,
            "output_load_fF": c_load,
            "tp_ns": cell.tp,
            "slew_out_ns": cell.slew_out,
        })
        total_tp += cell.tp
        s_in = cell.slew_out

    return {
        "initial_slew_ns": initial_slew,
        "final_load_fF": final_load,
        "stages": stages,
        "total_tp_ns": total_tp,
    }


def run():
    banner("EXPERIMENT 3 — Delay-chain propagation (INV -> AND2 -> DFF)")
    lib = Library(str(LIB_PATH))

    # ── (a) Punto de referencia del README ─────────────────────────────────
    ref = propagate(lib, initial_slew=0.040, final_load=0.0)
    print(f"  Reference point  initial_slew=40 ps, final_load=0 fF")
    for st in ref["stages"]:
        print(f"    {st['cell']:8s}  arc={st['arc']:8s}  "
              f"slew_in={st['input_slew_ns']*1000:6.2f} ps  "
              f"C_L={st['output_load_fF']:6.3f} fF  "
              f"tp={st['tp_ns']*1000:7.3f} ps  "
              f"slew_out={st['slew_out_ns']*1000:6.2f} ps")
    print(f"    TOTAL tp = {ref['total_tp_ns']*1000:.3f} ps "
          f"(README quotes 135.016 ps)")
    readme_match = abs(ref["total_tp_ns"] - 0.135016) < 1e-5
    print(f"    Reproduces README: {readme_match}")

    slews = np.linspace(0.005, 0.150, 12)
    loads = np.linspace(0.0,   30.0,  12)
    Z = np.empty((len(slews), len(loads)))
    rows = []
    for i, s in enumerate(slews):
        for j, c in enumerate(loads):
            r = propagate(lib, s, c)
            Z[i, j] = r["total_tp_ns"]
            rows.append({
                "initial_slew_ns": s,
                "final_load_fF": c,
                "total_tp_ns": r["total_tp_ns"],
                "inv_tp_ns": r["stages"][0]["tp_ns"],
                "and2_tp_ns": r["stages"][1]["tp_ns"],
                "dff_tp_ns": r["stages"][2]["tp_ns"],
                "final_slew_ns": r["stages"][-1]["slew_out_ns"],
            })

    save_json({
        "chain": CHAIN,
        "reference_point": ref,
        "reference_matches_readme": readme_match,
        "sweep": {
            "slews_ns": slews.tolist(),
            "loads_fF": loads.tolist(),
            "total_tp_ns": Z.tolist(),
        },
    }, "exp3_summary")
    save_csv(rows, "exp3_sweep")


    print(f"\n  Sweep over ({len(slews)} slews x {len(loads)} loads) = "
          f"{Z.size} operating points")
    print(f"    total tp min  = {Z.min()*1000:.2f} ps")
    print(f"    total tp max  = {Z.max()*1000:.2f} ps")
    print(f"    total tp mean = {Z.mean()*1000:.2f} ps")

    fig, ax = plt.subplots(figsize=(7.5, 5.0))
    im = ax.imshow(Z * 1000, origin="lower", aspect="auto",
                   extent=[loads[0], loads[-1],
                           slews[0] * 1000, slews[-1] * 1000],
                   cmap="viridis")
    cs = ax.contour(loads, slews * 1000, Z * 1000, levels=8,
                    colors="white", linewidths=0.6, alpha=0.7)
    ax.clabel(cs, inline=True, fontsize=7, fmt="%.0f")
    ax.set_xlabel("Final load $C_L$ (fF)")
    ax.set_ylabel("Initial input slew (ps)")
    ax.set_title("Exp. 3 — Total path delay (ps) for INV → AND2 → DFF")
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Total $t_p$ (ps)")
    ax.scatter([0.0], [40.0], marker="*", s=140, color="#ffeb3b",
               edgecolors="black", linewidths=0.8, zorder=3,
               label=f"Reference: {ref['total_tp_ns']*1000:.1f} ps")
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "exp3_total_delay_heatmap.png", dpi=160)
    plt.close(fig)

    fig2, ax2 = plt.subplots(figsize=(6.5, 4.0))
    stage_names = [s["cell"] for s in ref["stages"]]
    tps_ps = [s["tp_ns"] * 1000 for s in ref["stages"]]
    bars = ax2.bar(stage_names, tps_ps,
                   color=["#3a6ea5", "#5a8e5a", "#b53737"],
                   edgecolor="black")
    for b, v in zip(bars, tps_ps):
        ax2.text(b.get_x() + b.get_width() / 2, v + 1.5,
                 f"{v:.2f} ps", ha="center", fontsize=9)
    ax2.set_ylabel("Stage delay $t_p$ (ps)")
    ax2.set_title("Exp. 3 — Per-stage delay at reference point\n"
                  f"(initial slew = 40 ps, final load = 0 fF) — "
                  f"total = {ref['total_tp_ns']*1000:.2f} ps")
    ax2.grid(True, alpha=0.3, axis="y")
    fig2.tight_layout()
    fig2.savefig(FIGURES_DIR / "exp3_per_stage_bar.png", dpi=160)
    plt.close(fig2)

    print(f"\n  results: exp3_summary.json, exp3_sweep.csv")
    print(f"  figures: exp3_total_delay_heatmap.png, exp3_per_stage_bar.png")
    return ref


if __name__ == "__main__":
    run()
