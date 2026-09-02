from __future__ import annotations

from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_yaml(relative_path: str) -> dict:
    path = ROOT / relative_path
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_instruments() -> dict:
    return load_yaml("config/instruments.yaml")["instruments"]


def load_evaluation_config() -> dict:
    return load_yaml("config/evaluation.yaml")
