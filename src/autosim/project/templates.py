"""Built-in SimulationProject templates."""

from __future__ import annotations

from collections.abc import Callable

from autosim.project.schemas import (
    AgentSettings,
    BoundaryCondition,
    ChartBindings,
    ChartTabMeta,
    DomainDefinition,
    GeometryDefinition,
    GeometrySegment,
    MaterialAssignment,
    MeshDefinition,
    ModelSection,
    OutputVariable,
    PhysicsInterfaceInstance,
    ResultsSection,
    SimulationProject,
    SolverConvergenceSettings,
    SolverStep,
    SolverStepSettings,
    StudyDefinition,
    VisualizationRecipe,
)


def pn_si_stationary_template() -> SimulationProject:
    return SimulationProject(
        project_id="pn_si_equilibrium_demo",
        title="1D Si PN Junction — Stationary Poisson",
        model=ModelSection(
            geometry=GeometryDefinition(
                dimension="1D",
                segments=[
                    GeometrySegment(name="p_side", length=2e-4, origin=-2e-4),
                    GeometrySegment(name="n_side", length=2e-4, origin=0.0),
                ],
                junction_position=0.0,
            ),
            domains=[DomainDefinition(domain_id="semiconductor", geometry_ref="full")],
            materials=[
                MaterialAssignment(domain_id="semiconductor", material_id="Si", temperature_k=300.0)
            ],
            physics_interfaces=[
                PhysicsInterfaceInstance(
                    instance_id="pn_poisson",
                    interface_id="semiconductor_1d_poisson",
                    domain_ids=["semiconductor"],
                    settings={
                        "doping": {"type": "abrupt", "Na": 1e18, "Nd": 1e16},
                        "carrier_model": "boltzmann",
                        "model_type": "poisson",
                    },
                )
            ],
            boundary_conditions=[
                BoundaryCondition(
                    bc_id="left_contact",
                    type="dirichlet_potential",
                    boundary="left",
                    value="auto",
                ),
                BoundaryCondition(
                    bc_id="right_contact",
                    type="dirichlet_potential",
                    boundary="right",
                    value="auto",
                ),
            ],
            mesh=MeshDefinition(Nx=400, type="uniform"),
        ),
        studies=[
            StudyDefinition(
                study_id="stat_equilibrium",
                label="Stationary Equilibrium",
                study_type="stationary",
                physics_interface_ids=["pn_poisson"],
                parameters={"Vapp": 0.0},
                solver_sequence=[
                    SolverStep(
                        step_id="newton_solve",
                        solver_id="damped_newton",
                        settings=SolverStepSettings(
                            relative_tol=1e-4,
                            max_iter=200,
                            damping=0.5,
                            convergence=SolverConvergenceSettings(criterion="both", scaling_mode="auto"),
                        ),
                    )
                ],
                agent=AgentSettings(backend="rules", probe_window=10),
            )
        ],
        results=ResultsSection(
            output_variables=[
                OutputVariable(
                    var_id="potential",
                    source="pn_poisson.psi",
                    label="Potential ψ(x)",
                    unit="V",
                    kind="profile",
                ),
                OutputVariable(
                    var_id="electric_field",
                    source="pn_poisson.E",
                    label="Electric Field E(x)",
                    unit="V/cm",
                    kind="profile",
                ),
                OutputVariable(
                    var_id="Vbi",
                    source="derived.Vbi",
                    label="Built-in Potential",
                    unit="V",
                    kind="scalar",
                ),
            ],
            visualizations=[
                VisualizationRecipe(
                    viz_id="potential_profile",
                    chart_type="line_profile",
                    tab=ChartTabMeta(id="profiles", label="Profiles"),
                    bindings=ChartBindings(
                        x="x",
                        y=["potential"],
                        x_label="x (cm)",
                        y_label="ψ (V)",
                    ),
                ),
            ],
        ),
        active_study_id="stat_equilibrium",
    )


def falling_body_template() -> SimulationProject:
    return SimulationProject(
        project_id="falling_body_v2",
        title="Falling Body — Time Dependent",
        model=ModelSection(
            geometry=GeometryDefinition(dimension="0D", segments=[], junction_position=0.0),
            domains=[DomainDefinition(domain_id="body", geometry_ref="point")],
            materials=[],
            physics_interfaces=[
                PhysicsInterfaceInstance(
                    instance_id="falling_body",
                    interface_id="mechanics_0d_falling_body",
                    domain_ids=["body"],
                    settings={
                        "mass": 1.0,
                        "gravity": 9.81,
                        "y0": 100.0,
                        "v0": 0.0,
                        "ground_y": 0.0,
                        "drag_model": "quadratic",
                        "drag_params": {"c2": 0.5},
                        "t_max": 30.0,
                        "dt": 0.01,
                        "probe_interval": 0.1,
                    },
                )
            ],
            boundary_conditions=[],
            mesh=MeshDefinition(Nx=1, type="uniform"),
        ),
        studies=[
            StudyDefinition(
                study_id="time_fall",
                label="Time Dependent Fall",
                study_type="time_dependent",
                physics_interface_ids=["falling_body"],
                parameters={"iteration": {"max_trials": 1, "stop_on": "recommend_next"}},
                agent=AgentSettings(backend="hybrid", probe_window=10),
            )
        ],
        results=ResultsSection(
            output_variables=[
                OutputVariable(
                    var_id="height",
                    source="falling_body.y",
                    label="Height y(t)",
                    unit="m",
                    kind="profile",
                ),
                OutputVariable(
                    var_id="velocity",
                    source="falling_body.v",
                    label="Velocity v(t)",
                    unit="m/s",
                    kind="profile",
                ),
                OutputVariable(
                    var_id="impact_time",
                    source="derived.impact_time",
                    label="Impact Time",
                    unit="s",
                    kind="scalar",
                ),
                OutputVariable(
                    var_id="impact_velocity",
                    source="derived.impact_velocity",
                    label="Impact Velocity",
                    unit="m/s",
                    kind="scalar",
                ),
            ],
            visualizations=[
                VisualizationRecipe(
                    viz_id="height_time",
                    chart_type="time_series",
                    tab=ChartTabMeta(id="time_series", label="Time Series"),
                    bindings=ChartBindings(
                        x="t",
                        y=["height", "velocity"],
                        x_label="t (s)",
                        y_label="Value",
                    ),
                ),
            ],
        ),
        active_study_id="time_fall",
    )


TEMPLATE_BUILDERS: dict[str, Callable[[], SimulationProject]] = {
    "pn_stationary": pn_si_stationary_template,
    "falling_body": falling_body_template,
}


def get_template(template_id: str) -> SimulationProject:
    if template_id not in TEMPLATE_BUILDERS:
        raise KeyError(f"Unknown template: {template_id}")
    return TEMPLATE_BUILDERS[template_id]()


def list_template_ids() -> list[str]:
    return list(TEMPLATE_BUILDERS.keys())
