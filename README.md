# AutoFrame

AutoFrame is an auto-adaptive testing framework for Spring Boot and Python services. It discovers a target project, expands the discovered inventory into pytest matrices, runs API/security/performance/concurrency/database/source checks, and generates HTML/JUnit reports.

## What AutoFrame Tests

- API inventory, safe runtime checks, special endpoints, request schema fields, and CRUD candidates
- Spring Boot source structure: controllers, route methods, services, repositories, entities, scheduled jobs, transactions, injection points
- Python/Spring source files, manifests, config files, dependencies, route annotations
- Live database schema: tables, columns, primary keys, foreign keys, indexes, unique constraints, field types
- Security and DAST baselines: auth bypass, SQL injection probes, XSS reflection, path traversal, sensitive static files
- Performance and reliability: latency, load, throughput, stress, timeout, degradation, recovery
- Protocol compatibility: HEAD, OPTIONS, Accept variants, gzip negotiation, cache headers
- Optional ecosystem readiness: Schemathesis, k6, OWASP ZAP baseline, RESTler, Docker, Java, Maven, Gradle, pytest

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .
python -m autoframe run --url http://localhost:8080 --project C:\path\to\your\project -v
```

For authenticated APIs, provide a bearer token through an environment variable:

```powershell
$env:AUTOFRAME_AUTH_TOKEN="your-token"
python -m autoframe run --url http://localhost:8080 --project C:\path\to\your\project -v
```

## Common Commands

Run all default modules:

```bash
python -m autoframe run --url http://localhost:8080 --project /path/to/project
```

Run selected modules:

```bash
python -m autoframe run --url http://localhost:8080 --project /path/to/project --modules api,endpoint_matrix,security
```

Export discovered inventory for other tools:

```bash
python -m autoframe export --url http://localhost:8080 --project /path/to/project --output-dir reports/inventory
```

This writes:

- `inventory.json`: full redacted AutoFrame discovery inventory
- `openapi.json`: source/runtime-derived OpenAPI 3.0 contract
- `postman_collection.json`: Postman collection for manual and CI workflows
- `summary.md`: readable discovery summary

Skip HTML report generation:

```bash
python -m autoframe run --url http://localhost:8080 --project /path/to/project --no-report
```

## Reports

AutoFrame writes timestamped HTML reports and JUnit XML files into `reports/`, plus a latest-copy HTML report:

- `reports/report_dev_<timestamp>.html`
- `reports/report_dev.html`
- `reports/junit_dev_<timestamp>.xml`

## Optional External Tools

AutoFrame does not require these tools, but it detects and reports readiness for mature testing ecosystems:

- Schemathesis for OpenAPI/schema-based property testing
- Microsoft RESTler for stateful REST API fuzzing
- OWASP ZAP baseline for passive DAST
- k6 for load testing
- Docker/Testcontainers-style integration environments

Tool command overrides:

```bash
AUTOFRAME_SCHEMATHESIS_CMD=schemathesis
AUTOFRAME_K6_CMD=k6
AUTOFRAME_ZAP_BASELINE_CMD=zap-baseline.py
AUTOFRAME_RESTLER_CMD=restler
AUTOFRAME_DOCKER_CMD=docker
```

## Safety Model

AutoFrame prefers broad discovery with conservative runtime behavior:

- GET endpoints are called only when considered safe and concrete.
- Write endpoints need a request schema or source-derived request contract.
- 4xx responses from generated write payloads are treated as clean business rejection; 5xx responses are surfaced.
- Secrets and tokens should be supplied through environment variables, never committed.

## License

MIT. See [LICENSE](LICENSE).
