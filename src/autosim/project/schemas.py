"""SimulationProject v2 schemas (COMSOL-style Model / Studies / Results)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from autosim.api.schemas import ParameterSchema


class ProjectMetadata(BaseModel):
    description: str = ""
    tags: list[str] = Field(default_factory=list)


class GeometrySegment(BaseModel):
    name: str
    length: float
    origin: float = 0.0


class GeometryDefinition(BaseModel):
    dimension: Literal["0D", "1D", "2D", "3D"] = "1D"
    segments: list[GeometrySegment] = Field(default_factory=list)
    junction_position: float = 0.0


class DomainDefinition(BaseModel):
    domain_id: str
    geometry_ref: str = "full"
    label: str = ""


class MaterialAssignment(BaseModel):
    domain_id: str
    material_id: str = "Si"
    temperature_k: float = 300.0


class PhysicsInterfaceInstance(BaseModel):
    instance_id: str
    interface_id: str
    domain_ids: list[str] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)


class UserVariable(BaseModel):
    name: str
    expression: str = ""
    unit: str = ""


class BoundaryCondition(BaseModel):
    bc_id: str
    type: str
    boundary: str = "left"
    value: str | float = "auto"
    physics_ref: str | None = None


class InitialCondition(BaseModel):
    ic_id: str
    field: str
    expression: str = "0"
    physics_ref: str | None = None


class SourceTerm(BaseModel):
    source_id: str
    field: str
    expression: str = "0"
    domain_id: str | None = None


class JunctionRefinementMesh(BaseModel):
    enabled: bool = False
    ratio: float = 3.0
    width_frac: float = 0.1


class MeshDefinition(BaseModel):
    Nx: int = 400
    type: Literal["uniform", "nonuniform"] = "uniform"
    junction_refinement: JunctionRefinementMesh = Field(default_factory=JunctionRefinementMesh)


class ModelSection(BaseModel):
    geometry: GeometryDefinition = Field(default_factory=GeometryDefinition)
    domains: list[DomainDefinition] = Field(default_factory=list)
    materials: list[MaterialAssignment] = Field(default_factory=list)
    physics_interfaces: list[PhysicsInterfaceInstance] = Field(default_factory=list)
    variables: list[UserVariable] = Field(default_factory=list)
    boundary_conditions: list[BoundaryCondition] = Field(default_factory=list)
    initial_conditions: list[InitialCondition] = Field(default_factory=list)
    source_terms: list[SourceTerm] = Field(default_factory=list)
    mesh: MeshDefinition = Field(default_factory=MeshDefinition)


class SolverConvergenceSettings(BaseModel):
    criterion: Literal["residual", "solution", "either", "both"] = "both"
    relative_tol: float = 1e-4
    absolute_tol: float | None = None
    scaling_mode: Literal["auto", "initial", "manual"] = "auto"
    residual_scale: float | None = None
    solution_scale: float | None = None


class SolverStepSettings(BaseModel):
    relative_tol: float = 1e-4
    max_iter: int = 200
    damping: float = 0.5
    exp_clamp: float = 40.0
    linear_backend: Literal["direct", "iterative"] = "direct"
    adaptive_damping: bool = False
    convergence: SolverConvergenceSettings = Field(default_factory=SolverConvergenceSettings)


class SolverStep(BaseModel):
    step_id: str
    solver_id: Literal["newton", "damped_newton", "newton_line_search", "gummel"] = "damped_newton"
    settings: SolverStepSettings = Field(default_factory=SolverStepSettings)
    depends_on: list[str] = Field(default_factory=list)


class AgentSettings(BaseModel):
    backend: Literal["rules", "deepseek", "hybrid"] = "rules"
    probe_window: int = 10


class StudyDefinition(BaseModel):
    study_id: str
    study_type: Literal[
        "stationary",
        "time_dependent",
        "parameter_sweep",
        "bias_sweep",
        "cv_sweep",
        "transient",
        "optimization",
    ] = "stationary"
    label: str = ""
    physics_interface_ids: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    solver_sequence: list[SolverStep] = Field(default_factory=list)
    agent: AgentSettings | None = None


class OutputVariable(BaseModel):
    var_id: str
    source: str
    label: str = ""
    unit: str = ""
    kind: Literal["profile", "scalar", "series", "sweep", "time_series"] = "profile"


class ChartTabMeta(BaseModel):
    id: str
    label: str = ""


class ChartBindings(BaseModel):
    x: str = "x"
    y: list[str] = Field(default_factory=list)
    x_label: str = ""
    y_label: str = ""
    log_scale: bool = False


class VisualizationRecipe(BaseModel):
    viz_id: str
    chart_type: Literal[
        "line_profile",
        "convergence",
        "overview",
        "sweep",
        "time_series",
        "optimization",
    ] = "line_profile"
    tab: ChartTabMeta = Field(default_factory=lambda: ChartTabMeta(id="profiles", label="Profiles"))
    bindings: ChartBindings = Field(default_factory=ChartBindings)
    implemented: bool = True


class ResultsSection(BaseModel):
    output_variables: list[OutputVariable] = Field(default_factory=list)
    visualizations: list[VisualizationRecipe] = Field(default_factory=list)
    postprocessing: list[dict[str, Any]] = Field(default_factory=list)
    reports: list[dict[str, Any]] = Field(default_factory=list)


class SimulationProject(BaseModel):
    schema_version: Literal["2.0"] = "2.0"
    project_id: str
    title: str = ""
    model: ModelSection = Field(default_factory=ModelSection)
    studies: list[StudyDefinition] = Field(default_factory=list)
    results: ResultsSection = Field(default_factory=ResultsSection)
    active_study_id: str | None = None
    metadata: ProjectMetadata = Field(default_factory=ProjectMetadata)


class FieldDefinition(BaseModel):
    name: str
    label: str = ""
    unit: str = ""


class BCTypeSchema(BaseModel):
    type_id: str
    label: str = ""
    parameters: list[ParameterSchema] = Field(default_factory=list)


class VariableDefinition(BaseModel):
    name: str
    label: str = ""
    unit: str = ""
    expression: str = ""


class PhysicsInterfaceDescriptor(BaseModel):
    interface_id: str
    name: str
    category: str = "general"
    dimension: Literal["0D", "1D", "2D", "3D"] = "1D"
    governing_equations: list[str] = Field(default_factory=list)
    unknowns: list[FieldDefinition] = Field(default_factory=list)
    material_requirements: list[str] = Field(default_factory=list)
    boundary_condition_types: list[BCTypeSchema] = Field(default_factory=list)
    derived_variables: list[VariableDefinition] = Field(default_factory=list)
    parameter_schema: list[ParameterSchema] = Field(default_factory=list)
    default_instance_config: dict[str, Any] = Field(default_factory=dict)
    tree_parameter_groups: list[str] = Field(default_factory=list)
