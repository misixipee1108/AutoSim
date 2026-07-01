"""Tabulated doping profile from CSV or inline points."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np


class TableDoping:
    name = "table"

    def __init__(self, points: list[tuple[float, float]] | None = None, file: str | Path | None = None) -> None:
        if points:
            self._x = np.array([p[0] for p in points], dtype=float)
            self._c = np.array([p[1] for p in points], dtype=float)
        elif file:
            self._x, self._c = self._load_file(Path(file))
        else:
            raise ValueError("table doping requires 'points' or 'file'")
        if len(self._x) < 2:
            raise ValueError("table doping needs at least 2 points")
        order = np.argsort(self._x)
        self._x = self._x[order]
        self._c = self._c[order]

    @staticmethod
    def _load_file(path: Path) -> tuple[np.ndarray, np.ndarray]:
        if not path.exists():
            raise FileNotFoundError(path)
        xs: list[float] = []
        cs: list[float] = []
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames and "x" in reader.fieldnames:
                col = "C" if "C" in reader.fieldnames else "c"
                if col not in reader.fieldnames:
                    col = "net_doping" if "net_doping" in reader.fieldnames else reader.fieldnames[-1]
                for row in reader:
                    xs.append(float(row["x"]))
                    cs.append(float(row[col]))
            else:
                f.seek(0)
                for row in csv.reader(f):
                    if len(row) >= 2 and row[0].strip() and not row[0].startswith("#"):
                        try:
                            xs.append(float(row[0]))
                            cs.append(float(row[1]))
                        except ValueError:
                            continue
        return np.array(xs), np.array(cs)

    def net_doping(self, x: float) -> float:
        return float(np.interp(x, self._x, self._c))

    def net_doping_array(self, x) -> np.ndarray:
        return np.interp(np.asarray(x, dtype=float), self._x, self._c)
