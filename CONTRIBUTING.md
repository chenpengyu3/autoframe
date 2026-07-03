# Contributing

Thanks for helping improve AutoFrame.

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
python -m compileall autoframe
python -m pytest autoframe/modules/source_matrix autoframe/modules/ecosystem -q
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .[dev]
python -m compileall autoframe
python -m pytest autoframe/modules/source_matrix autoframe/modules/ecosystem -q
```

## Pull Request Checklist

- Keep changes small and reviewable.
- Add or update tests for behavior changes.
- Do not commit secrets, tokens, local reports, virtual environments, or target project data.
- Prefer auto-discovery and source-derived behavior over project-specific hardcoding.
- Runtime write tests must avoid destructive behavior and treat business 4xx rejection differently from server 5xx errors.
- Update README or examples when adding user-visible behavior.

## Test Module Guidelines

- Every module must have a `plugin.py` implementing `TestModule`.
- Add a pytest marker in `pytest.ini` and `pyproject.toml`.
- Add the module to `config/default.yaml` only when it is safe by default.
- Dynamic matrix modules should parametrize discovered objects and use pass-through behavior for non-applicable inventories.

## Reporting

When adding a test, add a concise description in `autoframe/reporting/generator.py` so HTML reports remain readable.
