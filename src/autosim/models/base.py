"""Drag model protocol and factory."""

from __future__ import annotations

from typing import Any, Protocol

from autosim.schemas import DragModelType


class DragModel(Protocol):
    name: str
    params: dict[str, Any]

    def drag_force(self, v: float) -> float:
        """Return drag force magnitude (opposes motion)."""
        ...


def build_drag_model(model_type: DragModelType, params: dict[str, Any]) -> DragModel:
    from autosim.models.custom import CustomDragModel
    from autosim.models.linear import LinearDragModel
    from autosim.models.polynomial import PolynomialDragModel
    from autosim.models.quadratic import QuadraticDragModel

    builders = {
        DragModelType.LINEAR: LinearDragModel,
        DragModelType.QUADRATIC: QuadraticDragModel,
        DragModelType.POLYNOMIAL: PolynomialDragModel,
        DragModelType.CUSTOM: CustomDragModel,
    }
    return builders[model_type](params)
