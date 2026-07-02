"""Legacy model registry — removed in v2 migration.

Physics plugins and project templates replace JSON descriptors.
"""

from __future__ import annotations


def list_models():
    raise RuntimeError("Legacy model registry removed. Use plugins.registry and project templates.")


def get_model(model_id: str):
    raise RuntimeError(f"Legacy model registry removed: {model_id}")


def get_adapter(model_id: str):
    raise RuntimeError(f"Legacy adapter registry removed: {model_id}")
