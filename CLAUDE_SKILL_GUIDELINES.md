# Claude Skill Guidelines

Based on analysis of the SKILL.md files used by Claude-compatible skill systems, these are recommended authoring practices for skills intended to trigger in Claude or Claude-like assistants.

## 1. FRONTMATTER (YAML Metadata)

```yaml
---
name: [skill-name]
description: [comprehensive description]
license: [license type and reference]
---
```

**Key Requirements:**
- `name` - short, lowercase identifier (e.g. `docx`, `frontend-design`)
- `description` - comprehensive trigger guidance
- `license` - license type and reference when applicable

## 2. CONTENT STRUCTURE

The main content section should include:

### A. Clear Section Headers
- Use markdown headers (`#`, `##`, `###`) to organize content.

### B. Task-Focused Organization
- Structure content around actual tasks and user goals.
- Use tables to map tasks to approaches.

### C. Practical Code Examples
- Include working code snippets and CLI commands.

### D. Known Issues & Gotchas
- Document critical pitfalls and warnings.

### E. Dependencies Documentation
- List required libraries, tools, and versions.

## 3. DESCRIPTION BEST PRACTICES

The description field should:
- explain when the skill should be used
- include keywords or triggers
- describe what it does NOT handle

## 4. CONTENT GUIDELINES

### Accuracy & Reliability
- Keep information tested and current.
- Validate code examples.

### Completeness
- Cover common tasks clearly.
- Include error handling guidance.

### Organization
- Put Overview / Quick Start early.
- Add Quick Reference tables when helpful.

### Cross-References
- Link to supporting docs.
- Avoid duplicate content across files.

## 5. SPECIAL SECTIONS

Commonly used sections include:
- Overview
- Quick Start
- Common Tasks
- Dependencies
- Gotchas / Warnings
- Next Steps
- Quick Reference

## 6. FILE ORGANIZATION

A typical skill folder may include:
```
skill-name/
├── SKILL.md
├── REFERENCE.md
├── FORMS.md
├── LICENSE.txt
└── scripts/
```

## 7. DOs & DON'Ts

DO:
- Be specific with triggers
- Include working examples
- Document real gotchas
- Explain why, not just how

DON'T:
- Be vague
- Leave out negative cases
- Repeat the same content across skills

## 8. SCOPE & PRECISION

Focus each skill on one capability area and make its scope precise. Document both the positive use cases and the cases where it should not apply.

## 9. VALIDATION

Use tooling to validate frontmatter, structure, code fences, and internal links.

## 10. MAINTENANCE

Keep skills up to date as APIs and frameworks evolve.

## 11. FILE LENGTH

Keep each skill file under 510 lines whenever possible. Shorter files are easier to read, review, and maintain, and they reduce the risk of outdated or duplicated content.
