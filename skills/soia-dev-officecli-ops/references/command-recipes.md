# OfficeCLI Command Recipes

语法以本机 `officecli help ... --json` 为准。以下只记录稳定的操作模式，不复制上游完整 schema。

## 只读盘点

```bash
officecli view <file> outline
officecli view <file> stats --json
officecli view <file> issues --json
officecli get <file> / --depth 2 --json
officecli query <file> '<selector>' --json
officecli validate <file> --json
```

PPT 可先列出一页的 shape，再保存稳定路径：

```bash
officecli get <deck.pptx> '/slide[1]' --depth 1 --json
officecli get <deck.pptx> '/slide[1]/shape[@id=42]' --json
```

Word 优先使用 `@paraId`，PPT 优先 `@id`/`@name`。只有没有稳定标识时才使用位置索引。

## 安全副本修改

```bash
python3 scripts/officecli_safe.py \
  --input <source.docx> \
  --output <result.docx> \
  --dry-run \
  -- set '/body/p[@paraId=1A2B3C4D]' --find draft --replace final
```

包装器会把源文件复制到输出，再把输出路径注入 OfficeCLI 命令。它拒绝输入与输出相同、输出已存在但没有 `--overwrite`、未知 verb 和非 Office 扩展名。

## 原子 batch

三项以上修改优先使用 batch。batch JSON 的字段和支持命令必须先查：

```bash
officecli help batch --json
```

然后通过副本包装器执行：

```bash
python3 scripts/officecli_safe.py \
  --input <source.pptx> \
  --output <result.pptx> \
  -- batch --input <operations.json>
```

OfficeCLI 1.0.137 起 batch 默认原子执行。任何步骤失败都按失败处理，读取 JSON envelope 的业务 verdict，不只看 stdout 文案。

## HTML、截图和 watch

```bash
officecli view <file> html -o <preview.html>
officecli view <deck.pptx> screenshot -o <preview.png> --grid 4
officecli watch <file>
officecli get <file> selected --json
officecli unwatch <file>
```

`watch` 只用于本机交互预览。修改仍应把选择结果转换成稳定路径，再执行明确的 `set` 或 batch。

## Raw XML

只有 DOM help 明确不支持目标能力时才进入 raw 层：

```bash
officecli raw <file> <part> --xpath '<xpath>'
officecli raw-set <file> <part> --xpath '<xpath>' --action <action> --xml '<xml>'
```

执行 `raw-set` 前必须保存副本、展示 part/xpath/action、获得确认，并在修改后重新 `validate`、读回 XML 和做视觉检查。
