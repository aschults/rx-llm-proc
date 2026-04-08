"""
A simple command-line tool to enforce a clean namespace by checking
for symbol imports from external packages.

This script recursively scans a directory for Python files and verifies that
all `from <package> import <symbol>` statements are only used for submodules,
not for importing individual classes, functions, or variables from external
libraries (with the exception of a configurable WHITELIST).

This helps maintain a clear and explicit codebase where the origin of symbols
is always apparent.
"""

import ast
import importlib.util
import sys
import argparse
from pathlib import Path

# Packages allowed to export symbols directly for sanity
WHITELIST = {"typing", "abc", "__future__", "typing_extensions"}


def is_submodule(parent_module_str: str, member_name: str) -> bool:
    """Checks if 'member_name' is a submodule of 'parent_module_str'."""
    try:
        full_path = (
            f"{parent_module_str}.{member_name}"
            if parent_module_str
            else member_name
        )
        spec = importlib.util.find_spec(full_path)
        return spec is not None
    except (ImportError, AttributeError, ValueError):
        return False


def check_file(path: Path, verbose: bool = False) -> int:
    """
    Parses a Python file and checks for non-module imports.

    Args:
        path (Path): The path to the Python file.
        verbose (bool): Whether to print verbose output.

    Returns:
        int: The number of import violations found.
    """
    violations = 0
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except Exception as e:
        if verbose:
            print(f"Skipping {path}: {e}")
        return 0

    for node in ast.walk(tree):
        # Case 1: 'from x import y [as z]'
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module in WHITELIST or node.level > 0:
                continue

            for alias in node.names:
                if not is_submodule(node.module, alias.name):
                    print(
                        f"❌ {path}:{node.lineno} -> Found symbol import: 'from {node.module} import {alias.name}'"
                    )
                    violations += 1

        # Case 2: 'import x [as y]'
        # This is almost always okay, but we check to ensure 'x' is a module
        # (Though 'import' without 'from' can ONLY import modules in Python)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                # alias.name is the real module, alias.asname is your 'rx'
                if not is_submodule("", alias.name):
                    print(
                        f"❌ {path}:{node.lineno} -> Found invalid import: 'import {alias.name}'"
                    )
                    violations += 1

    return violations


def main() -> None:
    """
    Main entry point for the import checker script.

    Parses command-line arguments, recursively finds Python files,
    checks them for import violations, and exits with a status code.
    """
    parser = argparse.ArgumentParser(
        description="Enforce module-only imports (aliases allowed)."
    )
    parser.add_argument("path", type=str, help="Directory or file to scan")
    args = parser.parse_args()

    root = Path(args.path)
    total_violations = 0

    files = root.rglob("*.py") if root.is_dir() else [root]

    for python_file in files:
        if any(
            part.startswith(".") or part == "__pycache__"
            for part in python_file.parts
        ):
            continue
        total_violations += check_file(python_file)

    if total_violations > 0:
        print(
            f"\nTotal violations: {total_violations}. Only modules/submodules may be imported."
        )
        sys.exit(1)
    else:
        print("✅ Namespace check passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
