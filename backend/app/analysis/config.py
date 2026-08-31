import os
import json
import copy
from typing import Dict, Any


def deep_update(orig: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively update orig with updates and return orig."""
    for k, v in updates.items():
        if isinstance(v, dict) and isinstance(orig.get(k), dict):
            deep_update(orig[k], v)
        else:
            orig[k] = v
    return orig


def load_thresholds(defaults: Dict[str, Any]) -> Dict[str, Any]:
    """Load thresholds configuration.

    Order of precedence:
    - Environment variable `ANALYSIS_THRESHOLDS`: if set, its value is either
      a path to a JSON file or a JSON string.
    - File at `backend/app/config/thresholds.json` if present.
    - Otherwise return `defaults` unchanged.
    """
    env = os.getenv('ANALYSIS_THRESHOLDS')
    cfg = None
    if env:
        # try file first
        if os.path.exists(env):
            try:
                with open(env, 'r') as f:
                    cfg = json.load(f)
            except Exception:
                cfg = None
        else:
            # try as JSON string
            try:
                cfg = json.loads(env)
            except Exception:
                cfg = None

    if cfg is None:
        # try default file relative to package
        base = os.path.dirname(__file__)
        path = os.path.join(base, '..', 'config', 'thresholds.json')
        path = os.path.normpath(path)
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    cfg = json.load(f)
            except Exception:
                cfg = None

    if cfg:
        # Use a deep copy of defaults to avoid mutating caller's nested structures
        merged = deep_update(copy.deepcopy(defaults), cfg)
        return merged
    return defaults

