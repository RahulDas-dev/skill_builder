# Copilot Skill Guidelines

These guidelines describe how to author skill documentation for a Copilot-like skill system. They are designed to make skills easy to trigger, easy to use, and easy to maintain.

## 1. Skill Metadata

Each skill should begin with metadata that clearly identifies its scope and safe usage.

- `name`: short, lowercase, hyphen-separated identifier
- `description`: a precise trigger and scope statement
- `license`: license guidance or usage restrictions

Example:

```yaml
---
name: fastapi-patterns
description: Use this skill when authoring or reviewing FastAPI service and route structure, startup patterns, dependency injection, and async architecture. Do NOT use for generic Flask or Django projects.
license: Personal use only — not for redistribution.
---
```

## 2. Trigger Guidance

The description should tell Copilot when to use the skill.

- Mention the main task categories it handles.
- Include specific keywords, file types, or frameworks.
- Mention what it does not cover.
- Prefer concrete phrases like "Use this skill when..." and "Do NOT use for...".

## 3. Clear Content Structure

Organize the skill with headings and sections.

Recommended sections:

- Overview / Quick Start
- When to Use This Skill
- Dependencies
- Common Tasks / Patterns
- Code Examples
- Gotchas / Warnings
- References / Next Steps

## 4. Practical Examples

Include working examples for common tasks.

- Use real syntax, not pseudocode.
- Keep examples focused on the skill's domain.
- Prefer short, copy-paste-ready snippets.
- Show common failure modes and correct handling.

## 5. Dependencies and Environment

Document required libraries, tools, and environment assumptions.

- List package names and minimum versions when relevant.
- Note which dependencies are optional.
- Call out runtime constraints such as Python version.

## 6. Scope and Negative Cases

A good skill is precise.

- Focus on one capability area.
- Avoid broad or overlapping skill scopes.
- Use negative cases to prevent incorrect triggering.
- If the skill is narrow, explain what belongs to other skills.

## 7. Gotchas and Warnings

Document known pitfalls and edge cases.

- Include warnings for fragile patterns.
- Explain common mistakes and safe alternatives.
- Use bold or callout-style text for critical warnings.

## 8. Cross-References

Link to supporting documentation when available.

- Reference related skills or files in the same repository.
- Link to external documentation only when it adds value.
- Avoid duplicate content across multiple files.

## 9. Validation and Review

Use tooling to keep skill documentation reliable.

- Validate frontmatter and section structure.
- Check code fences for valid syntax.
- Confirm internal links reference existing files.

## 10. Maintenance

Keep skill docs up to date.

- Update examples when APIs change.
- Revise dependency versions periodically.
- Add new gotchas when real issues appear.
- Re-check trigger phrasing as the skill evolves.

## 11. File Length

Keep each skill file under 510 lines whenever possible. This makes skills easier to consume and helps reviewers focus on the most important guidance.

## Why These Guidelines Matter

Well-written skills help Copilot choose the right guidance quickly, avoid incorrect matches, and provide users with practical, reliable answers.
