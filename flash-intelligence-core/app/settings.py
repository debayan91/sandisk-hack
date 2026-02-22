"""
settings.py — Loads and exposes config.yaml as a global singleton.

All modules import from here rather than reading the file themselves,
ensuring a single parse and a consistent configuration object.
"""

import pathlib
import yaml
from functools import lru_cache

CONFIG_FILE = pathlib.Path(__file__).parent.parent / "config.yaml"


@lru_cache(maxsize=1)
def get_config() -> dict:
    """Return parsed config.yaml as a nested dict (cached after first load)."""
    with open(CONFIG_FILE, "r") as f:
        return yaml.safe_load(f)
