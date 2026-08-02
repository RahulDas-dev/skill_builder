# Skill Builder

`skill-builder` is a lightweight framework for authoring, validating, and organizing domain-specific skills as markdown-driven documentation packages.

It helps you build various skills by providing:

- A clear package structure for skill content, references, and templates.
- Validation tooling to catch missing sections, formatting issues, broken links, and invalid example code.
- Separate skill directories for different domains, such as FastAPI architecture, AG-UI streaming events, and Python development best practices.

## What is a skill?

A skill is a self-contained markdown package that describes when and how to apply a specific development practice or architecture pattern. Each skill includes:

- A `SKILL.md` entry point with metadata and usage guidance.
- Supporting reference documents in `references/`.
- Optional code templates in `templates/`.

## How it helps

`skill-builder` makes it easier to:

- Author consistent, reusable guidance across multiple domains.
- Ensure each skill includes key sections like Overview, Dependencies, and Gotchas.
- Validate example code blocks for Python, JSON, TOML, and JavaScript.
- Catch broken cross-references between skill documentation and supporting files.

## Included skills

- `a2ui-development` — A2UI protocol: declarative agent-driven UI (surfaces, components, data binding) and native implementation guidance.
- `agui-development` — AG-UI event protocol and streaming UI integration guidance.
- `fastapi-patterns` — FastAPI project structure, routes, services, configs, and startup patterns.
- `python-dev` — Python idioms, type hints, logging, and package organization best practices.

## Usage

Run the verification script to check all skills:

```bash
uv run python scripts/verify_skills.py
```

See `COPILOT_SKILL_GUIDELINES.md` and `CLAUDE_SKILL_GUIDELINES.md` for skill authoring best practices.

This repository is designed to help authors keep skill documentation accurate, structured, and easy to extend.
