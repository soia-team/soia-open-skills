#!/usr/bin/env python3
"""Resolve soia-pkm-transform target/provider routes to prompt files."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import resolve_config


SKILL_ROOT = Path(__file__).resolve().parents[1]
REFERENCES_DIR = SKILL_ROOT / "references"

TARGET_ALIASES = {
    "deck": "ppt",
    "slide": "ppt",
    "slides": "ppt",
    "slide-deck": "ppt",
    "pptx": "ppt",
    "long-image": "long_image",
    "longimage": "long_image",
    "poster": "infographic",
    "image": "image",
    "infograph": "infographic",
    "exam": "quiz",
    "test": "quiz",
    "audio": "podcast",
    "cinematic_video": "cinematic-video",
    "mind-map": "mindmap",
    "mind_map": "mindmap",
    "datatable": "data_table",
    "data-table": "data_table",
}

PROVIDER_ALIASES = {
    "auto": "auto",
    "codex": "local",
    "presentations": "local",
    "local_presentation": "local",
    "html_deck": "local",
    "local_markdown": "local",
    "imagegen": "codex_image",
    "gpt-image-2": "codex_image",
    "image2": "codex_image",
    "codex-image": "codex_image",
    "notebooklm-py": "notebooklm",
    "open-design": "open_design",
}

DEFAULT_CONTENT_MODE = {
    "pdf": "preserve",
    "ppt": "learning",
    "image": "visual_dense",
    "long_image": "visual_dense",
    "infographic": "visual_dense",
    "quiz": "learning",
    "mindmap": "synthesize",
    "podcast": "synthesize",
    "video": "synthesize",
    "cinematic-video": "synthesize",
    "flashcards": "learning",
    "data_table": "synthesize",
    "report": "synthesize",
    "wechat": "synthesize",
    "x_thread": "synthesize",
    "xhs": "synthesize",
}

DEFAULT_PROVIDER = {
    "pdf": "obsidian",
    "ppt": "local",
    "image": "codex_image",
    "long_image": "local_visual",
    "infographic": "local_visual",
    "quiz": "notebooklm",
    "mindmap": "notebooklm",
    "podcast": "notebooklm",
    "video": "notebooklm",
    "cinematic-video": "notebooklm",
    "flashcards": "notebooklm",
    "data_table": "notebooklm",
    "report": "local",
    "wechat": "publish",
    "x_thread": "publish",
    "xhs": "publish",
}

DEFAULT_PROMPT_ROUTES: dict[str, dict[str, str]] = {
    "ppt": {
        "local": "prompt-ppt.md",
        "local_visual": "prompt-ppt.md",
        "open_design": "prompt-open-design.md",
        "notebooklm": "prompt-notebooklm-ppt.md",
    },
    "image": {
        "codex_image": "prompt-codex-image.md",
        "local_visual": "prompt-infographic.md",
        "open_design": "prompt-open-design.md",
        "notebooklm": "prompt-notebooklm-image.md",
    },
    "long_image": {
        "local_visual": "prompt-infographic.md",
        "open_design": "prompt-open-design.md",
        "notebooklm": "prompt-notebooklm-image.md",
    },
    "infographic": {
        "local_visual": "prompt-infographic.md",
        "open_design": "prompt-open-design.md",
        "notebooklm": "prompt-notebooklm-image.md",
    },
    "quiz": {
        "notebooklm": "prompt-notebooklm-quiz.md",
    },
    "flashcards": {
        "notebooklm": "prompt-notebooklm-flashcards.md",
    },
    "mindmap": {
        "notebooklm": "prompt-notebooklm-mindmap.md",
    },
    "podcast": {
        "notebooklm": "prompt-notebooklm-podcast.md",
    },
    "video": {
        "notebooklm": "prompt-notebooklm-podcast.md",
    },
    "cinematic-video": {
        "notebooklm": "prompt-notebooklm-podcast.md",
    },
    "data_table": {
        "notebooklm": "prompt-notebooklm-report.md",
    },
    "report": {
        "local": "prompt-report.md",
        "notebooklm": "prompt-notebooklm-report.md",
    },
}


def normalize_target(target: str) -> str:
    value = target.strip().lower().replace(" ", "_")
    return TARGET_ALIASES.get(value, value)


def normalize_provider(provider: str) -> str:
    value = provider.strip().lower().replace(" ", "_")
    return PROVIDER_ALIASES.get(value, value)


def load_config(cwd: Path) -> tuple[dict[str, Any], str | None, str | None]:
    found = next((p for p in resolve_config.candidate_paths(cwd) if p.is_file()), None)
    if not found:
        return {}, None, None
    config, warning = resolve_config.load_if_possible(found)
    if isinstance(config, dict):
        return config, str(found), warning
    return {}, str(found), warning


def merge_prompt_routes(config: dict[str, Any]) -> dict[str, dict[str, str]]:
    routes = {target: providers.copy() for target, providers in DEFAULT_PROMPT_ROUTES.items()}
    raw_routes = config.get("prompt_routes")
    if not isinstance(raw_routes, dict):
        return routes

    for raw_target, raw_provider_map in raw_routes.items():
        target = normalize_target(str(raw_target))
        if not isinstance(raw_provider_map, dict):
            continue
        routes.setdefault(target, {})
        for raw_provider, prompt_file in raw_provider_map.items():
            provider = normalize_provider(str(raw_provider))
            if isinstance(prompt_file, str):
                routes[target][provider] = prompt_file
    return routes


def infer_image_target(target: str, image_subtype: str | None) -> str:
    if target != "image":
        return target
    subtype = (image_subtype or "").strip().lower()
    if subtype in {"long_image", "long-image"}:
        return "long_image"
    if subtype == "infographic":
        return "infographic"
    return target


def default_provider_for(target: str, provider: str) -> str:
    if provider != "auto":
        return provider
    return DEFAULT_PROVIDER.get(target, "local")


def references_for(target: str, prompt_file: str | None, provider: str) -> list[str]:
    refs = ["references/output-recipes.md", "references/quality-gates.md"]
    if target in {"ppt", "image", "long_image", "infographic", "report"}:
        refs.insert(0, "references/design-prompts.md")
    if provider in {"local", "local_visual", "codex_image", "obsidian", "publish"}:
        refs.append("references/provider-soia-local.md")
    if provider == "notebooklm":
        refs.extend([
            "references/providers.md",
            "references/provider-notebooklm.md",
        ])
    if provider == "open_design":
        refs.extend([
            "references/providers.md",
            "references/provider-open-design.md",
        ])
    if target in {
        "podcast",
        "video",
        "cinematic-video",
        "ppt",
        "quiz",
        "flashcards",
        "mindmap",
        "report",
        "infographic",
        "data_table",
    } and provider == "notebooklm":
        refs.append("references/notebooklm-test-matrix.md")
    if prompt_file:
        refs.append(f"references/{prompt_file}")
    return list(dict.fromkeys(refs))


def resolve(args: argparse.Namespace) -> dict[str, Any]:
    target = infer_image_target(normalize_target(args.target), args.image_subtype)
    provider = default_provider_for(target, normalize_provider(args.provider))
    config, config_path, warning = load_config(Path(args.cwd).expanduser())
    routes = merge_prompt_routes(config)

    provider_routes = routes.get(target, {})
    prompt_file = provider_routes.get(provider)
    if prompt_file is None and provider == "codex_image" and target in {"long_image", "infographic"}:
        prompt_file = provider_routes.get("local_visual")

    available = sorted(provider_routes)
    errors: list[str] = []
    notes: list[str] = []
    if prompt_file is None and target not in {"pdf", "wechat", "x_thread", "xhs"}:
        errors.append(f"no prompt route for target={target!r}, provider={provider!r}")
    if provider == "codex_image" and target in {"long_image", "infographic"}:
        notes.append("codex_image is only for visual assets; use local_visual for dense Chinese layout.")

    prompt_path = REFERENCES_DIR / prompt_file if prompt_file else None
    if prompt_path and not prompt_path.is_file():
        errors.append(f"prompt file does not exist: references/{prompt_file}")

    result: dict[str, Any] = {
        "target": target,
        "provider": provider,
        "content_mode": DEFAULT_CONTENT_MODE.get(target, "synthesize"),
        "prompt_file": prompt_file,
        "reference_files": references_for(target, prompt_file, provider),
        "available_providers": available,
        "config_path": config_path,
        "warning": warning,
        "notes": notes,
        "errors": errors,
    }
    return result


def list_routes(cwd: Path) -> dict[str, Any]:
    config, config_path, warning = load_config(cwd)
    routes = merge_prompt_routes(config)
    return {
        "prompt_routes": routes,
        "default_providers": DEFAULT_PROVIDER,
        "default_content_mode": DEFAULT_CONTENT_MODE,
        "config_path": config_path,
        "warning": warning,
    }


def print_text(result: dict[str, Any]) -> None:
    print(f"target: {result['target']}")
    print(f"provider: {result['provider']}")
    print(f"content_mode: {result['content_mode']}")
    if result["prompt_file"]:
        print(f"prompt: references/{result['prompt_file']}")
    if result["available_providers"]:
        print(f"available_providers: {', '.join(result['available_providers'])}")
    print("read:")
    for ref in result["reference_files"]:
        print(f"  - {ref}")
    for note in result["notes"]:
        print(f"note: {note}")
    for error in result["errors"]:
        print(f"error: {error}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve transform target/provider prompt route.")
    parser.add_argument("--target", help="Target output: ppt, image, long_image, quiz, report, ...")
    parser.add_argument("--provider", default="auto", help="Provider: auto, local, notebooklm, codex_image, ...")
    parser.add_argument("--image-subtype", help="Image subtype: cover_image, illustration, long_image, infographic.")
    parser.add_argument("--cwd", default=os.getcwd(), help="Directory used for config discovery.")
    parser.add_argument("--json", action="store_true", help="Print JSON result.")
    parser.add_argument("--list", action="store_true", help="List all known prompt routes.")
    args = parser.parse_args()

    if args.list:
        result = list_routes(Path(args.cwd).expanduser())
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            for target, providers in result["prompt_routes"].items():
                print(target)
                for provider, prompt in providers.items():
                    print(f"  {provider}: references/{prompt}")
        return 0

    if not args.target:
        parser.error("--target is required unless --list is used")

    result = resolve(args)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_text(result)
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
