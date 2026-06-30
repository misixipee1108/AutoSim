"""Tests for drag models."""

import math

import pytest

from autosim.models.custom import CustomDragModel, evaluate_expression
from autosim.models.linear import LinearDragModel
from autosim.models.polynomial import PolynomialDragModel
from autosim.models.quadratic import QuadraticDragModel
from autosim.models.base import build_drag_model
from autosim.schemas import DragModelType


def test_linear_drag_force():
    model = LinearDragModel({"c1": 2.0})
    assert model.drag_force(0) == 0
    assert model.drag_force(10) == -20
    assert model.drag_force(-10) == 20


def test_quadratic_drag_force():
    model = QuadraticDragModel({"c2": 0.5})
    assert model.drag_force(0) == 0
    assert model.drag_force(10) == -50
    assert model.drag_force(-10) == 50


def test_polynomial_drag_force():
    model = PolynomialDragModel({"coeffs": [1.0, 0.1, 0.01]})
    assert model.drag_force(0) == 0
    assert model.drag_force(10) == -30
    assert model.drag_force(-10) == 30


def test_custom_drag_expression():
    model = CustomDragModel({"expression": "c1 * abs_v + c2 * abs_v * abs_v", "c1": 1.0, "c2": 0.5})
    assert model.drag_force(10) == -60
    assert model.drag_force(-10) == 60


def test_custom_unsafe_expression_rejected():
    with pytest.raises(ValueError):
        evaluate_expression("__import__('os').system('echo')", {})


def test_linear_terminal_velocity():
    model = LinearDragModel({"c1": 2.0})
    assert model.terminal_velocity(1.0, 9.81) == pytest.approx(4.905)


def test_quadratic_terminal_velocity():
    model = QuadraticDragModel({"c2": 0.5})
    assert model.terminal_velocity(1.0, 9.81) == pytest.approx(math.sqrt(19.62))


def test_build_drag_model_factory():
    model = build_drag_model(DragModelType.LINEAR, {"c1": 1.0})
    assert model.name == "linear"
