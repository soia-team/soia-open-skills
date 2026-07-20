#!/usr/bin/env python3
"""List functional Open Design skills from the local daemon."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from typing import Any

from daemon_ctl import daemon_url, validate_daemon_url
from open_design_env import load_private_env


def parse_skill_payload(payload: Any, category: str | None = None) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("skills"), list):
        raise ValueError("daemon response does not contain a skills list")
    expected_category = category.casefold() if category else None
    parsed: list[dict[str, Any]] = []
    for item in payload["skills"]:
        if not isinstance(item, dict):
            continue
        item_category = item.get("category") if isinstance(item.get("category"), str) else None
        if expected_category and (item_category or "").casefold() != expected_category:
            continue
        name = item.get("name") if isinstance(item.get("name"), str) else item.get("id")
        if not isinstance(name, str) or not name:
            continue
        description = item.get("description") if isinstance(item.get("description"), str) else ""
        mode = item.get("mode") if isinstance(item.get("mode"), str) else ""
        parsed.append(
            {
                "name": name,
                "description": description,
                "od": {"mode": mode},
                "category": item_category,
            }
        )
    return sorted(parsed, key=lambda value: value["name"].casefold())


def fetch_skills(base_url: str, timeout: float = 5.0) -> Any:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/skills",
        headers={"Accept": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--category", help="Exact category filter applied locally.")
    parser.add_argument("--daemon-url", help="Loopback daemon URL override.")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args(argv)
    load_private_env(required=False)
    try:
        base_url = validate_daemon_url(args.daemon_url) if args.daemon_url else daemon_url()
        payload = fetch_skills(base_url, args.timeout)
        skills = parse_skill_payload(payload, args.category)
    except (ValueError, OSError, urllib.error.URLError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(json.dumps({"status": "error", "error": type(exc).__name__}, sort_keys=True))
        return 1
    print(json.dumps({"status": "ok", "count": len(skills), "skills": skills}, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
