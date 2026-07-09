#!/usr/bin/env python3
"""Dry-run or execute a NotebookLM artifact coverage matrix.

Default is safe: print commands only. Pass --run to create a temporary notebook,
add one article source, generate artifacts, and download them.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from soia_env import load_private_env

DEFAULT_HOME = "~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-transform/notebooklm"
NO_LANGUAGE_TARGETS = {"quiz", "flashcards"}


TARGETS: dict[str, dict[str, Any]] = {
    "podcast": {
        "generate": ["generate", "audio", "--format", "deep-dive", "--length", "long"],
        "prompt": "用简体中文生成 8-12 分钟 deep-dive 播客。按 source 章节逐段讲解，覆盖全部主要概念、例子、易混点、风险边界和行动清单；不要只做 1 分钟摘要。",
        "download": ["download", "audio", "--all", "podcast", "--force"],
        "download_path_index": 3,
        "download_glob": "podcast/*.mp3",
        "kind": "binary",
    },
    "video": {
        "generate": ["generate", "video", "--format", "explainer", "--style", "whiteboard"],
        "prompt": "用简体中文生成 6-8 分钟讲解型视频。用白板/关系图风格逐段解释 source 的概念体系、案例链路、易混概念和验收边界；不要只列 3-5 个观点。",
        "download": ["download", "video", "--all", "video", "--force"],
        "download_path_index": 3,
        "download_glob": "video/*.mp4",
        "kind": "binary",
    },
    "cinematic-video": {
        "generate": ["generate", "video", "--format", "cinematic"],
        "prompt": "用纪录片式叙事做 60-90 秒 cinematic overview。视觉上表现“需求、资料、工具、执行、验收”这条链；事实表达必须来自 source，避免夸张和无来源判断。",
        "download": ["download", "video", "--all", "cinematic-video", "--force"],
        "download_path_index": 3,
        "download_glob": "cinematic-video/*.mp4",
        "kind": "binary",
    },
    "ppt": {
        "generate": ["generate", "slide-deck", "--format", "detailed", "--length", "default"],
        "prompt": "生成简体中文 detailed slide deck。若 source 是概念教程，目标 14-18 页；必须覆盖 source 中全部主要概念、章节地图、案例拆解、术语速查、易混概念、流程图、风险边界、自测和来源；不要做短摘要。",
        "download": ["download", "slide-deck", "deck.pptx", "--format", "pptx", "--force"],
        "kind": "binary",
    },
    "infographic": {
        "generate": [
            "generate",
            "infographic",
            "--orientation",
            "portrait",
            "--detail",
            "detailed",
            "--style",
            "professional",
        ],
        "prompt": "生成简体中文高密度信息图，包含 8-12 个信息块、关系/流程、风险和来源提示。",
        "download": ["download", "infographic", "infographic.png", "--force"],
        "kind": "binary",
    },
    "mindmap": {
        "generate": ["generate", "mind-map", "--kind", "note-backed", "--instructions"],
        "prompt": "用简体中文生成层级清晰的知识脑图，保留文章章节、概念关系和关键例子。",
        "download": ["download", "mind-map", "mindmap.json", "--force"],
        "kind": "json",
    },
    "report": {
        "generate": ["generate", "report", "--format", "custom"],
        "prompt": "生成一份简体中文深度 grounded report，不是摘要。结构包含：执行摘要、source 地图、概念覆盖矩阵、逐模块解释、关键案例拆解、易混概念表、风险与边界、行动清单、继续追问和来源说明。覆盖 source 中全部主要概念。",
        "download": ["download", "report", "report.md", "--force"],
        "kind": "text",
    },
    "data-table": {
        "generate": ["generate", "data-table"],
        "prompt": "提取 source 中所有关键概念，生成结构化对照表：术语、所在模块、人话解释、与案例的关系、易混对象、风险/边界、适合做成的产物。",
        "download": ["download", "data-table", "data.csv", "--force"],
        "kind": "text",
    },
    "quiz": {
        "generate": ["generate", "quiz", "--difficulty", "medium", "--quantity", "standard"],
        "prompt": "围绕文章关键概念、易混点和应用场景生成测验，题目必须可由原文回答。",
        "download": ["download", "quiz", "quiz.md", "--format", "markdown", "--force"],
        "kind": "text",
    },
    "flashcards": {
        "generate": ["generate", "flashcards", "--difficulty", "medium", "--quantity", "standard"],
        "prompt": "围绕文章术语、概念、步骤和易错点生成闪卡，每张卡只考一个点。",
        "download": ["download", "flashcards", "flashcards.md", "--format", "markdown", "--force"],
        "kind": "text",
    },
}


def notebooklm_env() -> dict[str, str]:
    load_private_env()
    env = os.environ.copy()
    home = env.get("NOTEBOOKLM_HOME") or str(Path(DEFAULT_HOME).expanduser())
    env["NOTEBOOKLM_HOME"] = home
    env["NOTEBOOKLM_HL"] = env.get("NOTEBOOKLM_HL", "zh_Hans")
    return env


def run_json(cmd: list[str], env: dict[str, str], cwd: Path | None = None) -> dict[str, Any]:
    completed = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            json.dumps(
                {
                    "cmd": cmd,
                    "returncode": completed.returncode,
                    "stdout": completed.stdout[-4000:],
                    "stderr": completed.stderr[-4000:],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    try:
        return json.loads(completed.stdout or "{}")
    except json.JSONDecodeError:
        return {"stdout": completed.stdout, "stderr": completed.stderr}


def error_payload(exc: BaseException) -> dict[str, Any]:
    raw = str(exc)
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    return {"error": True, "message": raw[-4000:]}


def run_plain(cmd: list[str], env: dict[str, str], cwd: Path | None = None) -> dict[str, Any]:
    completed = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    return {
        "cmd": cmd,
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-2000:],
        "stderr_tail": completed.stderr[-2000:],
    }


def find_id(data: Any, preferred: tuple[str, ...] = ("id", "notebook_id", "source_id")) -> str | None:
    if isinstance(data, dict):
        for key in preferred:
            value = data.get(key)
            if isinstance(value, str) and value:
                return value
        for value in data.values():
            found = find_id(value, preferred)
            if found:
                return found
    elif isinstance(data, list):
        for value in data:
            found = find_id(value, preferred)
            if found:
                return found
    return None


def sanitize_auth_check(data: dict[str, Any]) -> dict[str, Any]:
    """Keep auth evidence without leaking browser/cookie inventory."""
    details = data.get("details")
    safe_details: dict[str, Any] = {}
    if isinstance(details, dict):
        for key in ("auth_source", "error", "csrf_length", "session_id_length"):
            if key in details:
                safe_details[key] = details[key]
    return {
        "status": data.get("status"),
        "checks": data.get("checks"),
        "details": safe_details,
    }


def build_generate_command(target: str, notebook_id: str, language: str, timeout: int) -> list[str]:
    spec = TARGETS[target]
    base = ["notebooklm", *spec["generate"]]
    prompt = spec["prompt"]
    if target == "mindmap":
        base.append(prompt)
    else:
        base.append(prompt)
    base.extend(["-n", notebook_id])
    if target not in NO_LANGUAGE_TARGETS:
        base.extend(["--language", language])
    if target != "mindmap":
        base.extend(["--wait", "--timeout", str(timeout), "--json"])
    else:
        base.extend(["--json"])
    return base


def build_download_command(target: str, notebook_id: str, out_dir: Path) -> list[str]:
    spec = TARGETS[target]
    args = list(spec["download"])
    path_index = spec.get("download_path_index", 2)
    if len(args) > path_index:
        args[path_index] = str(out_dir / args[path_index])
    return ["notebooklm", *args, "-n", notebook_id, "--json"]


def validate_download(target: str, out_dir: Path) -> dict[str, Any]:
    spec = TARGETS[target]
    if "download_glob" in spec:
        paths = sorted(out_dir.glob(spec["download_glob"]))
        result: dict[str, Any] = {
            "glob": str(out_dir / spec["download_glob"]),
            "exists": bool(paths),
            "paths": [str(path) for path in paths],
            "count": len(paths),
        }
        if paths:
            result["bytes"] = sum(path.stat().st_size for path in paths)
            result["non_empty"] = all(path.stat().st_size > 1024 for path in paths)
            result["ok"] = result["non_empty"]
        else:
            result["ok"] = False
        return result
    filename = spec["download"][2]
    path = out_dir / filename
    result: dict[str, Any] = {"path": str(path), "exists": path.exists()}
    if path.exists():
        result["bytes"] = path.stat().st_size
        if spec["kind"] == "json":
            try:
                json.loads(path.read_text(encoding="utf-8"))
                result["json_valid"] = True
                result["ok"] = True
            except Exception as exc:  # noqa: BLE001
                result["json_valid"] = False
                result["json_error"] = str(exc)
                result["ok"] = False
        elif spec["kind"] == "text":
            result["non_empty"] = bool(path.read_text(encoding="utf-8", errors="replace").strip())
            result["ok"] = result["non_empty"]
        else:
            result["non_empty"] = path.stat().st_size > 1024
            result["ok"] = result["non_empty"]
    else:
        result["ok"] = False
    return result


def plan_commands(article: Path, out_dir: Path, targets: list[str], title: str, language: str, timeout: int) -> dict[str, Any]:
    notebook = "<notebook-id>"
    return {
        "mode": "dry-run",
        "article": str(article),
        "out_dir": str(out_dir),
        "commands": {
            "health": [
                "python3 scripts/notebooklm_health.py --ensure-home --json",
                'NOTEBOOKLM_HOME="$NOTEBOOKLM_HOME" notebooklm auth check --test --json',
            ],
            "create": ["notebooklm", "create", title, "--json"],
            "source_add": ["notebooklm", "source", "add", str(article), "-n", notebook, "--type", "file", "--json"],
            "targets": {
                target: {
                    "generate": build_generate_command(target, notebook, language, timeout),
                    "download": build_download_command(target, notebook, out_dir),
                }
                for target in targets
            },
        },
    }


def execute(args: argparse.Namespace, targets: list[str]) -> dict[str, Any]:
    env = notebooklm_env()
    article = Path(args.article).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if shutil.which("notebooklm") is None:
        raise RuntimeError("notebooklm CLI not found on PATH")

    raw_health = run_json(["notebooklm", "auth", "check", "--test", "--json"], env)
    health = sanitize_auth_check(raw_health)
    if raw_health.get("status") != "ok":
        raise RuntimeError(f"NotebookLM auth check failed: {health}")

    title = args.notebook_title or f"soia-transform-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    created = run_json(["notebooklm", "create", title, "--json"], env)
    notebook_id = find_id(created, ("id", "notebook_id"))
    if not notebook_id:
        raise RuntimeError(f"Could not parse notebook id from: {created}")

    result: dict[str, Any] = {
        "mode": "run",
        "notebook_id": notebook_id,
        "notebook_title": title,
        "article": str(article),
        "out_dir": str(out_dir),
        "health": health,
        "targets": {},
    }
    try:
        source = run_json(
            ["notebooklm", "source", "add", str(article), "-n", notebook_id, "--type", "file", "--json"],
            env,
        )
        source_id = find_id(source, ("source_id", "id"))
        result["source"] = source
        result["source_id"] = source_id
        if source_id:
            result["source_wait"] = run_plain(
                ["notebooklm", "source", "wait", source_id, "-n", notebook_id, "--timeout", str(args.timeout), "--json"],
                env,
            )

        for target in targets:
            generate_cmd = build_generate_command(target, notebook_id, args.language, args.timeout)
            download_cmd = build_download_command(target, notebook_id, out_dir)
            entry: dict[str, Any] = {"generate_cmd": generate_cmd, "download_cmd": download_cmd}
            try:
                entry["generate"] = run_json(generate_cmd, env)
            except Exception as exc:
                entry["status"] = "generate_failed"
                entry["error"] = error_payload(exc)
                result["targets"][target] = entry
                if args.stop_on_error:
                    raise
                continue
            try:
                entry["download"] = run_json(download_cmd, env)
            except Exception as exc:
                entry["status"] = "download_failed"
                entry["error"] = error_payload(exc)
                entry["validation"] = validate_download(target, out_dir)
                result["targets"][target] = entry
                if args.stop_on_error:
                    raise
                continue
            entry["validation"] = validate_download(target, out_dir)
            entry["status"] = "ok" if entry["validation"].get("ok") else "validation_failed"
            result["targets"][target] = entry
    finally:
        if not args.keep_notebook:
            result["delete"] = run_plain(["notebooklm", "delete", "-n", notebook_id, "-y", "--json"], env)
    result["summary"] = {
        "ok": [name for name, item in result["targets"].items() if item.get("status") == "ok"],
        "failed": {
            name: item.get("status")
            for name, item in result["targets"].items()
            if item.get("status") != "ok"
        },
    }
    return result


def parse_targets(raw: str) -> list[str]:
    if raw == "all":
        return list(TARGETS)
    targets = [part.strip() for part in raw.split(",") if part.strip()]
    unknown = [target for target in targets if target not in TARGETS]
    if unknown:
        raise SystemExit(f"Unknown targets: {', '.join(unknown)}. Known: {', '.join(TARGETS)}")
    return targets


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--article", required=True, help="Article Markdown/file path to upload.")
    parser.add_argument("--out-dir", required=True, help="Directory for downloaded artifacts.")
    parser.add_argument("--targets", default="all", help="Comma-separated targets or all.")
    parser.add_argument("--language", default=os.environ.get("NOTEBOOKLM_HL", "zh_Hans"))
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--notebook-title", help="Temporary notebook title.")
    parser.add_argument("--run", action="store_true", help="Actually create notebook and generate/download artifacts.")
    parser.add_argument("--keep-notebook", action="store_true", help="Keep the temporary notebook after --run.")
    parser.add_argument("--stop-on-error", action="store_true", help="Stop at first target failure instead of recording and continuing.")
    parser.add_argument("--json", action="store_true", help="Print JSON.")
    args = parser.parse_args()

    article = Path(args.article).expanduser().resolve()
    if not article.is_file():
        raise SystemExit(f"Article not found: {article}")
    targets = parse_targets(args.targets)
    title = args.notebook_title or f"soia-transform-test-{article.stem[:40]}"
    out_dir = Path(args.out_dir).expanduser()

    result = (
        execute(args, targets)
        if args.run
        else plan_commands(article, out_dir, targets, title, args.language, args.timeout)
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
