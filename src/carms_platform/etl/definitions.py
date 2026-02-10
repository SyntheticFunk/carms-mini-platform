# src/carms_platform/etl/definitions.py
from __future__ import annotations

from pathlib import Path
from dagster import asset, Definitions, MetadataValue

from carms_platform.etl.load import load_all, create_or_replace_views

def repo_root() -> Path:
    p = Path.cwd().resolve()
    while not (p / "pyproject.toml").exists():
        if p.parent == p:
            raise RuntimeError("Could not locate repo root")
        p = p.parent
    return p

@asset
def load_carms_warehouse():
    data_raw = repo_root() / "data" / "raw" / "dnokes"
    stats = load_all(match_cycle_id=1503, data_raw=data_raw)
    return MetadataValue.json(stats)

@asset(deps=[load_carms_warehouse])
def views():
    create_or_replace_views()
    return "ok"

defs = Definitions(assets=[load_carms_warehouse, views])
