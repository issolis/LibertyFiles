
from __future__ import annotations
import os
import sys
import json
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LIB_PATH = ROOT / "NangateOpenCellLibrary_typical.lib"
RESULTS_DIR = ROOT / "experiments" / "results"
FIGURES_DIR = ROOT / "experiments" / "figures"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

TARGET_CELLS = ["INV_X1", "AND2_X1", "NAND2_X1", "DFF_X1"]
LUT_KINDS = ["cell_rise", "cell_fall", "rise_transition", "fall_transition"]
SEED = 42


def save_json(data, name: str):
    """Guarda dict/list como JSON en results/."""
    path = RESULTS_DIR / f"{name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=_json_default)
    return path


def save_csv(rows, name: str, fieldnames=None):
    """Guarda lista de dicts como CSV en results/."""
    path = RESULTS_DIR / f"{name}.csv"
    if not rows:
        path.write_text("")
        return path
    if fieldnames is None:
        fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return path


def _json_default(o):
    if hasattr(o, "tolist"):
        return o.tolist()
    if hasattr(o, "item"):
        return o.item()
    return str(o)


def banner(title: str):
    line = "=" * 78
    print(f"\n{line}\n{title}\n{line}")
