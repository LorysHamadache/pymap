#!/usr/bin/env python3
import os
import ast
import logging
from typing import Dict, Set, List, Tuple, Optional
import sys
import argparse


logging.basicConfig(level=logging.INFO)

# ---------- Helpers for parsing ----------
def get_arg_type(arg) -> str:
    if arg.annotation is not None:
        return ast.unparse(arg.annotation) if hasattr(ast, "unparse") else ast.dump(arg.annotation)
    return "Any"

def get_return_type(node) -> str:
    if node.returns is not None:
        return ast.unparse(node.returns) if hasattr(ast, "unparse") else ast.dump(node.returns)
    return "Any"

def get_module_name(file_path: str, root: str) -> str:
    rel = os.path.relpath(file_path, root)
    parts = rel.split(os.sep)
    if parts[-1].endswith('.py'):
        parts[-1] = parts[-1][:-3]
    if parts[-1] == '__init__':
        parts = parts[:-1]
    return ".".join(parts)

# ---------- Main Analysis Passes ----------

def collect_functions_and_imports(py_files: List[str], root: str):
    """
    Returns:
        - all_functions: Dict[full_name, (file_path, FunctionDef/AsyncFunctionDef node, class_name or None)]
        - module_imports: Dict[module, {alias: real_module}]
        - symbol_imports: Dict[module, {local_name: imported_from_module}]
    """
    all_functions = dict()   # qualified_name -> (file, node, class_name/None)
    module_imports = dict()  # module -> {alias: real_module}
    symbol_imports = dict()  # module -> {local_name: from_module}
    for file_path in py_files:
        module = get_module_name(file_path, root)
        module_imports[module] = {}
        symbol_imports[module] = {}
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source, filename=file_path)
        except Exception as e:
            logging.error(f"Failed to parse {file_path}: {e}")
            continue
        for node in tree.body:
            # functions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_name = f"{module}.{node.name}"
                all_functions[func_name] = (file_path, node, None)
            elif isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        func_name = f"{module}.{node.name}.{item.name}"
                        all_functions[func_name] = (file_path, item, node.name)
            # imports
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    module_imports[module][alias.asname or alias.name] = alias.name
            elif isinstance(node, ast.ImportFrom):
                mod = node.module
                for alias in node.names:
                    # from X import Y as Z => local name: Z or Y, from_module: X
                    local = alias.asname or alias.name
                    symbol_imports[module][local] = (mod, alias.name)
    return all_functions, module_imports, symbol_imports

def build_function_call_graph(py_files: List[str], root: str, all_functions: Dict, module_imports: Dict, symbol_imports: Dict):
    """
    Returns:
        function_details: Dict[qualified_name, Dict with arguments/types/return/calls]
    """
    # Reverse mapping: symbol -> qualified name (for cross-module calls)
    symbol_to_func = {}
    for qname in all_functions:
        short = qname.split(".")[-1]
        symbol_to_func.setdefault(short, set()).add(qname)

    # Mapping: per function, all info
    function_details = {}
    for qname, (file_path, node, class_name) in all_functions.items():
        # Arguments and return type
        args = [(arg.arg, get_arg_type(arg)) for arg in node.args.args]
        return_type = get_return_type(node)
        # Figure out module for resolving imports
        module = get_module_name(file_path, root)
        # Now collect called functions (names)
        called = set()
        for call_node in ast.walk(node):
            if isinstance(call_node, ast.Call):
                name = None
                # Normal function call: foo()
                if isinstance(call_node.func, ast.Name):
                    name = call_node.func.id
                # Method call: self.bar(), cls.bar()
                elif isinstance(call_node.func, ast.Attribute):
                    if isinstance(call_node.func.value, ast.Name):
                        name = call_node.func.attr
                if name:
                    resolved = resolve_function_name(name, module, module_imports, symbol_imports, all_functions, symbol_to_func)
                    # *** Only include if resolved to a project function ***
                    if resolved and any(r in all_functions for r in resolved):
                        called.update(r for r in resolved if r in all_functions)
        function_details[qname] = {
            "args": args,
            "return": return_type,
            "calls": called
        }
    return function_details

def resolve_function_name(name, current_module, module_imports, symbol_imports, all_functions, symbol_to_func) -> Optional[Set[str]]:
    """
    Try to resolve a function name (called in current_module) to its fully qualified name(s).
    - Checks: local, imported as symbol, imported module alias, global matches.
    """
    # 1. Check local (same module)
    possible = set()
    for candidate in all_functions:
        if candidate.startswith(current_module + ".") and candidate.split(".")[-1] == name:
            possible.add(candidate)
    if possible:
        return possible
    # 2. Check symbol imports (from x import y)
    if name in symbol_imports.get(current_module, {}):
        from_mod, orig_name = symbol_imports[current_module][name]
        target = f"{from_mod}.{orig_name}"
        # Try to match in all_functions
        resolved = {k for k in all_functions if k.endswith(f".{orig_name}") and k.startswith(from_mod or "")}
        if resolved:
            return resolved
    # 3. Check if called via module alias: mod.foo()
    # (not handled directly here without deeper AST inspection, left as extension)
    # 4. Check globally (any function with matching name)
    if name in symbol_to_func:
        return symbol_to_func[name]
    return None

# ---------- Markdown Output ----------

def write_markdown(root: str, function_details: Dict, all_functions: Dict):
    lines = ["# Project-wide Function Mapping\n"]
    lines.append("## Functions (with cross-file call analysis)\n")
    for qname, details in sorted(function_details.items()):
        args_str = ", ".join(f"{n}: {t}" for n, t in details["args"])
        lines.append(f"### `{qname}({args_str}) -> {details['return']}`")
        if details["calls"]:
            calls_str = ", ".join(sorted(details["calls"]))
            lines.append(f"- Calls: `{calls_str}`")
        else:
            lines.append("- Calls: None")
        lines.append("")
    # Optionally: index all functions per file/module
    return "\n".join(lines)

# ---------- Entry point ----------

def find_python_files(root: str, ignore_dirs: Set[str]):
    py_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]
        for f in filenames:
            if f.endswith(".py"):
                py_files.append(os.path.join(dirpath, f))
    return py_files

def load_ignore_dirs(root: str) -> Set[str]:
    # Just directory names, not paths
    ignore = {".git", "__pycache__"}
    gitignore = os.path.join(root, ".gitignore")
    if os.path.exists(gitignore):
        with open(gitignore) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                name = line.rstrip("/").lstrip("*/")
                if name:
                    ignore.add(name)
    return ignore

def main():
    parser = argparse.ArgumentParser(description="Generate a function/call mapping for a Python project.")
    parser.add_argument("root", nargs="?", default=os.getcwd(), help="Project root (default: current directory)")
    args = parser.parse_args()
    root = os.path.abspath(args.root)
    ignore_dirs = load_ignore_dirs(root)
    py_files = find_python_files(root, ignore_dirs)
    logging.info(f"Found {len(py_files)} Python files")
    all_functions, module_imports, symbol_imports = collect_functions_and_imports(py_files, root)
    function_details = build_function_call_graph(py_files, root, all_functions, module_imports, symbol_imports)
    md = write_markdown(root, function_details, all_functions)
    with open(os.path.join(root, "mapping.md"), "w", encoding="utf-8") as f:
        f.write(md)
    print("Wrote mapping.md")


if __name__ == "__main__":
    main()
