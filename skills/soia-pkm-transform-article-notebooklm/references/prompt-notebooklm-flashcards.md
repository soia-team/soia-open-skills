# NotebookLM Flashcards Prompt

用于 NotebookLM `generate flashcards`。

```text
请严格基于已上传 source 生成中文 flashcards。

目标读者：{params.audience}
语言：中文
数量：{params.card_count 或 20-40}

卡片规则：
1. 一张卡只考一个概念、术语、判断或流程节点。
2. 正面是问题；背面是答案 + 必要解释。
3. 覆盖术语定义、易混概念、关键流程、风险边界和应用场景。
4. 不引入 source 外事实。
5. 避免背面过长；复杂内容拆成多张卡。
```

## QA Gate

- 每张卡只有一个考点。
- 正反面都存在。
- 下载 Markdown/JSON 后检查空卡和重复卡。
