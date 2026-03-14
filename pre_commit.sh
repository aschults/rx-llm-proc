#/bin/bash
set -x -e

export  PYRIGHT_PYTHON_FORCE_VERSION=latest

if [[ -n "$VIRTUAL_ENV" ]] ; then
    echo already in venv. using deactivate on prompt
    deactivate || true
fi

if ! [[ -d ".venv" ]] ; then
    python3 -m venv .venv
    .venv/bin/pip install -U pip
    .venv/bin/pip install -r requirements.txt
fi

source .venv/bin/activate

if ! black --check rxllmproc tests ; then
  black --diff rxllmproc tests
  exit 1
fi
flake8 rxllmproc tests \
  --ignore=E203,E501,C901,W503 \
  --statistics \
  --max-line-length=80
flake8 rxllmproc tests \
  --ignore=E203,E501,W503 \
  --select C901 \
  --show-source \
  --statistics \
  --max-complexity=10 \
  --max-line-length=80 || true
pydocstyle rxllmproc tests --convention=google || true
python3 import_checker.py rxllmproc
# pytype rxllmproc tests -P .:tests -j 4 --strict-primitive-comparisons --strict-import --precise-return --strict-parameter-checks
PYTHONPATH=.:tests pyright --dependencies #--stats
pytest --cov=rxllmproc/ --cov-report=term --cov-report=lcov

deactivate

# python3 -m build
venv_path=/tmp/rxllmproc_pre_commit_test
python3 -m venv --clear "${venv_path}"
"${venv_path}/bin/pip3" install .
"${venv_path}/bin/gmail_cli" --help 2>&1 | grep -- "verbose"
