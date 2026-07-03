# Open Source Release Checklist

Before publishing AutoFrame to GitHub:

- Replace placeholder project URLs in `pyproject.toml`.
- Confirm package name availability if publishing to PyPI.
- Run `python -m compileall autoframe`.
- Run `python -m pytest autoframe/modules/ecosystem -q`.
- Run an integration scan against a local demo service.
- Review generated reports and inventory exports for private paths or sensitive data.
- Confirm `LICENSE`, `README.md`, `SECURITY.md`, `CONTRIBUTING.md`, and GitHub templates are present.
- Create a first GitHub release tag, for example `v2.0.0`.
- Add screenshots or sample reports if you want a more polished README.

Recommended demo commands:

```bash
python -m autoframe export --url http://localhost:8080 --project /path/to/demo --output-dir reports/inventory
python -m autoframe run --url http://localhost:8080 --project /path/to/demo --modules api,endpoint_matrix,source_matrix,ecosystem
```

Optional ecosystem follow-ups:

- Add a Schemathesis runner that consumes `reports/inventory/openapi.json`.
- Add a k6 script generator from discovered safe GET endpoints.
- Add a ZAP baseline wrapper for opt-in DAST runs.
- Add RESTler compile/test integration for OpenAPI exports.
