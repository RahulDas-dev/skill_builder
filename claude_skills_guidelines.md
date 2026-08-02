Based on my analysis of the SKILL.md files in Anthropic's skill system, here are the **important guidelines the Claude Anthropic API expects from SKILL.md files**:

## **1. FRONTMATTER (YAML Metadata)**
```yaml
---
name: [skill-name]
description: [comprehensive description]
license: [license type and reference]
---
```

**Key Requirements:**
- `name` - Short, lowercase identifier (e.g., `docx`, `pdf`, `frontend-design`)
- `description` - **Comprehensive trigger guidance** that explains:
  - When Claude should use this skill
  - Specific keywords/phrases that trigger it
  - What tasks it handles
  - What it explicitly does NOT handle (use "Do NOT" statements)
- `license` - License type and reference to LICENSE.txt file

---

## **2. CONTENT STRUCTURE**

The main content section should include:

### **A. Clear Section Headers**
- Use markdown headers (`#`, `##`, `###`) to organize content
- Create logical sections for different aspects of the skill

### **B. Task-Focused Organization**
Structure content around **actual tasks** users perform:
- Use tables to map tasks to approaches/tools
- Example format:
  ```
  | Task | Approach |
  |------|----------|
  | Create | Use tool X |
  | Edit | Use tool Y |
  ```

### **C. Practical Code Examples**
- Include working code snippets for common operations
- Show actual syntax and expected usage
- Include commands for CLI tools

### **D. Known Issues & Gotchas**
- Document **critical pitfalls** that cause failures
- Highlight platform-specific quirks
- Use bold for emphasis on warnings
- Example: "Never use `\n` — use separate `Paragraph` elements"

### **E. Dependencies Documentation**
- List all required libraries, tools, and CLIs
- Specify versions if critical
- Note what's preinstalled vs. requires installation

---

## **3. DESCRIPTION BEST PRACTICES**

The description field should:

✅ **DO:**
- Be explicit about trigger conditions (keywords, file types, actions)
- Include both what TO use it for AND what NOT to use it for
- Use phrases like "whenever," "includes," "triggers," "also use when"
- Be specific about task categories it handles
- Mention file extensions, formats, or deliverables clearly

❌ **DON'T:**
- Be vague or abstract
- Assume Claude knows implicit use cases
- Omit negative cases (what it's NOT for)

**Example (from docx):**
> "Use this skill whenever the user wants to create, read, edit, or manipulate Word documents (.docx files)... Triggers include: any mention of 'Word doc', 'word document'... Do NOT use for PDFs, spreadsheets, Google Docs..."

---

## **4. CONTENT GUIDELINES**

### **A. Accuracy & Reliability**
- Information must be tested and current
- All code examples should be functional
- Document actual gotchas from real usage
- Specify workarounds for known limitations

### **B. Completeness**
- Cover common tasks comprehensively
- Include error handling guidance
- Explain WHY certain approaches are needed (not just HOW)

### **C. Organization**
- Quick Start / Overview section early
- Basic operations before advanced features
- Quick Reference tables for common tasks
- Links to supplementary files (REFERENCE.md, FORMS.md, etc.)

### **D. Cross-References**
- Reference supplementary documentation (REFERENCE.md, FORMS.md)
- Link to external official docs when relevant
- Indicate where to go for advanced features

---

## **5. SPECIAL SECTIONS COMMONLY USED**

- **Overview** - High-level summary
- **Quick Start** - Fast path to first success
- **Common Tasks** - Real-world use cases with solutions
- **Dependencies** - Tools/libraries required
- **Gotchas/Warnings** - Critical issues and workarounds
- **Next Steps** - Where to find advanced info
- **Quick Reference** - Tables mapping tasks to tools

---

## **6. FILE ORGANIZATION**

The skill folder structure typically includes:
```
skill-name/
├── SKILL.md           # Main skill documentation
├── REFERENCE.md       # Advanced/detailed reference
├── FORMS.md           # Specialized guides (optional)
├── LICENSE.txt        # License terms
└── scripts/           # Helper scripts/tools
```

---

## **7. CRITICAL DO's & DON'Ts**

| DO | DON'T |
|---|---|
| Be specific with triggers | Use vague trigger descriptions |
| Include working code | Theoretical-only examples |
| Document real gotchas | Skip known pitfalls |
| Explain the "why" | Just explain the "how" |
| Use tables for task mapping | Paragraph-only task lists |
| Reference supplementary docs | Repeat info in multiple files |
| Document dependencies | Assume libraries are known |
| Include negative cases (NOT for) | Only list positive uses |

---

## **8. SCOPE & PRECISION**

Each SKILL.md should:
- Focus on **one specific capability area** (docx, PDF, frontend design, etc.)
- Be **specific enough for Claude to auto-trigger** based on description
- Provide **actionable guidance** for every major task
- Avoid **overlap with other skills** (noted in description's "Do NOT" section)

---

These guidelines ensure skills are discoverable, usable, and maintainable by Claude when processing user requests.