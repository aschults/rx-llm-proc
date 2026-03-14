
When running python or related binaries, always add environment 
`PYTHONPATH=.:tests`

For unit tests use `.venv/bin/pytest`

To get documentation up to standard check
`.venv/bin/pydocstyle rxllmproc tests --convention=google`

For type checking use `.venv/bin/pyright --dependencies`

For import namespace checking:
```
python3 import_checker.py rxllmproc
```

Flake test1:
```
.venv/bin/flake8 rxllmproc tests \
  --ignore=E203,E501,C901,W503 \
  --statistics \
  --max-line-length=80
```

Flake test2:
```
.venv/bin/flake8 rxllmproc tests \
  --ignore=E203,E501,W503 \
  --select C901 \
  --show-source \
  --statistics \
  --max-complexity=10 \
  --max-line-length=80
```

