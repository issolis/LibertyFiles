from __future__ import annotations

from pathlib import Path
from typing import Iterator

from liberty.parser import parse_liberty
from liberty.types import Group


def load_liberty(path: str | Path) -> "LibertyExplorer":
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    root: Group = parse_liberty(text)
    return LibertyExplorer(root, level="library", path=[root.group_name or "library"])


class LibertyExplorer:
    def __init__(self, group: Group, level: str, path: list[str]) -> None:
        self._group = group
        self.level = level
        self.path = path

    @property
    def name(self) -> str:
        return self._group.args[0] if self._group.args else (self._group.group_name or "<anon>")

    @property
    def kind(self) -> str:
        return self._group.group_name

    def attributes(self) -> dict[str, object]:
        out: dict[str, object] = {}
        for attr in self._group.attributes:
            out[str(attr.name)] = attr.value
        return out

    def get(self, attr_name: str, default=None):
        try:
            return self._group.get_attribute(attr_name)
        except Exception:
            return default

    def child_kinds(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for g in self._group.groups:
            counts[g.group_name] = counts.get(g.group_name, 0) + 1
        return counts

    def children(self, kind: str | None = None) -> list[LibertyExplorer]:
        groups = self._group.get_groups(kind) if kind else self._group.groups
        children = []
        for g in groups:
            child_level = _infer_level(g.group_name)
            child_name = g.args[0] if g.args else g.group_name
            children.append(LibertyExplorer(g, child_level, self.path + [str(child_name)]))
        return children
    def child_names(self, kind: str) -> list[str]:
        return [
            str(g.args[0]) if g.args else g.group_name
            for g in self._group.get_groups(kind)
        ]

    def find(self, kind: str, name: str) -> "LibertyExplorer | None":
        for child in self.children(kind):
            if child.name == name:
                return child
        return None
    
    def all_child_names(self, with_kind: bool = False) -> list[str] | list[tuple[str, str]]:
        if with_kind:
            return [
                (g.group_name, str(g.args[0]) if g.args else g.group_name)
                for g in self._group.groups
            ]
        return [
            str(g.args[0]) if g.args else g.group_name
            for g in self._group.groups
        ]

    

_KIND_TO_LEVEL = {
    "library": "library",
    "cell": "cell",
    "pin": "pin",
    "bus": "pin",
    "timing": "timing",
    "internal_power": "power",
    "leakage_power": "power",
    "lu_table_template": "lut_template",
    "power_lut_template": "lut_template",
    "cell_rise": "lut",
    "cell_fall": "lut",
    "rise_transition": "lut",
    "fall_transition": "lut",
    "rise_power": "lut",
    "fall_power": "lut",
    "ff": "sequential",
    "latch": "sequential",
}


def _infer_level(kind: str) -> str:
    return _KIND_TO_LEVEL.get(kind, kind)

