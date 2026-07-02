# Plugin Development Guide

## Physics Plugin

1. Add manifest: `src/autosim/plugins/physics/manifests/<interface_id>.json`
2. Implement plugin class in `src/autosim/plugins/physics/<interface_id>/plugin.py`
3. Add compat mapper if reusing legacy solvers: `compat.py`
4. Register in `plugins/registry.py` `_physics_plugins()`

### Manifest Fields

- `interface_id`, `name`, `category`, `dimension`
- `parameter_schema` — drives DynamicParameterForm via `POST /api/project/parameters`
- `default_instance_config` — template defaults

### Plugin Methods

```python
def get_descriptor(self) -> PhysicsInterfaceDescriptor: ...
def validate_instance(self, instance, model) -> None: ...
def build_sim_input(self, project, study, instance) -> Any: ...
def run(self, sim_input, callbacks, trial_index=0) -> Any: ...
def filter_outputs(self, raw_result, results) -> dict[str, Any]: ...
```

## Study Runner

1. Create `plugins/studies/<name>.py` with `study_type` class attribute
2. Register in `plugins/registry.py` `_study_runners()`
3. Delegate to `plugins/engine/pn_engine.py` or `falling_engine.py` for execution

## Project Templates

Add builder in `project/templates.py` `TEMPLATE_BUILDERS` and optional YAML conversion in `project/yaml_converter.py`.

## Testing

- Unit: compat mapping + study runner smoke
- API: `tests/api/test_project_api.py`
- Equivalence: compare v2 project run vs legacy YAML via `legacy_flat_to_project` / `pn_yaml_to_project`
