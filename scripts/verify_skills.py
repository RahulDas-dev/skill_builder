"""Static verification for skills/ directories.

Catches transcription damage (typo'd filenames, broken cross-links, mangled
markdown, invalid embedded code) and checks alignment with
claude_skills_guidelines.md (frontmatter shape, Dependencies/Overview/Gotchas
sections, etc).

Parsing: `python-frontmatter` handles YAML frontmatter, `markdown-it-py`
(CommonMark) handles structural extraction (headings, fenced code blocks).
Table-cell and inline-code-span integrity checks are deliberately *stricter*
than the CommonMark/GFM spec (which silently tolerates a stray `|` in a table
cell or an odd backtick run) because that leniency is exactly what let past
authoring bugs slip through — so those two checks still scan raw lines.

Usage:
    uv run python scripts/verify_skills.py [skills_dir]
"""

from __future__ import annotations

import ast
import json
import re
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import frontmatter
from markdown_it import MarkdownIt

MD = MarkdownIt("commonmark")

PLACEHOLDER_TOKEN_RE = re.compile(r"<[a-zA-Z_][\w]*>")
BLOCK_HEADER_RE = re.compile(
    r"^(\s*)(def |class |if |elif |else|for |while |with |try|except|finally).*:\s*(#.*)?$"
)
JSON_ELLIPSIS_OBJECT_RE = re.compile(r"\{\s*\.\.\.\s*\}")
JSON_ELLIPSIS_VALUE_RE = re.compile(r"(?<=:\s)\.\.\.(?=\s*[,}\]])")
BRACKET_PAIRS = {"{": "}", "(": ")", "[": "]"}
LATEX_ARTIFACT_RE = re.compile(r"\$\\[a-zA-Z]+\$")
MANGLED_DUNDER_RE = re.compile(
    r"\*\*(init|slots|all|name|main|repr|eq|call|enter|exit|new|len|iter|next|str|post_init)\*\*"
)
REF_PATH_RE = re.compile(r"\b(?:references|templates)/[\w.\-/]+")
GOTCHA_KEYWORDS_RE = re.compile(
    r"(gotchas?|anti-patterns?|antipatterns?|known issues?|warnings?|pitfalls?|considerations?|rules?)\b",
    re.IGNORECASE,
)
OVERVIEW_KEYWORDS_RE = re.compile(r"^(overview|quick start|when to\b)", re.IGNORECASE)


def stub_missing_bodies(body: str) -> str:
    """Insert a synthetic '...' body after header lines with no indented body.

    Lets signature-only illustrative snippets (common in docs) parse as valid
    Python without requiring every example to be a runnable function.
    """
    lines = body.split("\n")
    out: list[str] = []
    for i, line in enumerate(lines):
        out.append(line)
        m = BLOCK_HEADER_RE.match(line)
        if not m:
            continue
        indent = m.group(1)
        next_line = lines[i + 1] if i + 1 < len(lines) else ""
        next_indent = len(next_line) - len(next_line.lstrip())
        has_body = next_line.strip() != "" and next_indent > len(indent)
        if not has_body:
            out.append(indent + "    ...")
    return "\n".join(out)


def parse_possibly_multi_json(text: str) -> None:
    """Raise json.JSONDecodeError unless text is one or more whitespace-separated JSON values."""
    decoder = json.JSONDecoder()
    idx, n = 0, len(text)
    found_any = False
    while idx < n:
        while idx < n and text[idx] in " \t\r\n":
            idx += 1
        if idx >= n:
            break
        _, idx = decoder.raw_decode(text, idx)
        found_any = True
    if not found_any:
        json.loads(text)  # raise the natural "empty" error consistently


@dataclass
class Finding:
    file: Path
    message: str
    line: int | None = None

    def __str__(self) -> str:
        loc = f":{self.line}" if self.line else ""
        return f"{self.file}{loc}  {self.message}"


@dataclass
class SkillReport:
    name: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.findings


@dataclass
class Heading:
    level: int
    text: str
    line: int  # 1-indexed, absolute within the file


@dataclass
class Fence:
    lang: str
    content: str
    line: int  # 1-indexed, absolute within the file — the ``` line itself


@dataclass
class ParsedMarkdown:
    raw_text: str
    body_text: str
    body_start_line: int  # 1-indexed absolute line where body_text begins
    metadata: dict
    metadata_error: str | None
    headings: list[Heading]
    fences: list[Fence]
    fenced_lines: set[int]  # absolute 1-indexed line numbers inside any fence


def line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def parse_markdown_file(md_file: Path) -> ParsedMarkdown:
    raw_text = md_file.read_text(encoding="utf-8")

    metadata: dict = {}
    metadata_error: str | None = None
    body_text = raw_text
    body_start_line = 1
    if raw_text.startswith("---"):
        try:
            post = frontmatter.loads(raw_text)
            metadata = post.metadata
            body_text = post.content
            idx = raw_text.find(post.content)
            body_start_line = line_of(raw_text, idx) if idx != -1 else 1
        except Exception as e:  # malformed YAML frontmatter
            metadata_error = str(e)

    tokens = MD.parse(body_text)
    headings: list[Heading] = []
    fences: list[Fence] = []
    fenced_lines: set[int] = set()

    for i, tok in enumerate(tokens):
        if tok.type == "heading_open" and tok.map:
            level = int(tok.tag[1:])
            content_tok = tokens[i + 1] if i + 1 < len(tokens) else None
            text = content_tok.content if content_tok and content_tok.type == "inline" else ""
            headings.append(Heading(level=level, text=text, line=body_start_line + tok.map[0]))
        elif tok.type == "fence" and tok.map:
            lang = (tok.info or "").strip().split()[0].lower() if tok.info else ""
            fences.append(Fence(lang=lang, content=tok.content, line=body_start_line + tok.map[0]))
            fenced_lines.update(range(body_start_line + tok.map[0], body_start_line + tok.map[1]))

    return ParsedMarkdown(
        raw_text=raw_text,
        body_text=body_text,
        body_start_line=body_start_line,
        metadata=metadata,
        metadata_error=metadata_error,
        headings=headings,
        fences=fences,
        fenced_lines=fenced_lines,
    )


def check_frontmatter(skill_md: Path, parsed: ParsedMarkdown, findings: list[Finding]) -> None:
    if not parsed.raw_text.startswith("---"):
        findings.append(Finding(skill_md, "missing YAML frontmatter (file should start with '---')", 1))
        return
    if parsed.metadata_error:
        findings.append(Finding(skill_md, f"invalid frontmatter YAML: {parsed.metadata_error}", 1))
        return

    for key in ("name", "description", "license"):
        if key not in parsed.metadata:
            findings.append(Finding(skill_md, f"frontmatter missing required key '{key}'"))

    description = str(parsed.metadata.get("description", ""))
    if description and not re.search(r"do not|don't", description, re.IGNORECASE):
        findings.append(
            Finding(
                skill_md,
                "description has no 'Do NOT' scope-boundary clause - add one so overlapping "
                "skills (or future ones) know when NOT to trigger this skill",
            )
        )


def check_dependencies_section(skill_md: Path, parsed: ParsedMarkdown, findings: list[Finding]) -> None:
    if not any(h.text.strip().lower() == "dependencies" for h in parsed.headings):
        findings.append(
            Finding(skill_md, "no 'Dependencies' section - list required tools/libraries and versions")
        )


def check_section_headers(skill_md: Path, parsed: ParsedMarkdown, findings: list[Finding]) -> None:
    if sum(1 for h in parsed.headings if h.level >= 2) < 2:
        findings.append(
            Finding(skill_md, "fewer than 2 '##' section headers - organize content into clear sections")
        )


def check_overview_section(skill_md: Path, parsed: ParsedMarkdown, findings: list[Finding]) -> None:
    if not any(OVERVIEW_KEYWORDS_RE.match(h.text.strip()) for h in parsed.headings):
        findings.append(
            Finding(
                skill_md,
                "no 'Overview' / 'Quick Start' / 'When to...' section - add one early so "
                "Claude can quickly tell when this skill applies",
            )
        )


MAX_FILE_LINES = 510


def check_file_length(md_file: Path, parsed: ParsedMarkdown, findings: list[Finding]) -> None:
    line_count = parsed.raw_text.count("\n") + 1
    if line_count > MAX_FILE_LINES:
        findings.append(
            Finding(
                md_file,
                f"{line_count} lines, over the {MAX_FILE_LINES}-line guideline - "
                "consider splitting into another references/ file",
            )
        )


def check_gotchas_section(skill_dir: Path, parsed_files: dict[Path, ParsedMarkdown], findings: list[Finding]) -> None:
    for parsed in parsed_files.values():
        if any(GOTCHA_KEYWORDS_RE.search(h.text) for h in parsed.headings):
            return
    findings.append(
        Finding(
            skill_dir / "SKILL.md",
            "no Gotchas/Anti-Patterns/Known-Issues/Rules section found anywhere in the skill - "
            "document critical pitfalls, not just the happy path",
        )
    )


def check_cross_references(skill_dir: Path, skill_md: Path, parsed: ParsedMarkdown, findings: list[Finding]) -> None:
    mentioned: set[str] = set()
    for m in REF_PATH_RE.finditer(parsed.raw_text):
        raw = m.group(0).rstrip(".,)")
        mentioned.add(raw)
        target = skill_dir / raw
        if not target.exists():
            findings.append(
                Finding(skill_md, f"references non-existent path '{raw}'", line_of(parsed.raw_text, m.start()))
            )

    for sub in ("references", "templates"):
        subdir = skill_dir / sub
        if not subdir.is_dir():
            continue
        for f in subdir.rglob("*"):
            if f.is_dir():
                continue
            rel = f.relative_to(skill_dir).as_posix()
            if rel not in mentioned and not any(rel.startswith(m.rstrip("/") + "/") for m in mentioned):
                findings.append(Finding(skill_md, f"'{rel}' exists but is never mentioned in SKILL.md (orphan / possible typo target)"))


def check_backtick_balance(md_file: Path, parsed: ParsedMarkdown, findings: list[Finding]) -> None:
    for i, line in enumerate(parsed.raw_text.splitlines(), start=1):
        if i in parsed.fenced_lines:
            continue
        if line.count("`") % 2 != 0:
            findings.append(Finding(md_file, "odd number of backticks on line (unbalanced inline code)", i))


def check_transcription_artifacts(md_file: Path, parsed: ParsedMarkdown, findings: list[Finding]) -> None:
    for m in LATEX_ARTIFACT_RE.finditer(parsed.raw_text):
        findings.append(Finding(md_file, f"leftover LaTeX artifact '{m.group(0)}' (expected a plain arrow/symbol)", line_of(parsed.raw_text, m.start())))
    for m in MANGLED_DUNDER_RE.finditer(parsed.raw_text):
        word = m.group(1)
        findings.append(Finding(md_file, f"'**{word}**' looks like a mangled '__{word}__' dunder", line_of(parsed.raw_text, m.start())))


def check_tables(md_file: Path, parsed: ParsedMarkdown, findings: list[Finding]) -> None:
    lines = parsed.raw_text.splitlines()
    i = 0
    while i < len(lines):
        line_no = i + 1
        line = lines[i]
        is_fenced = line_no in parsed.fenced_lines
        if (
            not is_fenced
            and line.strip().startswith("|")
            and i + 1 < len(lines)
            and re.match(r"^\s*\|?[\s:-]+\|", lines[i + 1])
        ):
            header_cols = line.count("|")
            sep_cols = lines[i + 1].count("|")
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                row_cols = lines[j].count("|")
                if row_cols != header_cols or sep_cols != header_cols:
                    findings.append(
                        Finding(
                            md_file,
                            f"table row has {row_cols} '|' but header has {header_cols} - likely an unescaped '|' inside a cell",
                            j + 1,
                        )
                    )
                j += 1
            i = j
            continue
        i += 1


def check_code_blocks(md_file: Path, parsed: ParsedMarkdown, findings: list[Finding]) -> None:
    for fence in parsed.fences:
        lang = fence.lang
        body = fence.content
        start_line = fence.line

        if lang == "python":
            if PLACEHOLDER_TOKEN_RE.search(body):
                continue  # e.g. `from <package>.routes import ...` — intentional template syntax
            try:
                ast.parse(stub_missing_bodies(body))
            except SyntaxError as e:
                findings.append(Finding(md_file, f"invalid python in code block: {e}", start_line))

        elif lang == "json":
            cleaned = re.sub(r"(?<!:)//.*$", "", body, flags=re.MULTILINE)
            cleaned = JSON_ELLIPSIS_OBJECT_RE.sub("{}", cleaned)
            cleaned = JSON_ELLIPSIS_VALUE_RE.sub("null", cleaned)
            try:
                parse_possibly_multi_json(cleaned)
            except json.JSONDecodeError as e:
                findings.append(Finding(md_file, f"invalid json in code block: {e}", start_line))

        elif lang == "toml":
            try:
                tomllib.loads(body)
            except tomllib.TOMLDecodeError as e:
                findings.append(Finding(md_file, f"invalid toml in code block: {e}", start_line))

        elif lang in ("ts", "tsx", "typescript", "javascript", "js", "jsx"):
            stack: list[str] = []
            for ch in body:
                if ch in BRACKET_PAIRS:
                    stack.append(BRACKET_PAIRS[ch])
                elif ch in BRACKET_PAIRS.values():
                    if not stack or stack[-1] != ch:
                        findings.append(Finding(md_file, f"unbalanced '{ch}' in {lang} code block", start_line))
                        break
                    stack.pop()
            else:
                if stack:
                    findings.append(Finding(md_file, f"unclosed {stack} in {lang} code block", start_line))


def verify_skill(skill_dir: Path) -> SkillReport:
    report = SkillReport(name=skill_dir.name)
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        report.findings.append(Finding(skill_dir, "missing SKILL.md"))
        return report

    md_files = sorted(skill_dir.rglob("*.md"))
    parsed_files = {f: parse_markdown_file(f) for f in md_files}
    skill_md_parsed = parsed_files[skill_md]

    check_frontmatter(skill_md, skill_md_parsed, report.findings)
    check_dependencies_section(skill_md, skill_md_parsed, report.findings)
    check_section_headers(skill_md, skill_md_parsed, report.findings)
    check_overview_section(skill_md, skill_md_parsed, report.findings)
    check_gotchas_section(skill_dir, parsed_files, report.findings)
    check_cross_references(skill_dir, skill_md, skill_md_parsed, report.findings)

    for md_file, parsed in parsed_files.items():
        check_backtick_balance(md_file, parsed, report.findings)
        check_transcription_artifacts(md_file, parsed, report.findings)
        check_tables(md_file, parsed, report.findings)
        check_code_blocks(md_file, parsed, report.findings)
        check_file_length(md_file, parsed, report.findings)

    return report


def main() -> int:
    skills_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "skills"
    if not skills_dir.is_dir():
        print(f"skills directory not found: {skills_dir}")
        return 1

    reports = [verify_skill(d) for d in sorted(skills_dir.iterdir()) if d.is_dir()]
    any_failed = False

    for report in reports:
        status = "PASS" if report.ok else "FAIL"
        print(f"[{status}] {report.name}")
        for finding in report.findings:
            print(f"    {finding}")
        if not report.ok:
            any_failed = True

    print()
    print(f"{len(reports)} skill(s) checked, {sum(not r.ok for r in reports)} with findings")
    return 1 if any_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
