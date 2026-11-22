# Project agent skills (drafts)

These tool-neutral workflow instructions are derived from the root factory manifesto. They are not installed into any specific agent runtime and do not imply the corresponding CLI workflow is implemented.

| Skill | Use when | Main output |
|---|---|---|
| [create-task](create-task/SKILL.md) | User asks to create a task from chat/manual input | One canonical `task.json`; clarify or mark unresolveds rather than invent |
| [go-to-task](go-to-task/SKILL.md) | User asks to resume/execute a known task key | Selected task/stage, checked workspace state, context links and plan |
| [задокументируй](document-session/SKILL.md) | User explicitly asks to record confirmed session changes | Task/stage delta or focused architecture update, then structural validation |

The agent uses only the skill relevant to current intent. `doc/tools` performs deterministic architecture-document operations; it does not perform semantic selection, task creation/execution, or judgment-heavy decisions.
