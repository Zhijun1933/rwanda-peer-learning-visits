"""Load YAML configuration files."""

from functools import lru_cache
from pathlib import Path

import yaml

from . import CONFIG_DIR


@lru_cache(maxsize=None)
def load(name: str, config_dir: Path = CONFIG_DIR) -> dict:
    with open(config_dir / f"{name}.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def sources() -> dict:
    return load("sources")


def vocab() -> dict:
    return load("vocab")
