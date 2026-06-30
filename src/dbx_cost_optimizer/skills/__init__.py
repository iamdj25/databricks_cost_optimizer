"""Skill catalog loader.

Skill cards are Markdown files with a small YAML-ish front-matter block. Agents
(and humans) use this to discover capabilities, signals, and fixes at runtime
without hard-coding. Add a card -> it is auto-discovered.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Dict, List

_DIR = os.path.dirname(__file__)
_FM = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


@dataclass
class Skill:
    skill: str
    agent: List[str] = field(default_factory=list)
    fix_family: str = ""
    categories: List[str] = field(default_factory=list)
    body: str = ""
    path: str = ""


def _parse_list(val: str) -> List[str]:
    val = val.strip()
    if val.startswith("[") and val.endswith("]"):
        return [x.strip() for x in val[1:-1].split(",") if x.strip()]
    return [val] if val else []


def _parse_front_matter(text: str):
    m = _FM.match(text)
    meta: Dict[str, str] = {}
    if not m:
        return meta, text
    fm, body = m.group(1), m.group(2)
    for line in fm.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, body


def load_skills() -> Dict[str, Skill]:
    out: Dict[str, Skill] = {}
    for fn in sorted(os.listdir(_DIR)):
        if not fn.endswith(".md"):
            continue
        path = os.path.join(_DIR, fn)
        with open(path) as fh:
            meta, body = _parse_front_matter(fh.read())
        name = meta.get("skill", fn[:-3])
        out[name] = Skill(
            skill=name,
            agent=_parse_list(meta.get("agent", "")),
            fix_family=meta.get("fix_family", ""),
            categories=_parse_list(meta.get("categories", "")),
            body=body.strip(),
            path=path,
        )
    return out


def get_skill(name: str) -> Skill:
    skills = load_skills()
    if name not in skills:
        raise KeyError(f"Unknown skill '{name}'. Available: {list(skills)}")
    return skills[name]


def skill_for_category(category: str) -> List[Skill]:
    return [s for s in load_skills().values() if category in s.categories]
