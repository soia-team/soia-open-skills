#!/usr/bin/env python3
"""SOIA 全生态图形资产的单一真源：一张表 → 三个面。

之前配色与字形表只存在于会话临时目录里，不在任何仓；结果是同一套图标在
元仓 assets/plugins/、8 个域仓 assets/、以及 WorkBuddy 专家头像里各存一份副本，
共 19 处，没有任何东西保证它们同源。这个脚本把那张表收进仓里，三个面全部由它派生。

三个面（同一字形与配色，只是承载surface不同）：

    marketplace  assets/plugins/<插件>.svg|png   元仓市场条目，安装前就要显示
    plugin       <域仓>/assets/icon.svg|png      该仓 .codex-plugin 的 composerIcon/logo
    avatar       experts/<专家>/avatar.svg|png   WorkBuddy 专家头像，圆形无标签

brandColor 也从这张表出，写进清单时不用手抄，避免图标换色而清单还留着旧色号
（实测发生过：图标已是紫色系，8 个 brandColor 仍是琥珀期的橙色）。

PNG 需要 cairosvg（仅维护者用，不进运行时依赖）：
    python3 -m pip install cairosvg
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

SIZE = 1024
RADIUS = 230        # 圆角，接近 iOS squircle 观感
GLYPH_CY = 452      # 带标签时字形中心 Y，给底部标签留位
GLYPH_CY_BARE = 512  # 无标签（头像）时字形居中
STROKE = 40
LABEL_Y = 838
LABEL_SIZE = 108

# 插件 → (标签, 深色停, 浅色停, 强调色)
# 家族感靠结构（同圆角、同渐变构造、同线宽），辨识度靠色相偏移 + 字形。
PALETTE: dict[str, tuple[str, str, str, str]] = {
    "soia-dev": ("coding", "#312E81", "#6366F1", "#C7D2FE"),
    "soia-dev-design": ("design", "#4C1D95", "#8B5CF6", "#DDD6FE"),
    "soia-pkm-vault": ("vault", "#1E1B4B", "#4F46E5", "#C7D2FE"),
    "soia-media-content": ("media", "#3730A3", "#5B5CE2", "#D6D6FF"),
    "soia-cwork-office": ("cowork", "#1E3A8A", "#3B82F6", "#DBEAFE"),
    "soia-edu-course": ("course", "#5B21B6", "#A78BFA", "#EDE9FE"),
    "soia-env": ("env", "#164E63", "#6366F1", "#CFFAFE"),
    "soia-meta": ("meta", "#2E1065", "#7C3AED", "#E9D5FF"),
    "soia-gov": ("gov", "#3B0764", "#9333EA", "#F3E8FF"),
    "soia-workspace": ("workspace", "#581C87", "#C026D3", "#FAE8FF"),
    "soia-corp": ("corp", "#172554", "#2563EB", "#DBEAFE"),
    "soia-harness": ("harness", "#27272A", "#71717A", "#E4E4E7"),
}

# 字形：以 (0,0) 为中心、约 470 见方的框内作图
GLYPHS: dict[str, str] = {
    "soia-dev": """
      <polyline points="-150,-70 -228,0 -150,70"/>
      <line x1="-40" y1="105" x2="40" y2="-105"/>
      <polyline points="150,-70 228,0 150,70"/>""",
    "soia-dev-design": """
      <polygon points="-200,110 60,110 -70,-115"/>
      <line x1="95" y1="-120" x2="215" y2="-120"/>
      <line x1="155" y1="-120" x2="155" y2="120"/>
      <line x1="95" y1="120" x2="215" y2="120"/>""",
    "soia-pkm-vault": """
      <rect x="-205" y="-165" width="410" height="330" rx="34"/>
      <circle cx="20" cy="0" r="98"/>
      <line x1="20" y1="-150" x2="20" y2="-98"/>
      <line x1="20" y1="98" x2="20" y2="150"/>
      <line x1="-70" y1="0" x2="-118" y2="0"/>
      <line x1="118" y1="0" x2="166" y2="0"/>""",
    "soia-media-content": """
      <polygon points="-215,-25 215,-165 95,175 -10,60"/>
      <line x1="-10" y1="60" x2="215" y2="-165"/>""",
    "soia-cwork-office": """
      <path d="M-160,-185 L60,-185 L160,-85 L160,185 L-160,185 Z"/>
      <polyline points="60,-185 60,-85 160,-85"/>
      <line x1="-88" y1="35" x2="88" y2="35"/>
      <line x1="-88" y1="112" x2="40" y2="112"/>""",
    "soia-edu-course": """
      <polygon points="0,-155 235,-45 0,65 -235,-45"/>
      <path d="M-135,-3 L-135,120 A135,72 0 0 0 135,120 L135,-3"/>""",
    "soia-env": """
      <circle cx="0" cy="0" r="82"/>
      <path d="M0,-215 L46,-172 L46,-150 L106,-116 L128,-124 L182,-98
               L166,-38 L150,-22 L150,22 L166,38 L182,98 L128,124 L106,116
               L46,150 L46,172 L0,215 L-46,172 L-46,150 L-106,116 L-128,124
               L-182,98 L-166,38 L-150,22 L-150,-22 L-166,-38 L-182,-98
               L-128,-124 L-106,-116 L-46,-150 L-46,-172 Z"/>""",
    "soia-meta": """
      <circle cx="0" cy="0" r="62"/>
      <circle cx="0" cy="0" r="165"/>
      <line x1="0" y1="-165" x2="0" y2="-225"/>
      <line x1="143" y1="82" x2="195" y2="112"/>
      <line x1="-143" y1="82" x2="-195" y2="112"/>""",
    "soia-gov": """
      <circle cx="0" cy="-172" r="40"/>
      <line x1="0" y1="-132" x2="0" y2="150"/>
      <line x1="-198" y1="-150" x2="198" y2="-150"/>
      <line x1="-198" y1="-150" x2="-198" y2="-40"/>
      <line x1="198" y1="-150" x2="198" y2="-40"/>
      <path d="M-286,-40 L-110,-40 A88,96 0 0 1 -286,-40 Z"/>
      <path d="M110,-40 L286,-40 A88,96 0 0 1 110,-40 Z"/>
      <line x1="-96" y1="196" x2="96" y2="196"/>
      <path d="M-48,150 L48,150 L62,196 L-62,196 Z"/>""",
    "soia-workspace": """
      <rect x="-215" y="-175" width="430" height="300" rx="30"/>
      <line x1="-215" y1="55" x2="215" y2="55"/>
      <line x1="0" y1="125" x2="0" y2="185"/>
      <line x1="-110" y1="212" x2="110" y2="212"/>
      <circle cx="-115" cy="-62" r="34"/>
      <line x1="-30" y1="-10" x2="145" y2="-10"/>
      <line x1="-30" y1="-108" x2="145" y2="-108"/>""",
    "soia-corp": """
      <path d="M0,-210 L200,-140 L200,20 A200,240 0 0 1 0,215
               A200,240 0 0 1 -200,20 L-200,-140 Z"/>
      <polyline points="-88,5 -22,72 96,-58"/>""",
    "soia-harness": """
      <path d="M-172,-40 A172,172 0 0 1 118,-125"/>
      <polyline points="60,-172 132,-128 88,-56"/>
      <path d="M172,40 A172,172 0 0 1 -118,125"/>
      <polyline points="-60,172 -132,128 -88,56"/>
      <circle cx="0" cy="0" r="52"/>""",
}

# 专家 → (借用哪个插件的配色, 字形覆盖或 None)
#
# 头像沿用所属域插件的色相，让「召唤哪个专家」与「装了哪个域插件」在视觉上对得上。
# 只有知识库管家需要换字形：域插件是保险柜，但那张图靠底部 vault 标签才不歧义，
# 头像没有标签位，保险柜在小尺寸下被认成相机，故改用摊开的书。
EXPERTS: dict[str, tuple[str, str | None]] = {
    "soia-vault-curator": ("soia-pkm-vault", """
      <path d="M0,-108 C-62,-158 -148,-158 -200,-132 L-200,118
               C-148,92 -62,92 0,142 C62,92 148,92 200,118 L200,-132
               C148,-158 62,-158 0,-108 Z"/>
      <line x1="0" y1="-108" x2="0" y2="142"/>"""),
    "soia-content-operator": ("soia-media-content", None),
    "soia-office-aide": ("soia-cwork-office", None),
}

# 域仓 → 该仓各 plugin root 对应的插件名。私有仓不在本仓工作副本里，
# 但表放这儿，指向它的克隆时同样可用。
DEPLOY_TARGETS: dict[str, list[tuple[str, str]]] = {
    "soia-open-dev-skills": [(".", "soia-dev")],
    "soia-open-dev-design-skills": [(".", "soia-dev-design")],
    "soia-open-pkm-vault-skills": [(".", "soia-pkm-vault")],
    "soia-open-media-content-skills": [(".", "soia-media-content")],
    "soia-open-cwork-office-skills": [(".", "soia-cwork-office")],
    "soia-open-edu-course-skills": [(".", "soia-edu-course")],
    "soia-open-env-skills": [(".", "soia-env")],
    "soia-open-skills": [(".", "soia-meta")],
    "soia-private-corp-skills": [(".", "soia-corp")],
    "soia-private-skills": [
        (".", "soia-gov"),
        ("workspace", "soia-workspace"),
        ("harness", "soia-harness"),
    ],
}

_DEFS = """  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0.35" y2="1">
      <stop offset="0" stop-color="{light}"/>
      <stop offset="1" stop-color="{dark}"/>
    </linearGradient>
    <linearGradient id="sheen" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#FFFFFF" stop-opacity="0.30"/>
      <stop offset="0.55" stop-color="#FFFFFF" stop-opacity="0.04"/>
      <stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="ink" x1="0" y1="0" x2="0.3" y2="1">
      <stop offset="0" stop-color="#FFFFFF"/>
      <stop offset="1" stop-color="{accent}"/>
    </linearGradient>
{extra}  </defs>
"""

# 字形先画一层下沉暗影再画本体，制造轻微厚度
_GLYPH_GROUP = """    <g transform="translate({cx},{gy})" fill="none" stroke-width="{stroke}"
       stroke-linecap="round" stroke-linejoin="round">
      <g stroke="{dark}" opacity="0.38" transform="translate(0,14)">{glyph}</g>
      <g stroke="url(#ink)">{glyph}</g>
    </g>
"""


def render(plugin: str, *, labelled: bool, round_crop: bool,
           glyph_override: str | None = None) -> str:
    """渲染一张图。labelled 决定底部是否带标签，round_crop 决定方角还是圆形。"""
    label, dark, light, accent = PALETTE[plugin]
    glyph = glyph_override if glyph_override is not None else GLYPHS[plugin]
    cx = SIZE // 2
    gy = GLYPH_CY if labelled else GLYPH_CY_BARE

    extra = (f'    <clipPath id="round"><circle cx="{cx}" cy="{cx}" r="{cx}"/></clipPath>\n'
             if round_crop else "")
    defs = _DEFS.format(light=light, dark=dark, accent=accent, extra=extra)

    shape = (f'<rect width="{SIZE}" height="{SIZE}" rx="{RADIUS}" fill="url(#{{grad}})"/>'
             if not round_crop else
             f'<rect width="{SIZE}" height="{SIZE}" fill="url(#{{grad}})"/>')
    body = [
        "    " + shape.format(grad="bg"),
        "    " + shape.format(grad="sheen"),
        _GLYPH_GROUP.format(cx=cx, gy=gy, stroke=STROKE, dark=dark, glyph=glyph).rstrip(),
    ]
    if labelled:
        body.append(
            f'    <text x="{cx}" y="{LABEL_Y}" text-anchor="middle"\n'
            f'          font-family="Helvetica Neue, Helvetica, Arial, sans-serif"\n'
            f'          font-size="{LABEL_SIZE}" font-weight="600" letter-spacing="4"\n'
            f'          fill="#FFFFFF" fill-opacity="0.94">{label}</text>'
        )
    inner = "\n".join(body)
    if round_crop:
        inner = f'  <g clip-path="url(#round)">\n{inner}\n  </g>'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SIZE}" height="{SIZE}" '
        f'viewBox="0 0 {SIZE} {SIZE}">\n{defs}\n{inner}\n</svg>\n'
    )


def write_pair(svg_path: pathlib.Path, png_path: pathlib.Path, svg: str,
               cairosvg, check: bool, drift: list[str]) -> None:
    """写 SVG/PNG；--check 模式下只比对不写，用于 CI 拦住手改。"""
    if check:
        if not svg_path.exists() or svg_path.read_text(encoding="utf-8") != svg:
            drift.append(str(svg_path))
        return
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(svg, encoding="utf-8")
    if cairosvg is not None:
        cairosvg.svg2png(url=str(svg_path), write_to=str(png_path),
                         output_width=SIZE, output_height=SIZE)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true",
                        help="只比对 SVG 是否与表一致，不写文件（CI 用）")
    parser.add_argument("--deploy", type=pathlib.Path, metavar="REPO_ROOT",
                        help="把 plugin 面写进指定域仓的 assets/ 并同步其清单 brandColor")
    args = parser.parse_args(argv)

    try:
        import cairosvg
    except ImportError:
        cairosvg = None
    if cairosvg is None and not args.check:
        print("⚠️  未装 cairosvg，只写 SVG 不生成 PNG：python3 -m pip install cairosvg")

    if args.deploy:
        return deploy(args.deploy.resolve(), cairosvg)

    drift: list[str] = []
    for plugin in sorted(PALETTE):
        svg = render(plugin, labelled=True, round_crop=False)
        base = REPO_ROOT / "assets/plugins" / plugin
        write_pair(base.with_suffix(".svg"), base.with_suffix(".png"), svg,
                   cairosvg, args.check, drift)
    for expert, (plugin, glyph) in sorted(EXPERTS.items()):
        svg = render(plugin, labelled=False, round_crop=True, glyph_override=glyph)
        base = REPO_ROOT / "experts" / expert / "avatar"
        write_pair(base.with_suffix(".svg"), base.with_suffix(".png"), svg,
                   cairosvg, args.check, drift)

    if args.check:
        if drift:
            print("❌ 以下资产与配色表不一致，请重跑 generate_icons.py：")
            for path in drift:
                print(f"   {pathlib.Path(path).relative_to(REPO_ROOT)}")
            return 1
        print(f"icons are current ({len(PALETTE)} 插件 + {len(EXPERTS)} 专家头像)")
        return 0

    print(f"  ✓ {len(PALETTE)} 个插件图标 → assets/plugins/")
    print(f"  ✓ {len(EXPERTS)} 张专家头像 → experts/*/avatar.*")
    return 0


def deploy(repo_root: pathlib.Path, cairosvg) -> int:
    """把 plugin 面写进某个域仓，并把 brandColor 同步进它的 Codex 清单。"""
    targets = DEPLOY_TARGETS.get(repo_root.name)
    if not targets:
        print(f"❌ 未知仓：{repo_root.name}", file=sys.stderr)
        return 2
    for sub, plugin in targets:
        root = repo_root if sub == "." else repo_root / sub
        svg = render(plugin, labelled=True, round_crop=False)
        write_pair(root / "assets/icon.svg", root / "assets/icon.png", svg,
                   cairosvg, check=False, drift=[])

        manifest = root / ".codex-plugin/plugin.json"
        if not manifest.exists():
            print(f"  ✓ {plugin}: 已写 assets/（该 root 无 Codex 清单）")
            continue
        data = json.loads(manifest.read_text(encoding="utf-8"))
        iface = data.setdefault("interface", {})
        iface["composerIcon"] = "./assets/icon.svg"
        iface["logo"] = "./assets/icon.png"
        iface["brandColor"] = PALETTE[plugin][2]
        manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
        print(f"  ✓ {plugin}: assets/ 与 Codex 清单 brandColor={PALETTE[plugin][2]}")
    print("\n  注意：改动会随插件发布生效，记得 bump 双份 plugin.json 的 version。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
