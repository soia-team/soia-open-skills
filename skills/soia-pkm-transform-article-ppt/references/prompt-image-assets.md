# Image Asset Prompt

用于 imagegen、gpt-image 或等价图片能力生成 PPT/信息图素材。图片必须绑定一个明确页面任务，不做无用途装饰。

## 资产计划

生成前列出：

```yaml
asset_id: image-01
used_on: slide-01 | slide-07 | infographic-main
semantic_job: <帮助理解哪个概念/关系>
subject: <主体>
direction: top-to-bottom | left-to-right | radial | none
aspect_ratio: "16:9"
text_policy: no_text
negative_constraints: []
```

典型 2-4 张素材：

- 封面主视觉：表达整篇文章的冲突、路径或对象。
- 核心机制图：表达一个流程、系统或概念关系。
- 案例/场景图：让抽象概念落入真实任务。
- 信息图主视觉：为中文排版保留干净区域。

## Prompt 模板

```text
为一份中文演示文稿生成一张无文字视觉素材。

页面用途：{used_on}
语义任务：{semantic_job}
主体：{subject}
关系与方向：{direction_and_relationships}
画幅：{aspect_ratio}
视觉风格：{style}
留白：{safe_text_area}

要求：
1. 画面只有一个主视觉焦点，关系方向必须正确。
2. 不生成中文、英文标签、数字、logo、水印或伪造界面。
3. 为后期 PPT/HTML 中文排版保留明确干净区域。
4. 不使用模糊背景、无意义光球、纯装饰渐变或库存图式人物摆拍。
5. 主体必须和 source 的真实对象一致，不擅自加入品牌、设备或统计。
```

## 验收

- 查看原图，而不是只看缩略图。
- 核对主体、方向、数量、手部/设备/连接关系和留白。
- 出现错误文字、数字、logo 或语义方向错误时，修改 prompt 重新生成。
- 文字与来源统一由 PPT/HTML 后期叠加；不要在位图上打补丁掩盖错误。

