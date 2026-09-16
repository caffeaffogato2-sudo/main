# Claude Code Instructions

Before making changes, read:

- `README.md`
- `docs/AI_WORKFLOW.md`

`docs/AI_WORKFLOW.md` is the canonical workflow and quality rule for this repository.

Do not create a separate Claude-specific workflow.

Use Claude Code when local execution, environment-dependent verification, Windows-specific work, large file processing, or complex E2E execution is required.

For every task:

- inspect the current baseline first
- confirm the requested scope
- prefer a `work/<task>` branch for changes
- do not modify files outside the requested scope
- run applicable validation
- report changed files, validation actually executed, and unresolved items
