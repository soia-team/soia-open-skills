#!/usr/bin/env python3
"""Incrementally generate a master Excel catalog and per-partition detail workbooks."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from catalog_xlsx.cache import commit_manifest, default_cache_dir, prepare_incremental


SCRIPT_DIR = Path(__file__).resolve().parent
BUILDER = SCRIPT_DIR / "catalog_xlsx" / "build_workbooks.mjs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="把 OB 云盘馆藏 Markdown 增量生成成轻量总索引 + 分区明细 Excel。"
    )
    parser.add_argument("--catalog", type=Path, required=True, help="馆藏总览 Markdown 文件")
    parser.add_argument("--search-dir", type=Path, required=True, help="分区全文检索 Markdown 目录")
    parser.add_argument("--output", type=Path, required=True, help="总索引 xlsx 输出路径")
    parser.add_argument("--cache-dir", type=Path, help="增量缓存目录；默认按数据源路径生成用户级缓存")
    parser.add_argument("--node", default=os.environ.get("SOIA_ARTIFACT_NODE", "node"), help="Node.js 可执行文件")
    parser.add_argument(
        "--artifact-runtime",
        type=Path,
        default=os.environ.get("SOIA_ARTIFACT_RUNTIME"),
        help="包含 node_modules/@oai/artifact-tool 的运行目录",
    )
    parser.add_argument(
        "--soffice",
        default=os.environ.get("SOIA_SOFFICE"),
        help="可选：LibreOffice/soffice 路径，用于预计算 HYPERLINK 显示值",
    )
    parser.add_argument("--force", action="store_true", help="忽略缓存，重建全部分区")
    parser.add_argument("--verify", action="store_true", help="渲染总索引与本次变化分区的全部工作表")
    parser.add_argument("--json", action="store_true", help="只输出 JSON 结果")
    return parser.parse_args()


def validate_inputs(args: argparse.Namespace) -> None:
    if not args.catalog.is_file():
        raise SystemExit(f"catalog 不存在：{args.catalog}")
    if not args.search_dir.is_dir():
        raise SystemExit(f"search-dir 不存在：{args.search_dir}")
    if args.output.suffix.lower() != ".xlsx":
        raise SystemExit("output 必须以 .xlsx 结尾")
    node = shutil.which(args.node) if os.sep not in args.node else args.node
    if not node or not Path(node).exists():
        raise SystemExit(f"Node.js 不可用：{args.node}")
    args.node = str(Path(node).resolve())
    if not args.artifact_runtime:
        raise SystemExit(
            "缺少 --artifact-runtime：请先让宿主加载 spreadsheet workspace dependencies，"
            "在临时工作目录创建 node_modules 软链后传入该目录。"
        )
    args.artifact_runtime = args.artifact_runtime.resolve()
    package = args.artifact_runtime / "node_modules" / "@oai" / "artifact-tool"
    if not package.exists():
        raise SystemExit(f"artifact runtime 中未找到 @oai/artifact-tool：{package}")
    if args.soffice:
        soffice = shutil.which(args.soffice) if os.sep not in args.soffice else args.soffice
        if not soffice or not Path(soffice).exists():
            raise SystemExit(f"soffice 不可用：{args.soffice}")
        args.soffice = str(Path(soffice).resolve())


def recalculate_with_soffice(soffice: str, outputs: list[Path], cache_dir: Path) -> None:
    for output in outputs:
        if not output.exists():
            raise RuntimeError(f"待重算工作簿不存在：{output}")
        with tempfile.TemporaryDirectory(prefix="recalc-", dir=cache_dir) as temporary:
            command = [soffice, "--headless", "--convert-to", "xlsx", "--outdir", temporary, str(output)]
            process = subprocess.run(command, text=True, capture_output=True, check=False)
            if process.returncode != 0:
                raise RuntimeError(
                    f"LibreOffice 重算失败：{output}\nstdout={process.stdout}\nstderr={process.stderr}"
                )
            recalculated = Path(temporary) / output.name
            if not recalculated.exists():
                raise RuntimeError(f"LibreOffice 未生成重算文件：{recalculated}")
            recalculated.replace(output)


def cleanup_inspection_sidecars(outputs: list[Path]) -> None:
    """清理 artifact-tool inspect 生成的调试文件，只保留正式 xlsx。"""
    for output in outputs:
        Path(f"{output}.inspect.ndjson").unlink(missing_ok=True)


def run() -> dict:
    args = parse_args()
    validate_inputs(args)
    started = time.monotonic()
    cache_dir = (args.cache_dir or default_cache_dir(args.catalog, args.search_dir)).resolve()
    plan = prepare_incremental(
        catalog_path=args.catalog,
        search_dir=args.search_dir,
        output_path=args.output,
        cache_dir=cache_dir,
        force=args.force,
        verify=args.verify,
    )
    changed = plan["changedPartitions"]
    managed_outputs = [Path(plan["outputPath"])]
    managed_outputs.extend(Path(item["output"]) for item in plan["partitions"])
    outputs = []
    if plan["buildMaster"]:
        outputs.append(Path(plan["outputPath"]))
    outputs.extend(Path(item["output"]) for item in plan["partitions"] if item["changed"])

    if outputs:
        environment = os.environ.copy()
        node_options = os.environ.get("SOIA_ARTIFACT_NODE_OPTIONS")
        if node_options:
            environment["NODE_OPTIONS"] = node_options
        command = [
            args.node,
            str(BUILDER),
            "--plan",
            str(cache_dir / "build-plan.json"),
            "--artifact-runtime",
            str(args.artifact_runtime),
        ]
        process = subprocess.run(command, text=True, capture_output=True, env=environment, check=False)
        if process.returncode != 0:
            raise RuntimeError(
                f"artifact-tool 生成失败（缓存未提交，下次会继续重建）：\n"
                f"stdout={process.stdout}\nstderr={process.stderr}"
            )
        if args.soffice:
            recalculate_with_soffice(args.soffice, outputs, cache_dir)
        commit_manifest(plan)
    cleanup_inspection_sidecars(managed_outputs)

    payload = {
        "status": "updated" if outputs else "unchanged",
        "master": plan["outputPath"],
        "detailDir": plan["detailDir"],
        "changedPartitions": changed,
        "rebuilt": [str(item) for item in outputs],
        "reusedPartitions": [item["partition"] for item in plan["partitions"] if not item["changed"]],
        "cacheDir": str(cache_dir),
        "elapsedSeconds": round(time.monotonic() - started, 3),
        "verified": args.verify,
        "recalculated": bool(args.soffice and outputs),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(f"status={payload['status']}")
        print(f"master={payload['master']}")
        print(f"rebuilt={len(payload['rebuilt'])}")
        print(f"changed_partitions={len(changed)}")
        print(f"reused_partitions={len(payload['reusedPartitions'])}")
        print(f"elapsed_seconds={payload['elapsedSeconds']}")
    return payload


if __name__ == "__main__":
    try:
        run()
    except (ValueError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
