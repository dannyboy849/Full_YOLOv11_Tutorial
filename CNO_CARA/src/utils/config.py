"""
src/utils/config.py
Loads and merges YAML configs into a SimpleNamespace.

Access patterns (both always work):
    cfg.output_vars           ← promoted flat shortcut
    cfg.dataset.output_vars   ← nested under filename
    cfg.mpc.u_min             ← nested under filename
    cfg.paths.models          ← from base.yaml (always flat)
"""

import yaml

from types      import SimpleNamespace
from pathlib    import Path


CONFIG_DIR = Path(__file__).resolve().parents[2] / "configs"


def _dict_to_ns(d: dict) -> SimpleNamespace:
    ns = SimpleNamespace()
    for k, v in d.items():
        setattr(ns, k, _dict_to_ns(v) if isinstance(v, dict) else v)
    return ns


def _deep_merge(base: dict, override: dict) -> dict:
    merged = base.copy()
    for k, v in override.items():
        if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
            merged[k] = _deep_merge(merged[k], v)
        else:
            merged[k] = v
    return merged


def load_config(*names: str) -> SimpleNamespace:
    """
    load and merge named YAML files from configs/.
    """
    if "base" not in names:
        names = ("base",) + tuple(names)

    # -----------------------------------------------------
    # ── load base flat ───────────────────────────────────
    # -----------------------------------------------------
    base_path = CONFIG_DIR / "base.yaml"
    if not base_path.exists():
        raise FileNotFoundError(f"Config not found: {base_path}")
    with open(base_path) as f:
        merged: dict = yaml.safe_load(f) or {}

    # -----------------------------------------------------
    # ── load each other file, nest and promote flat  ─────
    # -----------------------------------------------------
    for name in names:
        if name == "base":
            continue
        path = CONFIG_DIR / f"{name}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Config not found: {path}")
        with open(path) as f:
            data: dict = yaml.safe_load(f) or {}

        # nest under filename  ->  cfg.mpc.u_min, cfg.dataset.output_vars
        merged = _deep_merge(merged, {name: data})

        # only promotes if key doesn't already exist
        for k, v in data.items():
            if k not in merged:
                merged[k] = v

    return _dict_to_ns(merged)