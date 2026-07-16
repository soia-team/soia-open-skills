# NotebookLM Podcast Prompt

用于 NotebookLM `generate audio` / `generate video`，也可生成播客脚本、视频脚本作为本地降级。

```text
请严格基于已上传 source 生成中文 audio overview / podcast。

目标听众：{params.audience}
语言：中文
时长：{params.duration 或 8-12 分钟；只有用户明确要短版时才低于 5 分钟}
风格：清晰、克制、有结构，不要夸张营销腔。

内容结构：
1. 开场 20 秒说明文章解决什么问题。
2. 先按 source 的主要结构讲解，不只列观点。
3. 覆盖 source 中的主要概念清单；中长文不能只讲 3-5 个词。
4. 用原文例子解释关键概念。
5. 加入 2-3 个听众可能误解的点，并纠正。
6. 结尾给出行动清单、风险边界和继续追问。

约束：
- 不引入 source 外事实。
- 不把作者观点说成已验证事实。
- 不生成 1 分钟浅聊，除非用户明确要求 short。
```

视频 / cinematic：

- `video` 用 explainer / whiteboard 风格，目标 6-8 分钟，必须有概念链路和案例链路。
- `cinematic-video` 用 `generate video --format cinematic`，目标 60-90 秒视觉隐喻，不承载密集中文解释。
- 两者都必须记录生成/下载命令和失败原因；视频下载失败时只能交脚本/shotlist，不能声称视频已生成。

## QA Gate

- 记录 notebook_id、source_id、artifact_id、下载 MP3 路径。
- 若未成功下载音频，只能交播客脚本，不能声称生成了 NotebookLM 音频。
- Audio 默认使用 `deep-dive + long`；用户明确要短版才用 `brief + short`。
