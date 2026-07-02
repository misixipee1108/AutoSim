"""Tests for Shockley analytic validation and solver diagnostics."""

from __future__ import annotations

import numpy as np
import pytest

from autosim.pn.analytical import bernoulli_b, shockley_current, shockley_saturation_current
from autosim.materials.loader import load_material
from autosim.pn.schemas import PnSimInput
from autosim.pn.validation import build_shockley_validation_report, shockley_validation_eligible


def test_bernoulli_b_small_argument():
    assert bernoulli_b(0.0) == pytest.approx(1.0)
    assert bernoulli_b(1e-10) == pytest.approx(1.0, rel=1e-6)


def test_shockley_saturation_current_positive():
    material = load_material("Si", 300.0)
    js = shockley_saturation_current(1e16, 1e16, material, 2e-4, 2e-4)
    assert js > 0


def test_shockley_validation_eligible_forward_dd():
    sim = PnSimInput(model_type="drift_diffusion", Na=1e16, Nd=1e16, Vapp=0.3)
    ok, _ = shockley_validation_eligible(sim)
    assert ok is True


def test_shockley_validation_ineligible_poisson():
    sim = PnSimInput(model_type="poisson", Vapp=0.3)
    ok, reason = shockley_validation_eligible(sim)
    assert ok is False
    assert "drift_diffusion" in reason


def test_build_shockley_validation_report_matches_analytic():
    material = load_material("Si", 300.0)
    sim = PnSimInput(model_type="drift_diffusion", Na=1e16, Nd=1e16, Vapp=0.3, Lp=2e-4, Ln=2e-4)
    js = shockley_saturation_current(1e16, 1e16, material, sim.Lp, sim.Ln)
    j_ana = shockley_current(sim.Vapp, js, material)
    report = build_shockley_validation_report(j_ana, sim, j_tol=0.01)
    assert report.status.value == "analytic_passed"
