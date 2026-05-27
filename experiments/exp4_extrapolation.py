"""
Experiment 4 — Extrapolation behaviour.

For the INV_X1 cell (arc A -> ZN, cell_rise LUT), the output load is swept
from the LUT minimum (~0.37 fF) to 2× the LUT maximum (~121 fF) at a fixed
input slew of 40 ps. Inside the LUT range the bilinear engine produces a
fully characterized value. Outside the range, the engine applies constant-edge
extension (clamping): query coordinates are pinned to the nearest LUT boundary,
so the reported value stops changing.

We compare the clamped estimate to a monotone PCHIP extrapolation fitted to
the last four in-range characterized points (along the load axis, at the
nearest characterized slew row). PCHIP is monotone and shape-preserving, so
it gives a physically plausible reference for how the LUT *trend* would
continue beyond its tabulated range. The gap between the two quantifies the
systematic underestimation introduced by constant-edge extension.
"""
from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import PchipInterpolator

from common import (LIB_PATH, RESULTS_DIR, FIGURES_DIR, save_json, save_csv,
                    banner)
from library.library import Library


def run():
    banner("EXPERIMENT 4 — Extrapolation behaviour (constant-edge vs PCHIP)")
    lib = Library(str(LIB_PATH))
    cell = lib.findCell("INV_X1")
    arc = cell.timing_arcs[0]
    lut = arc.luts["cell_rise"]

    input_slew = 0.040
    load_min = lut.index_2[0]
    load_max = lut.index_2[-1]

    diffs = [abs(s - input_slew) for s in lut.index_1]
    nearest_row = diffs.index(min(diffs))
    row_loads = np.asarray(lut.index_2)
    row_vals  = np.asarray(lut.values[nearest_row])

    tail_x = row_loads[-4:]
    tail_y = row_vals[-4:]
    pchip = PchipInterpolator(tail_x, tail_y, extrapolate=True)

    loads_in  = np.linspace(load_min, load_max,             80)
    loads_out = np.linspace(load_max, 2 * load_max,         60)[1:]   # sin duplicar load_max
    loads = np.concatenate([loads_in, loads_out])

    rows = []
    clamped_vals = []
    pchip_vals = []
    for c in loads:
        res = lut.lookup(input_slew, c)
        v_clamped = res["value"]

        if c <= load_max:
            v_pchip = v_clamped
        else:
            v_pchip = float(pchip(c))

        out_of_range = c > load_max
        if out_of_range and v_pchip != 0:
            under_pct = (v_pchip - v_clamped) / v_pchip * 100.0
        else:
            under_pct = 0.0

        rows.append({
            "load_fF": float(c),
            "value_bilinear_clamped_ns": float(v_clamped),
            "value_pchip_ns": float(v_pchip),
            "out_of_range": out_of_range,
            "out_of_range_flag": bool(res["output_load_clamped"]),
            "underestimation_pct": float(under_pct),
        })
        clamped_vals.append(v_clamped)
        pchip_vals.append(v_pchip)

    clamped_vals = np.asarray(clamped_vals)
    pchip_vals   = np.asarray(pchip_vals)

    # subestimación a 1.5x y 2x del LUT max
    def under_at(factor):
        target = factor * load_max
        idx = int(np.argmin(np.abs(loads - target)))
        cl, pc = clamped_vals[idx], pchip_vals[idx]
        pct = (pc - cl) / pc * 100.0 if pc != 0 else 0.0
        return loads[idx], cl, pc, pct

    print(f"  Cell:  INV_X1   Arc: {arc.related_pin}->{arc.output_pin}   "
          f"LUT: cell_rise")
    print(f"  Fixed input_slew = {input_slew*1000:.1f} ps   "
          f"(nearest LUT row index = {nearest_row}, "
          f"slew_row = {lut.index_1[nearest_row]*1000:.2f} ps)")
    print(f"  LUT load range = [{load_min:.3f}, {load_max:.3f}] fF")
    print(f"  Sweep range    = [{loads[0]:.3f}, {loads[-1]:.3f}] fF "
          f"({len(loads_in)} in-range + {len(loads_out)} out-of-range)\n")

    L, cl, pc, pct = under_at(1.0)
    print(f"  At C_L = {L:6.2f} fF (1.0x max):  clamped={cl*1000:.2f} ps  "
          f"pchip={pc*1000:.2f} ps  diff={pct:+5.2f}%")
    L, cl, pc, pct = under_at(1.5)
    print(f"  At C_L = {L:6.2f} fF (1.5x max):  clamped={cl*1000:.2f} ps  "
          f"pchip={pc*1000:.2f} ps  underestimation={pct:5.2f}%")
    L, cl, pc, pct = under_at(2.0)
    print(f"  At C_L = {L:6.2f} fF (2.0x max):  clamped={cl*1000:.2f} ps  "
          f"pchip={pc*1000:.2f} ps  underestimation={pct:5.2f}%")

    summary = {
        "cell": "INV_X1",
        "arc": f"{arc.related_pin}->{arc.output_pin}",
        "lut": "cell_rise",
        "input_slew_ns": input_slew,
        "nearest_row_index": nearest_row,
        "nearest_row_slew_ns": lut.index_1[nearest_row],
        "lut_load_min_fF": load_min,
        "lut_load_max_fF": load_max,
        "underestimation_pct_at_1_5x": under_at(1.5)[3],
        "underestimation_pct_at_2_0x": under_at(2.0)[3],
        "max_clamped_value_ns": float(lut.values[nearest_row][-1]),
        "tail_anchor_loads_fF": tail_x.tolist(),
        "tail_anchor_values_ns": tail_y.tolist(),
    }
    save_json(summary, "exp4_summary")
    save_csv(rows, "exp4_extrapolation_sweep")

    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    ax.axvspan(load_max, loads[-1], alpha=0.10, color="red",
               label="Out-of-LUT range")
    ax.plot(loads, clamped_vals * 1000, color="#3a6ea5", linewidth=1.6,
            label="LibertyScope (bilinear + constant-edge clamp)")
    ax.plot(loads[loads > load_max], pchip_vals[loads > load_max] * 1000,
            "--", color="#b53737", linewidth=1.4,
            label="Monotone PCHIP extrapolation (last 4 points)")
    ax.scatter(row_loads, row_vals * 1000, color="black", s=22, zorder=3,
               label="LUT characterized points (row $t_{in}$ ≈ 40 ps)")
    ax.axvline(load_max, color="grey", linestyle=":", linewidth=0.8)
    ax.set_xlabel(r"Output load $C_L$ (fF)")
    ax.set_ylabel("$cell\\_rise$ value (ps)")
    ax.set_title("Exp. 4 — Constant-edge extension vs monotone extrapolation\n"
                 "INV_X1, cell_rise, input slew = 40 ps")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "exp4_extrapolation.png", dpi=160)
    plt.close(fig)

    print(f"\n  results: exp4_summary.json, exp4_extrapolation_sweep.csv")
    print(f"  figure:  exp4_extrapolation.png")
    return summary


if __name__ == "__main__":
    run()
