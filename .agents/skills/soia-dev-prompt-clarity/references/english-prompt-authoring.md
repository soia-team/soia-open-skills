# English Prompt Authoring

Use this reference whenever `prompt_language = English`, including English-only and bilingual delivery. Compose the prompt directly in natural English; do not generate a Chinese prompt first and translate it sentence by sentence.

## Contents

- Language resolution
- Native-English construction
- Obligation and scope preservation
- Bilingual delivery
- Mode-specific guidance
- Quality checklist

## Language resolution

Track three independent values:

| Field | Meaning | Default |
|---|---|---|
| `input_language` | Language of the request or source prompt | Detect from the supplied text |
| `prompt_language` | Language of the reusable prompt | Explicit request; otherwise preserve source prompt or use the user's language |
| `explanation_language` | Language of diagnosis and change notes | Explicit request; otherwise use the conversation language |

Examples:

- Chinese request + “write the prompt in English” → English prompt, Chinese explanation.
- English request with no language instruction → English prompt and explanation.
- Existing English prompt + “optimize it” → keep English.
- “Give me Chinese and English versions” → two complete versions; use the requested primary language first.

Do not ask a language question when these defaults resolve the request without changing its meaning.

## Native-English construction

1. Start requirements with precise verbs: `Analyze`, `Compare`, `Draft`, `Verify`, `Produce`, `Do not modify`.
2. Prefer short declarative requirements over translated Chinese topic phrases.
3. State purpose only when it changes the target AI's decisions.
4. Put related constraints together; do not repeat the same prohibition in several sections.
5. Keep paths, commands, field names, model identifiers, code, and product names unchanged.
6. Preserve a Chinese term when no stable English equivalent exists; add a concise English gloss on first use.
7. Use headings only when they make a complex prompt easier to execute.
8. Use numbered requirements when ordering, traceability, or later acceptance checks matter.

Avoid literal constructions such as:

- `Please according to the following requirements...`
- `Help me to do an analysis about...`
- `Need you to...`
- `Under the premise of not changing...`

Prefer:

- `Follow these requirements:`
- `Analyze...`
- `Do not change...`
- `Preserve...`

## Obligation and scope preservation

Language conversion is a semantic operation, not permission to edit the contract.

| Source meaning | English expression | Do not weaken to |
|---|---|---|
| 必须 | `must`, `is required to` | `should`, `consider` |
| 应该 | `should` | `may` |
| 可以 | `may`, `can` | `must` |
| 禁止/不得 | `must not`, `do not` | `avoid if possible` |
| 全部/不得遗漏 | `all`, `without omissions` | `representative`, `sample` |
| 自动执行 | `automatically perform` | `recommend how to perform` |
| 仅建议 | `recommend only; do not execute` | `perform` |

When the source is ambiguous about obligation strength, mark it for clarification instead of choosing a stronger or weaker modal.

## Bilingual delivery

Deliver bilingual prompts as two standalone artifacts:

```markdown
## English version
<complete English prompt>

## 中文版
<完整中文提示词>
```

Rules:

- Keep requirement order and identifiers aligned across both versions.
- Preserve placeholders, paths, schema fields, and code exactly.
- Translate explanatory prose, not machine-readable keys, unless the user requests localized keys.
- If one version contains a clarification, boundary, or acceptance condition, the other version must contain its semantic equivalent.
- Do not alternate languages sentence by sentence.

## Mode-specific guidance

### Mode A

Write the smallest complete prompt that changes the target AI's behavior. A simple English prompt often needs only action, context, and output.

Example:

```text
Summarize the attached research note for product managers.

Focus on the three findings that could change roadmap priorities. Separate observed facts from your inferences, and flag claims that require source verification.

Return:
1. A five-bullet executive summary.
2. A table with finding, evidence, product implication, and confidence.
```

### Mode B

Preserve effective wording. Diagnose before rewriting, and do not replace concise English with ceremonial headings. Explain changed modality, scope, or ordering explicitly.

### Mode C

Use factual ownership and authorization language:

```text
Export the published articles from an account I own and administer, using the platform's official export interface, for a private local backup. Do not access other accounts or bypass access controls.
```

Never invent ownership or authorization to make a request sound safer.

### Mode D

Use stable requirement identifiers and explicit acceptance evidence. Preserve `must`, `must not`, complete scope, automatic behavior, and stop conditions. If a fact is unknown, write `<to-be-discovered>` or `unknown` instead of inventing a value.

## Reasoning requests

Do not ask the target AI to expose private or hidden chain-of-thought. Ask for outputs that can be checked:

- task decomposition;
- assumptions;
- evidence and citations;
- calculations or intermediate artifacts;
- concise rationale;
- counterexamples and residual risks.

## English quality checklist

Before delivery, verify:

- The prompt reads as originally written in English, not translated line by line.
- Every requirement has an explicit action or observable outcome.
- Modal strength and scope match the source.
- No new facts, permissions, or platform capabilities were invented.
- Technical tokens and placeholders remain unchanged.
- The prompt and explanation use the requested languages.
- A bilingual pair is semantically aligned.
- The prompt does not request hidden chain-of-thought.
