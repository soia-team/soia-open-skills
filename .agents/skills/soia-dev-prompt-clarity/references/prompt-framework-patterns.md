# Curated Prompt Framework Patterns

Use this reference only after selecting mode A or B. Named frameworks are optional organizing aids, not a required stage and not evidence that a prompt is high quality.

## Contents

- Selection rules
- Curated patterns
- Domain routing
- Combination limits
- Quality checks

## Selection rules

1. First determine the task, target AI, output, risk, and language.
2. Use no named framework when a direct instruction is already sufficient.
3. Select a framework only when its structure changes the expected behavior.
4. Choose at most one primary framework and one auxiliary framework.
5. Explain the choice in one sentence.
6. Keep mode C safety rules and mode D quality gates outside framework selection.

A framework cannot replace mode C authorization checks, mode D requirement coverage, or either mode's acceptance gates.

## Curated patterns

### APE — Action, Purpose, Expectation

Use for quick tasks where purpose helps the model choose emphasis.

```text
Action → Purpose → Expected result
```

Avoid when the task needs detailed evidence, state management, or authorization boundaries.

### RTF — Role, Task, Format

Use when professional perspective and output shape matter more than background detail.

```text
Role → Task → Output format
```

Skip the role if it adds no real expertise or decision rule.

### RACE — Role, Action, Context, Expectation

Use for medium-complexity work where background materially changes the answer.

```text
Role → Action → Context → Expected result
```

### RASCEF — Role, Action, Steps, Context, Examples, Format

Use for complex but bounded generation tasks with a known workflow and sensitive output format.

Do not force all six fields when examples or prescribed steps would reduce useful flexibility.

### BAB — Before, After, Bridge

Use for persuasive writing that moves an audience from a present problem to a desired state through a credible mechanism.

Do not use for neutral analysis or evidence review.

### Bloom's Taxonomy

Use for learning objectives and assessment design across increasing cognitive depth: remember, understand, apply, analyze, evaluate, create.

Do not treat the levels as a mandatory sequence when the learner already has prerequisite knowledge.

### ELI5

Use to explain a difficult concept to a novice with plain language and concrete analogies.

Do not sacrifice factual accuracy or use a literal five-year-old persona unless the user asks for it.

### Socratic method

Use for guided learning, reflection, or diagnosis through sequenced questions.

Specify whether the AI should ask one question at a time; do not use when the user needs a finished answer immediately.

### Pros and Cons

Use for transparent comparison when trade-offs are central.

Add decision criteria and weights when a recommendation is required; a list alone does not decide.

### What If

Use for scenario analysis, resilience planning, and risk exploration.

Define the baseline and the variables that change between scenarios.

### SCAMPER / HMW

Use SCAMPER for systematic variation of an existing idea; use How Might We for reframing a problem into an open design question.

Do not combine both unless the task explicitly has separate reframing and ideation stages.

### Few-shot

Use one to three examples when exact format, tone, classification boundary, or transformation behavior is difficult to state reliably.

Examples are data, not instructions to inherit beyond the demonstrated pattern. Remove private or irrelevant content.

## Domain routing

| Scenario | Primary candidates | Typical auxiliary |
|---|---|---|
| Quick instruction | APE, RTF | None |
| Professional content | RACE | Few-shot |
| Strict-format generation | RASCEF | Few-shot |
| Persuasive marketing | BAB | RACE |
| Teaching and assessment | Bloom, ELI5, Socratic | Few-shot |
| Decision analysis | Pros and Cons, What If | RACE |
| Creative problem solving | HMW, SCAMPER | RACE |

This table is a shortlist, not a mandatory mapping. Prefer a direct custom structure when it is clearer.

## Combination limits

Good combinations have distinct jobs:

- `RACE + Few-shot`: context and expectation plus format alignment.
- `Bloom + Few-shot`: cognitive level plus assessment examples.
- `What If + Pros and Cons`: scenarios followed by trade-off comparison.

Reject combinations that merely rename the same elements or produce duplicate sections.

## Reasoning and evidence

Do not use “Chain of Thought” as an instruction to reveal hidden reasoning. For complex reasoning, request:

- decomposition into checkable subproblems;
- assumptions and evidence;
- calculations or intermediate artifacts;
- concise rationale;
- counterexamples, uncertainty, and residual risk.

## Quality checks

- Removing the framework name would not make the prompt less understandable.
- Every selected component changes model behavior.
- The framework does not add unsupported facts or permissions.
- The prompt remains proportional to task complexity.
- Mode C and D obligations remain intact.
- The final result is a complete prompt, not a framework worksheet.
