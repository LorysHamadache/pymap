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

**(Optional: CLI install)**

'''
pip install --user .
'''

### 2. RUN

'''
pymap
'''

or

'''
pymap /path/to/any/python/project
'''
