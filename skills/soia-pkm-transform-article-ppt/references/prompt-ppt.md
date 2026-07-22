# Editable PPT Prompt

用于 `local_editable` 和 `hybrid` 的正式母版。先形成 slide plan，再调用宿主演示文稿能力实现。

## 输入参数

```yaml
source: <article.md | outline | data-table | topic>
audience: <who>
job_to_be_done: <看完后理解、判断或行动什么>
main_verdict: <一句明确判断>
content_mode: learning | preserve | synthesize
style: course_module | technical_sharing | knowledge_blueprint | editorial | executive | workshop
slide_count: auto
aspect_ratio: "16:9"
visual_assets: 0..4
infographic: true | false
```

用户未指定时，必须把 `auto` 解析成具体值再进入生成。概念教程默认 `course_module`；技术工具默认 `technical_sharing`；系统/知识地图默认 `knowledge_blueprint`；观点文章默认 `editorial`。

## 内容合同

先输出以下结构并保存到 prompt 或 manifest：

```yaml
main_verdict: ""
sections: []
concepts: []
case_chain: []
source_claims: []
inferences: []
unknown_or_unverified: []
confusable_pairs: []
audience_questions: []
```

source 中看到的、从 source 推出的、尚未验证的内容必须分开。来源时间、作者、链接、性能数字和企业案例逐项核对；不要从当前日期或模型记忆补齐。

## Slide plan

每页写清六项：

| 字段 | 要求 |
|---|---|
| `title` | 一句判断或问题答案，不是空栏目名 |
| `page_job` | 这页让听众理解/比较/决定什么 |
| `source_anchor` | 对应章节、段落、术语或数据 |
| `content` | 页面要呈现的事实与关系 |
| `visual_form` | cover / map / flow / matrix / comparison / timeline / case / quiz / source |
| `asset_binding` | 使用哪张素材、放在哪里；不用则为空 |

中长文 14-18 页时推荐包含：封面、主判断、文章地图、3-6 个主体模块、流程/架构、关键机制、案例、易混概念、风险/边界、完整速查、自测/行动、来源。不是机械页序；根据 source 调整。

## 实现提示词

```text
你是中文课程设计师、信息架构师和演示文稿设计师。请严格基于内容合同和 slide plan，生成一份以可编辑对象为主的 PPTX。

交付目标：
- 受众：{audience}
- 用途：{job_to_be_done}
- 主判断：{main_verdict}
- 页数：{slide_count}
- 风格：{style}
- 画幅：{aspect_ratio}

内容要求：
1. 覆盖 source 主体章节、概念、案例链和关键边界；术语多时提供完整速查或索引。
2. 每页只讲一个主判断，但允许用流程、矩阵、表格承载多个相关事实。
3. 所有外部判断都标明是 source 事实、推断还是未验证原文观点。
4. 来源页只写核实过的 source 信息；不出现模型名、notebook id、artifact id、下载路径、占位符和内部运行记录。

设计要求：
1. 至少 4 种页面轮廓；连续页面不能只是换文字的同款卡片网格。
2. 封面有明确主题视觉；正文页显示结构、关系和证据，不靠装饰撑版面。
3. imagegen 素材只做图片；中文标题、术语、数字、流程箭头、来源和表格由 PPT 对象绘制。
4. 使用稳定网格、固定页边距和可预测字号；正文在投影和普通笔记本屏幕上可读。
5. 颜色承担语义：主线、支持、风险、行动有区别；避免整套只有单一蓝紫或装饰渐变。
6. 不使用嵌套卡片、漂浮页面区块、无意义大面积留白或装饰性小字。

可编辑性：
1. 标题、正文、图形、箭头、表格和页码保持可编辑。
2. 不把整页截图塞进正式母版。
3. 只有照片、插画、纹理和复杂视觉可以是位图。

生成后：
1. 实际保存 PPTX。
2. 渲染全部页面为 PNG，生成 montage。
3. 运行溢出/越界检查。
4. 人工逐页检查焦点、层级、中文断行、素材方向、来源和事实。
5. 修复后重新渲染，直到通过。
```

## 设计攻击清单

生成前后各问一次：

- 如果删掉标题，这页的结构仍能让人看懂吗？
- 最重要的信息是否在 2 秒内可见？
- 是否有连续 3 页同构？
- 图片是否表达了正确方向和关系，还是只是好看？
- 是否有一页承担了两个不相干的结论？
- 最长中文词、英文术语和数字是否会导致孤行或溢出？

