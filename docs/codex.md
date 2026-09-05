# Codex and GPT-6 Astra

This repository uses Codex with OpenAI models for development. The shared default is
`gpt-6-astra`, with `high` reasoning effort as a project choice for code and data-pipeline work.
The scraper itself uses HTTP requests and local Python processing; it does not call an LLM API.

## Configuration

[.codex/config.toml](../.codex/config.toml) sets the model and reasoning effort.
Codex reads project configuration in trusted repositories. CLI overrides take precedence; an
existing app task may already have its own model selection. Check the active task's model picker
and select **GPT-6 Astra** when needed. Editing a Markdown instruction does not switch a model.

From this repository, an explicit CLI selection is:

```bash
codex --model gpt-6-astra -c model_provider=openai -c model_reasoning_effort=high
```

For a small task, reasoning effort can be lowered without editing the shared configuration:

```bash
codex --model gpt-6-astra -c model_provider=openai -c model_reasoning_effort=low
```

The `openai` provider is Codex's built-in default. Provider selection is a host/user setting:
Codex ignores `model_provider` in project configuration. The explicit commands above select it
for that invocation. If a user configuration selects another provider, change the existing
top-level `model_provider` setting to `"openai"` in the user configuration (normally
`~/.codex/config.toml`) before using the app's project defaults. This PR does not edit that file.
See the [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
for the distinction between project and user settings.

Use an installed Codex version and account that expose Astra. If the model is unavailable, report
that limitation and select another available OpenAI model only in line with the user's choice.
Do not silently change the project's pinned model. Authentication, project trust, permissions,
and private settings belong to the host/user configuration; do not commit credentials.

## Instructions and skills

[AGENTS.md](../AGENTS.md) is the repository instruction entry point. Operational detail is in
[the pipeline guide](pipeline.md), [README](../README.md), and the linked domain documentation.
The previous `CLAUDE.md` has been removed; there is no parallel instruction file to maintain.

The following skills are checked in under `.agents/skills/`:

| Skill | Use when |
| --- | --- |
| [cave-scraping](../.agents/skills/cave-scraping/SKILL.md) | Changing CBDG requests or diagnosing bounded fetch failures |
| [cave-data-pipeline](../.agents/skills/cave-data-pipeline/SKILL.md) | Changing parsing/cleaning or validating a requested data refresh |
| [cave-archive-restore](../.agents/skills/cave-archive-restore/SKILL.md) | Restoring archived cave descriptions and attachments |

Codex can select a skill from its description, or it can be invoked explicitly, for example:

```text
$cave-data-pipeline sprawdź parser na tymczasowych danych, bez zmiany zbioru jaskiń
```

Start a new Codex task after installing these repository instructions and skills if the current
task has not discovered them. Skills carry the workflow, while model selection remains in Codex
configuration. There are no agent-role model aliases or mandatory external plugins to install.

## Maintaining this setup

Keep `AGENTS.md` short and move conditional detail into the relevant guide or skill. Describe
the intended outcome, data invariants, and verification rather than scripting the model's every
step. New skills need a `SKILL.md` with YAML `name` and `description`, a clear task boundary, and
working relative links. Add helpers only for a concrete repeated operation.

Review changes against actual source behavior and realistic tasks. Documentation or instruction
updates do not require live scraping, full dataset regeneration, or reduced sandbox protection.

The migration was checked on 2026-09-05 against Codex CLI 0.146.0 and these official references:

- [GPT-6 Astra model identifier and reasoning support](https://developers.openai.com/api/docs/models/gpt-6-astra)
- [Codex configuration and precedence](https://learn.chatgpt.com/docs/config-file/config-basic)
- [AGENTS.md discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Repository skills and progressive loading](https://learn.chatgpt.com/docs/build-skills)
