"""Load YAML configuration files."""

import csv
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


OUTSIDE_AFRICA = "Outside Africa"
MULTINATIONAL = "Multinational"


@lru_cache(maxsize=None)
def regions(config_dir: Path = CONFIG_DIR) -> dict[str, str]:
    """ISO3 code -> African Union region, from config/regions.csv."""
    with open(config_dir / "regions.csv", encoding="utf-8", newline="") as f:
        return {row["iso3"]: row["region"] for row in csv.DictReader(f)}


def region_of(iso3: str, config_dir: Path = CONFIG_DIR) -> str:
    """AU region for a sending country; non-African countries are 'Outside Africa',
    and a blank code (a multinational body) is 'Multinational'."""
    iso3 = (iso3 or "").strip().upper()
    if not iso3:
        return MULTINATIONAL
    return regions(config_dir).get(iso3, OUTSIDE_AFRICA)
