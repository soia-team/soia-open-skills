# Infographic Prompt

用于「高密度长图 / 信息图 / 海报 / 一张图讲清楚」。中文密集文字、数字、表格和引用优先用 HTML/CSS 排版截图，不优先交给 imagegen。

## 参数

```yaml
target_output: long_image | infographic | image
params:
  provider: local_visual          # local_visual | open_design | notebooklm
  canvas: "1080x1920"             # 900x1600 | 1080x1920 | 1440x2560 | auto
  density: high                   # dense | high
  audience: auto
  style: research_poster          # research_poster | magazine | xhs | course | technical
  content_mode: visual_dense
```

## Prompt 模板

```text
你是资深中文信息设计师和研究编辑。请把下面文章转换成一张高密度中文信息图。

目标读者：{params.audience}
画幅：{params.canvas}
风格：{params.style}
内容模式：visual_dense，不是摘要卡。

内容要求：
1. 严格基于原文，不引入原文外事实数据。
2. 先抽 source coverage：章节、概念清单、案例链、关键判断。
3. 提取 1 个主判断、12-18 个信息块、1 条主流程或关系链、1 个对比表或示意图、支持点、风险点、继续追问。
4. 每个信息块必须有「短标题 + 具体解释」，避免空泛名词。
5. 如果使用图表但原文没有数字，必须标注「教学示意」。

版式要求：
1. 顶部：大标题 + 来源 + verdict 横幅。
2. 中上部：6-9 个编号卡片，形成主信息矩阵。
3. 中部：流程图 / 层级图 / 对比表 / 示意图至少 2 种。
4. 底部：支持使用的点、必须警惕的点、继续追问。
5. 信息密度接近研究海报，而不是社交媒体标题图。

视觉要求：
1. 字体层级清楚：标题、分区标题、卡片标题、正文、注释至少 4 级。
2. 使用深浅对比、边框、语义色区分普通信息/支持/风险。
3. 控制留白，避免大片空区；但文字不能拥挤到不可读。
4. 禁止图表或文字覆盖其他模块。

输出：
- 先给信息架构 YAML。
- 再给完整 HTML/CSS。
- 渲染成 PNG 后检查：尺寸、可读性、重叠、截断。
```

## QA Gate

- 至少 12 个信息块；概念教程要覆盖主要概念模块，不能只挑 3-5 个词。
- 至少 2 种结构化表达：流程、层级、对比表、矩阵、示意图。
- 中文文字可读，没有乱码、遮挡、截断。
- 不用 imagegen 直接生成密集中文成品。
