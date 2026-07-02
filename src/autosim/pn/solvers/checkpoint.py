"""Newton solver checkpoint save/load for warm restart."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def checkpoint_path(checkpoint_dir: str | Path, tag: str = "psi") -> Path:
    base = Path(checkpoint_dir)
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{tag}.npy"


def save_checkpoint(
    checkpoint_dir: str | Path,
    psi: np.ndarray,
    *,
    iteration: int | None = None,
    tag: str = "psi",
) -> Path:
    path = checkpoint_path(checkpoint_dir, tag)
    np.save(path, psi)
    meta = {"iteration": iteration, "length": len(psi)}
    path.with_suffix(".json").write_text(json.dumps(meta), encoding="utf-8")
    return path


def load_checkpoint(checkpoint_dir: str | Path, tag: str = "psi") -> np.ndarray | None:
    path = checkpoint_path(checkpoint_dir, tag)
    if not path.exists():
        return None
    return np.load(path)
