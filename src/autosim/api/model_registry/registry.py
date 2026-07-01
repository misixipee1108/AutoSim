"""Model descriptor registry."""

from __future__ import annotations

import json
from pathlib import Path

from autosim.api.schemas import ModelDescriptor

_REGISTRY_DIR = Path(__file__).parent
_LIBRARY_DIR = _REGISTRY_DIR.parents[1] / "materials" / "library"
_DESCRIPTORS: dict[str, ModelDescriptor] = {}


_MATERIAL_OPTIONS: dict[str, tuple[str, str]] = {
    "silicon": ("Si", "Silicon (Si)"),
    "germanium": ("Ge", "Germanium (Ge)"),
}


def _material_options_from_library() -> list[dict[str, str]]:
    """Build material select options by scanning YAML library (avoids circular import)."""
    options: list[dict[str, str]] = []
    if not _LIBRARY_DIR.is_dir():
        return options
    for path in sorted(_LIBRARY_DIR.glob("*.yaml")):
        value, label = _MATERIAL_OPTIONS.get(path.stem, (path.stem, path.stem.replace("_", " ").title()))
        options.append({"value": value, "label": label})
    return options


def _enrich_pn_descriptor(descriptor: ModelDescriptor) -> ModelDescriptor:
    """Inject material options from the YAML library at load time."""
    options = _material_options_from_library()
    if not options:
        return descriptor

    params = []
    for param in descriptor.parameters:
        if param.name == "material":
            params.append(param.model_copy(update={"options": options}))
        else:
            params.append(param)
    return descriptor.model_copy(update={"parameters": params})


def _load_descriptors() -> None:
    if _DESCRIPTORS:
        return
    for path in sorted(_REGISTRY_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        descriptor = ModelDescriptor.model_validate(data)
        if descriptor.model_id == "pn_junction_1d":
            descriptor = _enrich_pn_descriptor(descriptor)
        _DESCRIPTORS[descriptor.model_id] = descriptor


def list_models() -> list[ModelDescriptor]:
    _load_descriptors()
    return list(_DESCRIPTORS.values())


def get_model(model_id: str) -> ModelDescriptor:
    _load_descriptors()
    if model_id not in _DESCRIPTORS:
        raise KeyError(f"Unknown model_id: {model_id}")
    return _DESCRIPTORS[model_id]


def get_adapter(model_id: str):
    from autosim.api.adapters.falling_block import FallingBlockAdapter
    from autosim.api.adapters.pn import PnAdapter

    adapters = {
        "falling_block": FallingBlockAdapter(),
        "pn_junction_1d": PnAdapter(),
    }
    if model_id not in adapters:
        raise KeyError(f"No adapter for model_id: {model_id}")
    return adapters[model_id]
