"""Map SimulationProject v2 to legacy PnSimInput."""

from __future__ import annotations

from typing import Any

from autosim.pn.convergence import ConvergenceSpec
from autosim.pn.schemas import (
    BiasScanSpec,
    BoundarySpec,
    BreakdownSpec,
    CVScanSpec,
    DopingSpec,
    JunctionRefinementSpec,
    PnAgentConfig,
    PnOptimizationSpec,
    PnSimInput,
    RecombinationSpec,
    SolverSpec,
    TransientBiasSpec,
)
from autosim.project.schemas import (
    PhysicsInterfaceInstance,
    SimulationProject,
    SolverStep,
    StudyDefinition,
)
from autosim.schemas import AgentBackend, IterationConfig


def _geometry_lengths(project: SimulationProject) -> tuple[float, float, float]:
    geo = project.model.geometry
    if geo.segments:
        p_len = next((s.length for s in geo.segments if "p" in s.name.lower()), 2e-4)
        n_len = next((s.length for s in geo.segments if "n" in s.name.lower()), 2e-4)
    else:
        p_len, n_len = 2e-4, 2e-4
    return p_len, n_len, geo.junction_position


def _material_for_project(project: SimulationProject) -> tuple[str, float]:
    mats = project.model.materials
    if mats:
        return mats[0].material_id, mats[0].temperature_k
    return "Si", 300.0


def _boundary_from_project(project: SimulationProject) -> BoundarySpec:
    left_type = "dirichlet"
    right_type = "dirichlet"
    left_flux = 0.0
    right_flux = 0.0
    for bc in project.model.boundary_conditions:
        if bc.boundary == "left":
            if bc.type == "neumann_flux":
                left_type = "neumann"
                left_flux = float(bc.value) if bc.value != "auto" else 0.0
        elif bc.boundary == "right":
            if bc.type == "neumann_flux":
                right_type = "neumann"
                right_flux = float(bc.value) if bc.value != "auto" else 0.0
    return BoundarySpec(
        left_type=left_type,  # type: ignore[arg-type]
        right_type=right_type,  # type: ignore[arg-type]
        left_flux=left_flux,
        right_flux=right_flux,
    )


def _solver_from_study(study: StudyDefinition) -> SolverSpec:
    if not study.solver_sequence:
        return SolverSpec()
    step: SolverStep = study.solver_sequence[0]
    settings = step.settings
    conv = settings.convergence
    return SolverSpec(
        tol=settings.relative_tol,
        max_iter=settings.max_iter,
        damping=settings.damping,
        exp_clamp=settings.exp_clamp,
        method=step.solver_id if step.solver_id != "gummel" else "damped_newton",  # type: ignore[arg-type]
        linear_backend=settings.linear_backend,
        adaptive_damping=settings.adaptive_damping,
        convergence=ConvergenceSpec(
            criterion=conv.criterion,
            relative_tol=conv.relative_tol,
            absolute_tol=conv.absolute_tol,
            scaling_mode=conv.scaling_mode,
            residual_scale=conv.residual_scale,
            solution_scale=conv.solution_scale,
        ),
    )


def _doping_from_settings(settings: dict[str, Any]) -> DopingSpec | None:
    raw = settings.get("doping")
    if not raw:
        na = settings.get("Na")
        nd = settings.get("Nd")
        if na is not None or nd is not None:
            return DopingSpec(type="abrupt", Na=na, Nd=nd)
        return None
    if isinstance(raw, dict):
        return DopingSpec.model_validate(raw)
    return None


def project_to_pn_sim_input(
    project: SimulationProject,
    study: StudyDefinition,
    instance: PhysicsInterfaceInstance,
) -> PnSimInput:
    """Convert v2 project + study + physics instance to PnSimInput."""
    settings = dict(instance.settings)
    Lp, Ln, xj = _geometry_lengths(project)
    material, temperature_k = _material_for_project(project)
    mesh = project.model.mesh
    jref = mesh.junction_refinement

    doping = _doping_from_settings(settings)
    na = settings.get("Na") or (doping.Na if doping else None) or 1e18
    nd = settings.get("Nd") or (doping.Nd if doping else None) or 1e16
    if doping and doping.Na is None:
        doping = doping.model_copy(update={"Na": na, "Nd": nd})

    model_type = settings.get("model_type", "poisson")
    params = study.parameters
    vapp = float(params.get("Vapp", 0.0))
    solver = _solver_from_study(study)

    agent_cfg = PnAgentConfig()
    if study.agent:
        agent_cfg = PnAgentConfig(
            backend=AgentBackend(study.agent.backend),
            probe_window=study.agent.probe_window,
        )

    bias_scan = BiasScanSpec()
    if isinstance(params.get("bias_scan"), dict):
        bias_scan = BiasScanSpec.model_validate(params["bias_scan"])
    elif study.study_type == "bias_sweep":
        bias_scan = bias_scan.model_copy(update={"enabled": True})

    cv_scan = CVScanSpec()
    if isinstance(params.get("cv_scan"), dict):
        cv_scan = CVScanSpec.model_validate(params["cv_scan"])
    elif study.study_type == "cv_sweep":
        cv_scan = cv_scan.model_copy(update={"enabled": True})

    transient = TransientBiasSpec()
    if isinstance(params.get("transient"), dict):
        transient = TransientBiasSpec.model_validate(params["transient"])
    elif study.study_type == "time_dependent" and model_type == "transient_dd":
        transient = transient.model_copy(update={"enabled": True})

    recombination = RecombinationSpec()
    if isinstance(settings.get("recombination"), dict):
        recombination = RecombinationSpec.model_validate(settings["recombination"])
    elif isinstance(params.get("recombination"), dict):
        recombination = RecombinationSpec.model_validate(params["recombination"])

    breakdown = BreakdownSpec()
    if isinstance(settings.get("breakdown"), dict):
        breakdown = BreakdownSpec.model_validate(settings["breakdown"])
    elif isinstance(params.get("breakdown"), dict):
        breakdown = BreakdownSpec.model_validate(params["breakdown"])

    optimization = PnOptimizationSpec()
    if isinstance(params.get("optimization"), dict):
        optimization = PnOptimizationSpec.model_validate(params["optimization"])
    elif study.study_type == "optimization":
        optimization = optimization.model_copy(update={"enabled": True})

    iteration = IterationConfig(max_trials=1)
    if isinstance(params.get("iteration"), dict):
        iteration = IterationConfig.model_validate(params["iteration"])
    elif study.study_type == "parameter_sweep":
        iteration = iteration.model_copy(update={"max_trials": max(iteration.max_trials, 2)})

    return PnSimInput(
        model_type=model_type,  # type: ignore[arg-type]
        material=material,
        temperature_k=temperature_k,
        Na=float(na),
        Nd=float(nd),
        Lp=Lp,
        Ln=Ln,
        xj=xj,
        Nx=mesh.Nx,
        boundary=_boundary_from_project(project),
        Vapp=vapp,
        tol=solver.tol,
        max_iter=solver.max_iter,
        damping=solver.damping,
        exp_clamp=solver.exp_clamp,
        doping=doping,
        solver=solver,
        bias_scan=bias_scan,
        cv_scan=cv_scan,
        transient=transient,
        recombination=recombination,
        breakdown=breakdown,
        optimization=optimization,
        junction_refinement=JunctionRefinementSpec(
            enabled=jref.enabled,
            ratio=jref.ratio,
            width_frac=jref.width_frac,
        ),
        agent=agent_cfg,
        iteration=iteration,
    )


def legacy_flat_to_project(flat: dict[str, Any]) -> SimulationProject:
    """Build a v2 project from legacy flat PN config (for equivalence tests)."""
    from autosim.project.templates import pn_si_stationary_template

    project = pn_si_stationary_template()
    project.project_id = flat.get("project_id", "legacy_mapped")

    iface = project.model.physics_interfaces[0]
    settings = dict(iface.settings)
    if "doping" in flat and isinstance(flat["doping"], dict):
        doping = dict(flat["doping"])
        doping.setdefault("Na", flat.get("Na", 1e18))
        doping.setdefault("Nd", flat.get("Nd", 1e16))
        settings["doping"] = doping
    elif "Na" in flat or "Nd" in flat:
        settings["doping"] = {
            "type": flat.get("doping", {}).get("type", "abrupt") if isinstance(flat.get("doping"), dict) else "abrupt",
            "Na": flat.get("Na", 1e18),
            "Nd": flat.get("Nd", 1e16),
        }
    settings["model_type"] = flat.get("model_type", "poisson")
    iface.settings = settings

    if flat.get("Lp") is not None:
        project.model.geometry.segments = [
            project.model.geometry.segments[0].model_copy(update={"length": flat["Lp"]}),
            project.model.geometry.segments[1].model_copy(update={"length": flat.get("Ln", 2e-4)}),
        ]
    if flat.get("xj") is not None:
        project.model.geometry.junction_position = flat["xj"]
    if flat.get("Nx") is not None:
        project.model.mesh.Nx = int(flat["Nx"])
    if flat.get("material"):
        project.model.materials[0].material_id = str(flat["material"])
    if flat.get("temperature_k") is not None:
        project.model.materials[0].temperature_k = float(flat["temperature_k"])

    study = project.studies[0]
    study.parameters["Vapp"] = flat.get("Vapp", 0.0)
    step = study.solver_sequence[0]
    step.settings.relative_tol = float(flat.get("tol", flat.get("solver", {}).get("convergence", {}).get("relative_tol", 1e-4)))
    step.settings.max_iter = int(flat.get("max_iter", 200))
    step.settings.damping = float(flat.get("damping", 0.5))
    step.settings.exp_clamp = float(flat.get("exp_clamp", 40.0))
    if "solver" in flat and isinstance(flat["solver"], dict):
        s = flat["solver"]
        if "method" in s:
            step.solver_id = s["method"]  # type: ignore[assignment]
        if "convergence" in s and isinstance(s["convergence"], dict):
            c = s["convergence"]
            step.settings.convergence.criterion = c.get("criterion", "both")
            step.settings.convergence.scaling_mode = c.get("scaling_mode", "auto")

    if "agent" in flat and isinstance(flat["agent"], dict):
        study.agent = study.agent.model_copy(update=flat["agent"]) if study.agent else None

    return project
