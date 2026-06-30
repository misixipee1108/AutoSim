"""Theory-specific probes for each drag model."""

from __future__ import annotations

from typing import Any

from autosim.models.base import DragModel
from autosim.models.custom import CustomDragModel
from autosim.models.linear import LinearDragModel
from autosim.models.polynomial import PolynomialDragModel
from autosim.models.quadratic import QuadraticDragModel
from autosim.schemas import SimInput, SimState


def compute_theory_probes(
    state: SimState,
    sim_input: SimInput,
    drag_model: DragModel,
) -> dict[str, Any]:
    m = sim_input.mass
    g = sim_input.gravity
    weight = m * g

    if isinstance(drag_model, LinearDragModel):
        drag = drag_model.drag_force(state.v)
        v_term = drag_model.terminal_velocity(m, g)
        result: dict[str, Any] = {
            "drag_weight_ratio": drag / weight if weight else 0.0,
        }
        if v_term is not None:
            result["v_terminal_linear"] = v_term
        return result

    if isinstance(drag_model, QuadraticDragModel):
        drag = drag_model.drag_force(state.v)
        v_term = drag_model.terminal_velocity(m, g)
        return {
            "v_terminal_quad": v_term,
            "reynolds_like": abs(state.v),
            "drag_weight_ratio": drag / weight if weight else 0.0,
        }

    if isinstance(drag_model, PolynomialDragModel):
        contribs = drag_model.term_contributions(state.v)
        total = sum(contribs) or 1.0
        fractions = [abs(c) / abs(total) for c in contribs]
        idx = drag_model.dominant_term_index(state.v)
        return {
            "dominant_term": idx,
            "term_fractions": fractions,
            "term_contributions": contribs,
        }

    if isinstance(drag_model, CustomDragModel):
        drag = drag_model.drag_force(state.v)
        return {
            "drag_value": drag,
            "drag_sensitivity": drag_model.drag_sensitivity(state.v),
        }

    return {}
