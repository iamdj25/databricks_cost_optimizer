"""Reader for the Databricks CLI config file (~/.databrickscfg).

The CLI stores one section per profile, e.g.:

    [DEFAULT]
    host = https://adb-123.4.azuredatabricks.net
    token = dapiXXXX

    [prod]
    host = https://prod.cloud.databricks.com
    token = dapiYYYY

This lets the optimizer target whatever workspace the CLI is logged into,
without re-entering credentials. Honors DATABRICKS_CONFIG_FILE if set.
"""
from __future__ import annotations

import configparser
import os
from typing import Dict, List, Optional


def config_path() -> str:
    return os.getenv("DATABRICKS_CONFIG_FILE") or os.path.expanduser("~/.databrickscfg")


def _load() -> Optional[configparser.ConfigParser]:
    path = config_path()
    if not os.path.exists(path):
        return None
    cp = configparser.ConfigParser()
    cp.read(path)
    return cp


def list_profiles() -> List[str]:
    cp = _load()
    if cp is None:
        return []
    names = list(cp.sections())
    if cp.defaults():
        names.insert(0, "DEFAULT")
    return names


def read_profile(profile: Optional[str] = None) -> Dict[str, str]:
    """Return {host, token, ...} for a profile. Defaults to DEFAULT/env."""
    cp = _load()
    if cp is None:
        return {}
    name = profile or os.getenv("DATABRICKS_CONFIG_PROFILE") or "DEFAULT"
    if name == "DEFAULT":
        return dict(cp.defaults())
    if cp.has_section(name):
        return dict(cp.items(name))
    return {}
