"""Shared, stdlib-only selection contract for meta install and sync workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


SCOPES = ("project", "global")
TARGET_KINDS = ("skill", "domain", "all")


@dataclass(frozen=True)
class InstallSelection:
    scope: str | None
    agents: tuple[str, ...]
    target_kind: str | None
    skills: tuple[str, ...]
    domains: tuple[str, ...]
    pending: tuple[str, ...]

    @property
    def selection_required(self) -> bool:
        return bool(self.pending)


def tokens(values: Iterable[str] | None) -> list[str]:
    result: list[str] = []
    for value in values or ():
        result.extend(part.strip() for part in value.split(",") if part.strip())
    return list(dict.fromkeys(result))


def select(
    *,
    scope: str | None,
    agents: Iterable[str] | None,
    target_kind: str | None,
    requested_skills: Iterable[str] | None,
    requested_domains: Iterable[str] | None,
    discovered: Iterable[str],
) -> InstallSelection:
    skills = tuple(tokens(requested_skills))
    domains = tuple(tokens(requested_domains))
    available = tuple(discovered)
    pending: list[str] = []
    if scope not in SCOPES:
        pending.append("scope")
    if target_kind not in TARGET_KINDS:
        pending.append("target_kind")
    if target_kind == "skill" and not skills:
        pending.append("skills")
    if target_kind == "domain" and not domains:
        pending.append("domains")
    if scope == "project" and not tuple(tokens(agents)):
        pending.append("agents")
    if skills == ("*",) and target_kind != "all":
        raise ValueError("--skills '*' requires --target-kind all")
    if target_kind == "skill":
        missing = [name for name in skills if name not in available]
        if missing:
            raise ValueError("requested skills not found in source-dir: " + ", ".join(missing))
        selected = skills
    elif target_kind == "domain":
        selected = tuple(name for name in available if any(name.startswith(f"soia-{domain}-") for domain in domains))
    elif target_kind == "all":
        selected = available
    else:
        selected = ()
    return InstallSelection(scope, tuple(tokens(agents)), target_kind, selected, domains, tuple(pending))
