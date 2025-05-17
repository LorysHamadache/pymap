# Python Codebase Mapping Tool

## Overview

This tool generates a comprehensive mapping of any Python project's source code, including:

- All user-defined functions and methods
- Their argument names, types, and return types (from type hints)
- All calls to other user-defined functions, even across files (cross-file analysis)
- Ignores standard library/external calls for clarity

**Purpose:**  
This mapping is designed to serve as precise context input for LLMs (Large Language Models) and AI agents, enabling them to understand, summarize, or refactor your codebase efficiently.  
It is ideal for code understanding, automated documentation, and codebase onboarding.

---

## Features

- **Project-wide static analysis** (no code execution needed)
- **Cross-file call graph:** identifies and links user function calls, even when imported from other files
- **Argument and return type extraction** (uses type hints when available)
- **Easy integration with LLM/AI agents** (mapping output in Markdown for simple ingestion)
- **No third-party dependencies:** 100% standard library
- **CLI usage:** Run from anywhere, point at any Python project

---

## Usage

### 1. Installation

Clone this repo or copy `generate_mapping.py` to your preferred tools folder.

**Optional: Install as CLI tool**

If you want to run as `pymap` from anywhere, add a `setup.py` as described below and install:

```bash
pip install --user .
# or, if you use pipx (recommended for global scripts)
pipx install .


```

### 2. RUN

From the project directory, simply run:

```bash
pymap
```

or to analyze any project folder:

```bash
pymap /path/to/any/python/project
```

Or run directly with Python:

```bash
python generate_mapping.py /path/to/any/python/project
```

### 2. OUTPUT

The script generates a mapping.md file in your target project directory containing:
All functions/methods with their argument names, types, and return type.
All calls to other user-defined functions/methods, across the project.
No external or standard library calls included.
This file is ideal as context for LLM and agent workflows.

```markdown
### `my_module.my_func(x: int, y: str) -> float`

- Calls: `other_module.another_func`

### `my_module.MyClass.class_method(self: Any, z: list) -> None`

- Calls: None
```

## Notes

- Only user-defined function and method calls are included; external library calls are excluded.
- Ignores directories listed in your .gitignore, as well as .git and **pycache** by default.
- 100% standard library. No external dependencies required.
