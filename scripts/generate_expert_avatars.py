#!/usr/bin/env python3
"""确定性生成 WorkBuddy 专家头像：SVG 母版 → PNG。

官方 avatar-spec 建议用 ImageGen 画角色肖像；这里改用代码重绘的角色徽标，
理由是可复现——同一次提交永远得到同一张图，新增专家时家族观感不会漂移。
视觉语言沿用 assets/plugins/ 的插件图标：同一渐变构造、同一线宽、同一圆角语汇，
只把域字形换成角色字形，让「专家」与「它背后的域插件」在视觉上认得出是一家。

PNG 需要 cairosvg（仅维护者用，不进运行时依赖）：
    python3 -m pip install cairosvg
无 cairosvg 时只写 SVG 并提示，不报错退出——SVG 本身也是要提交的产物。
"""
from __future__ import annotations

import argparse
import pathlib
import sys

SIZE = 1024
STROKE = 44
GLYPH_CY = 512  # 头像是圆形裁切，字形居中，不留标签位

# 取各专家对应域插件的色相，专家与插件在市场里一眼能对上号
AVATARS = {
    # name,                   深色停,     浅色停,    强调色
    "soia-vault-curator": ("#1E1B4B", "#4F46E5", "#C7D2FE"),
    "soia-content-operator": ("#3730A3", "#5B5CE2", "#D6D6FF"),
    "soia-office-aide": ("#1E3A8A", "#3B82F6", "#DBEAFE"),
}

# 字形：以 (0,0) 为中心作图，直接沿用该专家所属域插件的字形。
#
# 第一版画的是「人物半身 + 职业道具」，实测在头像尺寸下道具糊成一团——
# 书被认成领结。域字形本来就是照小尺寸可读设计的，直接复用既解决可读性，
# 又让「召唤哪个专家」和「装了哪个域插件」在视觉上对得上号。
GLYPHS = {
    # 摊开的书：知识库。
    # 域插件用的是保险柜字形，但那张图靠底部「vault」标签才不歧义；
    # 头像没有标签位，保险柜在小尺寸下被认成相机，故换成同色系的书。
    "soia-vault-curator": """
      <path d="M0,-108 C-62,-158 -148,-158 -200,-132 L-200,118
               C-148,92 -62,92 0,142 C62,92 148,92 200,118 L200,-132
               C148,-158 62,-158 0,-108 Z"/>
      <line x1="0" y1="-108" x2="0" y2="142"/>""",
    # 纸飞机：内容分发（同 assets/plugins/soia-media-content.svg）
    "soia-content-operator": """
      <polygon points="-215,-25 215,-165 95,175 -10,60"/>
      <line x1="-10" y1="60" x2="215" y2="-165"/>""",
    # 折角文档：办公资料（同 assets/plugins/soia-cwork-office.svg）
    "soia-office-aide": """
      <path d="M-160,-185 L60,-185 L160,-85 L160,185 L-160,185 Z"/>
      <polyline points="60,-185 60,-85 160,-85"/>
      <line x1="-88" y1="30" x2="88" y2="30"/>
      <line x1="-88" y1="110" x2="30" y2="110"/>""",
}

TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" width="{s}" height="{s}" viewBox="0 0 {s} {s}">
  <defs>
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
    <clipPath id="round"><circle cx="{cx}" cy="{cx}" r="{cx}"/></clipPath>
  </defs>

  <g clip-path="url(#round)">
    <rect width="{s}" height="{s}" fill="url(#bg)"/>
    <rect width="{s}" height="{s}" fill="url(#sheen)"/>
    <g transform="translate({cx},{gy})" fill="none" stroke-width="{stroke}"
       stroke-linecap="round" stroke-linejoin="round">
      <g stroke="{dark}" opacity="0.38" transform="translate(0,14)">{glyph}</g>
      <g stroke="url(#ink)">{glyph}</g>
    </g>
  </g>
</svg>
"""


def render_svg(name: str) -> str:
    dark, light, accent = AVATARS[name]
    return TEMPLATE.format(
        s=SIZE, cx=SIZE // 2, gy=GLYPH_CY, stroke=STROKE,
        dark=dark, light=light, accent=accent, glyph=GLYPHS[name],
    )


def build(experts_dir: pathlib.Path) -> int:
    try:
        import cairosvg
    except ImportError:
        cairosvg = None

    for name in sorted(AVATARS):
        target = experts_dir / name
        if not target.is_dir():
            print(f"  ⚠ 跳过 {name}：{target} 不存在")
            continue
        svg_path = target / "avatar.svg"
        svg_path.write_text(render_svg(name), encoding="utf-8")
        if cairosvg is None:
            print(f"  ✓ {name}/avatar.svg（无 cairosvg，未生成 PNG）")
            continue
        png_path = target / "avatar.png"
        cairosvg.svg2png(url=str(svg_path), write_to=str(png_path),
                         output_width=SIZE, output_height=SIZE)
        kb = png_path.stat().st_size / 1024
        flag = "✓" if kb <= 500 else "✗ 超过 500KB 上限"
        print(f"  {flag} {name}/avatar.png（{kb:.0f} KB）")
    if cairosvg is None:
        print("\n  提交前请在装有 cairosvg 的环境重跑本脚本生成 PNG：")
        print("    python3 -m pip install cairosvg")
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experts-dir", type=pathlib.Path,
                        default=repo_root / "experts",
                        help="专家定义目录，默认 <仓根>/experts")
    args = parser.parse_args(argv)
    return build(args.experts_dir)


if __name__ == "__main__":
    sys.exit(main())
