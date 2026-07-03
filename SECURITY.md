# Security Policy

## Supported Versions

Security fixes target the latest released version on the default branch.

## Reporting a Vulnerability

Please do not open a public issue for a suspected vulnerability. Report it privately to the maintainers.

Include:

- Affected AutoFrame version or commit
- Reproduction steps
- Impact and affected module
- Whether secrets, tokens, or target project data are involved

## Handling Secrets

AutoFrame should never require secrets in source-controlled files. Use environment variables such as:

- `AUTOFRAME_AUTH_TOKEN`
- `AUTOFRAME_DB_URL`
- `AUTOFRAME_BASE_URL`
- `AUTOFRAME_PROJECT_PATH`

Reports may include endpoint paths, status codes, timings, and test names. Avoid publishing reports from private systems without review.

## Safe Testing Expectations

Security and fuzzing checks must avoid destructive payloads by default. High-risk active scans should be opt-in and documented.
