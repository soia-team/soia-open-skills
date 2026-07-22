# NotebookLM PPT Prompt

用于 NotebookLM `generate slide-deck`。NotebookLM 版是 source-grounded 视觉对照稿；不要假设其页面元素可编辑。

```text
请严格基于已上传的 source，生成一份简体中文 slide deck。

目标读者：{audience}
使用场景：{job_to_be_done}
主判断：{main_verdict}
页数：{slide_count，默认 14-18}
风格：{style}
内容模式：{learning | preserve}

内容要求：
1. 覆盖 source 的主体章节、核心概念、案例链和边界；概念较多时必须提供完整术语索引。
2. 每页标题表达一个明确判断，不使用「背景介绍」「核心观点」等空标题。
3. 页面任务至少覆盖 map、flow、comparison、case、quick reference、risk、quiz/action、source。
4. 所有判断都能回到 source；时间敏感预测、性能数字和企业案例只能以「原文观点/未验证」呈现。
5. source 没有数据时不伪造统计图表；使用层级、流程、关系图和对照表。

视觉要求：
1. 16:9，中文清晰，单页只有一个视觉焦点。
2. 不连续生成同款摘要卡；图像服务于页面判断。
3. 不使用来源外 logo、人物肖像、品牌资产或伪造界面。
4. 完整术语索引可以拆为多页，不能为了塞进一页缩成不可读小字。

来源页要求：
1. 只显示 source 中核实的标题、作者、链接、发布时间和必要局限声明。
2. 禁止显示 notebook_id、source_id、artifact_id、下载 URL、下载路径、账号、模型名、运行时间、占位符或其他内部元数据。
3. 不要生成 [PLACEHOLDER]、*_PLACEHOLDER、待补充路径等内容。
```

## 失败重做条件

- 出现任何运行元数据、占位符或账号信息。
- 主要概念覆盖不足 80%，或完整术语索引缺失。
- source 外事实被写成确定事实。
- 中文乱码、错误标签、方向错误或关键页面不可读。

发生上述问题时修改 prompt 重新生成。NotebookLM 页面通常是位图，不用遮盖层做表面修补。

