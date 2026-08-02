# Ruff Configuration

Add this to your `pyproject.toml`:

```toml
[project]
name = "mypackage"
version = "1.0.0"
requires-python = ">=3.13"
dependencies = [
    "requests>=2.31.0",
    "pydantic>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.5.0",
]

[tool.ruff]
exclude = [
    ".ruff_cache",
    ".git",
    ".venv",
    ".vscode",
    ".github",
    ".pytest_cache",
    "reference"
]
extend-include = []
line-length = 120
indent-width = 4
target-version = "py313"

[tool.ruff.lint]
select = ["ALL"]
ignore = [
    "ANN204",
    "ANN401",
    "E731",
    "D",
    "DTZ005",
    "BLE001",
    "B008",
    "CPY001",
    "COM812",
    "ERA001",
    "EM101",
    "EM102",
    "FA",
    "FBT",
    "PTH123",
    "ISC001",
    "C901",
    "PLR0912",
    "PLR0913",
    "PLR0915",
    "TRY003"
]
fixable = ["ALL"]

# Per-file ignores
[tool.ruff.lint.per-file-ignores]
"tests/**" = ["T201", "S101", "PLR2004", "ANN"]  # More permissive for tests
"examples/**" = ["T201", "INP001", "ANN"]  # Allow prints and no __init__ in examples
"scripts/**" = ["T201", "INP001", "ANN"]  # Allow prints and no __init__ in examples
"*_test.py" = ["T201", "S101", "PLR2004", "ANN"]  # Test files
"test_*.py" = ["T201", "S101", "SLF001", "PLR2004", "ANN"]  # Test files

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"
docstring-code-format = false
docstring-code-line-length = "dynamic"

```

## Rule Categories Explained

| Ignored Rule | Reason |
| --- | --- |
| **ANN204** | Missing return type annotation for special method |
| **D** | All docstring rules (too verbose for rapid development) |
| **ERA001** | Commented out code (useful during development) |
| **FBT** | Boolean trap (sometimes necessary) |
| **TRY** | Try/except style (too opinionated) |
