# NotebookLM Podcast Prompt

用于 NotebookLM `generate audio`，也可生成播客脚本作为本地降级。

```text
请严格基于已上传 source 生成中文 audio overview / podcast。

目标听众：{params.audience}
语言：中文
时长：{params.duration 或 6-10 分钟}
风格：清晰、克制、有结构，不要夸张营销腔。

内容结构：
1. 开场 20 秒说明文章解决什么问题。
2. 按 source 的主要结构讲解，不只列观点。
3. 用原文例子解释关键概念。
4. 加入 2-3 个听众可能误解的点，并纠正。
5. 结尾给出行动清单、风险边界和继续追问。

约束：
- 不引入 source 外事实。
- 不把作者观点说成已验证事实。
```

## QA Gate

- 记录 notebook_id、source_id、artifact_id、下载 MP3 路径。
- 若未成功下载音频，只能交播客脚本，不能声称生成了 NotebookLM 音频。
