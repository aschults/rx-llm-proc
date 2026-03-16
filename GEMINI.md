
When running python or related binaries, always add environment 
`PYTHONPATH=.:tests`

For unit tests use `.venv/bin/pytest`

To get documentation up to standard check
`.venv/bin/pydocstyle rxllmproc tests --convention=google`

For type checking use `.venv/bin/pyright --dependencies`

## Import Constraints
To maintain a clear and explicit codebase where the origin of symbols is always apparent, the following import constraints are enforced:
- **Module-only imports:** `from <package> import <symbol>` statements must only be used for submodules, not for individual classes, functions, or variables.
- **Whitelisted exceptions:** The following packages are allowed to export symbols directly for sanity: `typing`, `abc`, `__future__`, `pydantic`, `typing_extensions`.
- **Typing consistency:** For whitelisted typing packages, import individual members consistently (e.g., `from typing import cast, Optional`).

## Logging Constraints
- **Lazy formatting:** For all logging calls, use lazy `%` formatting (e.g., `logger.info("msg %s", arg)`) instead of f-strings or `.format()` to avoid unnecessary string interpolation if the log level is not enabled.

For import namespace checking, use the following command:
```bash
python3 import_checker.py rxllmproc
```

Flake test1:
```bash
.venv/bin/flake8 rxllmproc tests \
  --ignore=E203,E501,C901,W503 \
  --statistics \
  --max-line-length=80
```

Flake test2:
```bash
.venv/bin/flake8 rxllmproc tests \
  --ignore=E203,E501,W503 \
  --select C901 \
  --show-source \
  --statistics \
  --max-complexity=10 \
  --max-line-length=80
```
