# Codex Image Prompt

用于 Codex imagegen / gpt-image-2 / image provider 生成「封面图、头图、文章配图、背景图、插画、视觉隐喻、图标素材」。它生成视觉素材，不承担中文密集信息排版。

## 参数

```yaml
target_output: image
params:
  provider: codex_image           # codex_image | imagegen | gpt-image-2 | auto
  image_subtype: cover_image      # cover_image | illustration | background | icon_set
  aspect_ratio: "16:9"            # 16:9 | 4:3 | 1:1 | 3:4 | 9:16
  text_policy: avoid_dense_text   # no_text | short_title_only | avoid_dense_text
  style: editorial                # editorial | cinematic | isometric | 3d | collage | minimal
  audience: auto
```

## Prompt 模板

```text
你是资深视觉创意总监。请为下面文章生成一张 {params.image_subtype}。

目标读者：{params.audience}
画幅：{params.aspect_ratio}
风格：{params.style}
视觉目标：让读者在 2 秒内感到 {emotion_or_conflict}
文章主判断：{main_verdict}

内容要求：
1. 只表达文章的核心主题、情绪和视觉隐喻，不承载密集事实。
2. 不生成长段中文文字、表格、小字、真实统计数字。
3. 如果必须有文字，只允许 1 个短中文标题或留出标题区，最终文字由后期排版叠加。
4. 不伪造品牌 logo、人物肖像、真实机构标识，除非用户提供素材和授权。

视觉要求：
1. 明确主体、前景、中景、背景和留白区域。
2. 为后期叠加中文标题预留干净区域。
3. 色彩不能单一糊满；要有背景、主体、强调、留白。
4. 避免截图感、模糊小字、乱码文字。
```

## QA Gate

- 图像不包含错误中文、乱码数字或伪造标识。
- 如需标题、作者、来源，用 HTML/PPT/图片编辑后期叠加。
- 回执区分「Codex image 生成视觉素材」与「最终排版图」。
