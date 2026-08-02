"""Static verification for skills/ directories.

Catches transcription damage (typo'd filenames, broken cross-links, mangled
markdown, invalid embedded code) without needing any third-party deps.

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

CODE_FENCE_RE = re.compile(r"```([\w.+-]*)\n(.*?)```", re.DOTALL)
REF_PATH_RE = re.compile(r"\b(?:references|templates)/[\w.\-/]+")
LATEX_ARTIFACT_RE = re.compile(r"\$\\[a-zA-Z]+\$")
MANGLED_DUNDER_RE = re.compile(
    r"\*\*(init|slots|all|name|main|repr|eq|call|enter|exit|new|len|iter|next|str|post_init)\*\*"
)
PLACEHOLDER_TOKEN_RE = re.compile(r"<[a-zA-Z_][\w]*>")
BLOCK_HEADER_RE = re.compile(
    r"^(\s*)(def |class |if |elif |else|for |while |with |try|except|finally).*:\s*(#.*)?$"
)
JSON_ELLIPSIS_OBJECT_RE = re.compile(r"\{\s*\.\.\.\s*\}")
JSON_ELLIPSIS_VALUE_RE = re.compile(r"(?<=:\s)\.\.\.(?=\s*[,}\]])")
BRACKET_PAIRS = {"{": "}", "(": ")", "[": "]"}


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


def line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def check_frontmatter(skill_md: Path, findings: list[Finding]) -> None:
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        findings.append(Finding(skill_md, "missing opening '---' frontmatter fence", 1))
        return
    end = text.find("\n---", 4)
    if end == -1:
        findings.append(Finding(skill_md, "missing closing '---' frontmatter fence"))
        return
    frontmatter = text[4:end]
    for key in ("name:", "description:"):
        if key not in frontmatter:
            findings.append(Finding(skill_md, f"frontmatter missing required key '{key}'"))


def check_cross_references(skill_dir: Path, skill_md: Path, findings: list[Finding]) -> None:
    text = skill_md.read_text(encoding="utf-8")
    mentioned: set[str] = set()
    for m in REF_PATH_RE.finditer(text):
        raw = m.group(0).rstrip(".,)")
        mentioned.add(raw)
        target = skill_dir / raw
        if not target.exists():
            findings.append(
                Finding(skill_md, f"references non-existent path '{raw}'", line_of(text, m.start()))
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


def check_backtick_balance(md_file: Path, findings: list[Finding]) -> None:
    text = md_file.read_text(encoding="utf-8")
    in_fence = False
    for i, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.count("`") % 2 != 0:
            findings.append(Finding(md_file, "odd number of backticks on line (unbalanced inline code)", i))


def check_transcription_artifacts(md_file: Path, findings: list[Finding]) -> None:
    text = md_file.read_text(encoding="utf-8")
    for m in LATEX_ARTIFACT_RE.finditer(text):
        findings.append(Finding(md_file, f"leftover LaTeX artifact '{m.group(0)}' (expected a plain arrow/symbol)", line_of(text, m.start())))
    for m in MANGLED_DUNDER_RE.finditer(text):
        word = m.group(1)
        findings.append(Finding(md_file, f"'**{word}**' looks like a mangled '__{word}__' dunder", line_of(text, m.start())))


def check_tables(md_file: Path, findings: list[Finding]) -> None:
    text = md_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    in_fence = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("```"):
            in_fence = not in_fence
            i += 1
            continue
        if not in_fence and line.strip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?[\s:-]+\|", lines[i + 1]):
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


def check_code_blocks(md_file: Path, findings: list[Finding]) -> None:
    text = md_file.read_text(encoding="utf-8")
    for m in CODE_FENCE_RE.finditer(text):
        lang = m.group(1).lower()
        body = m.group(2)
        start_line = line_of(text, m.start())

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

    check_frontmatter(skill_md, report.findings)
    check_cross_references(skill_dir, skill_md, report.findings)

    for md_file in skill_dir.rglob("*.md"):
        check_backtick_balance(md_file, report.findings)
        check_transcription_artifacts(md_file, report.findings)
        check_tables(md_file, report.findings)
        check_code_blocks(md_file, report.findings)

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
