# AutoFrame v2.0 - Auto-Adaptive Testing Framework Implementation Plan

## Executive Summary

Transform AutoFrame from a hardcoded-endpoint testing tool into a fully auto-adaptive framework that scans any Spring Boot or Python project, auto-discovers API endpoints, auto-detects database/auth configuration, and auto-generates comprehensive test suites.

---

## 1. Complete File Structure

```
normaltest/
├── pyproject.toml                          # Package config, dependencies, entry points
├── requirements.txt                        # Pinned dependencies
├── pytest.ini                              # Pytest configuration with markers
├── README.md                               # Usage documentation
├── start.bat                               # Quick-start script for Windows
│
├── config/                                 # Default config templates
│   ├── default.yaml                        # Default framework config
│   └── security_payloads.yaml              # SQL injection, XSS, path traversal payloads
│
├── autoframe/                              # Main package
│   ├── __init__.py                         # Package init, version
│   ├── __main__.py                         # python -m autoframe entry
│   ├── cli.py                              # Typer CLI: scan, run, report commands
│   ├── conftest.py                         # Root pytest fixtures (discovered data)
│   │
│   ├── scanner/                            # *** NEW: Auto-discovery engine ***
│   │   ├── __init__.py
│   │   ├── models.py                       # DiscoveredEndpoint, DiscoveredResource, etc.
│   │   ├── project_detector.py             # Detect project type (Spring Boot/Python)
│   │   ├── openapi_fetcher.py              # Fetch and parse OpenAPI/Swagger specs
│   │   ├── source_parser.py                # Parse source code for route annotations
│   │   ├── endpoint_enricher.py            # Probe endpoints, detect auth, infer params
│   │   ├── resource_detector.py            # Group endpoints into CRUD resources
│   │   ├── db_detector.py                  # Auto-detect database configuration
│   │   ├── auth_detector.py                # Auto-detect authentication mechanism
│   │   ├── data_generator.py               # Schema-aware test data generation
│   │   └── pipeline.py                     # Orchestrates the full scan pipeline
│   │
│   ├── generator/                          # *** NEW: Test case generation ***
│   │   ├── __init__.py
│   │   ├── api_test_gen.py                 # Generate API functional test params
│   │   ├── crud_test_gen.py                # Generate CRUD lifecycle test params
│   │   ├── security_test_gen.py            # Generate security test params
│   │   ├── concurrency_test_gen.py         # Generate concurrency test params
│   │   ├── db_test_gen.py                  # Generate database test params
│   │   └── fault_test_gen.py               # Generate fault tolerance test params
│   │
│   ├── core/                               # Core framework (evolved from AutoFrame v0.1)
│   │   ├── __init__.py
│   │   ├── config.py                       # Config loader with auto-discovered data support
│   │   ├── context.py                      # TestContext with discovered project data
│   │   ├── client.py                       # HttpClient with metrics (reuse pattern)
│   │   └── logging.py                      # Rich-based structured logging (reuse)
│   │
│   ├── plugins/                            # Plugin system (reuse pattern)
│   │   ├── __init__.py
│   │   ├── base.py                         # TestModule ABC
│   │   └── registry.py                     # Plugin discovery and registration
│   │
│   ├── modules/                            # Test modules (adapted for auto-discovery)
│   │   ├── __init__.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── plugin.py
│   │   │   ├── conftest.py
│   │   │   ├── test_endpoints.py           # Parametrized over discovered endpoints
│   │   │   ├── test_crud.py                # Parametrized over discovered resources
│   │   │   └── test_schemas.py             # Schema validation using discovered schemas
│   │   ├── security/
│   │   │   ├── __init__.py
│   │   │   ├── plugin.py
│   │   │   ├── conftest.py
│   │   │   ├── test_sql_injection.py
│   │   │   ├── test_xss.py
│   │   │   ├── test_auth_bypass.py
│   │   │   └── test_headers.py
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── plugin.py
│   │   │   ├── conftest.py                 # Uses auto-detected DB config
│   │   │   ├── test_connections.py
│   │   │   ├── test_integrity.py           # Auto-discovers tables
│   │   │   └── test_queries.py
│   │   ├── concurrency/
│   │   │   ├── __init__.py
│   │   │   ├── plugin.py
│   │   │   ├── conftest.py
│   │   │   ├── test_concurrent_requests.py
│   │   │   ├── test_race_conditions.py
│   │   │   └── test_thread_safety.py
│   │   ├── fault_tolerance/
│   │   │   ├── __init__.py
│   │   │   ├── plugin.py
│   │   │   ├── conftest.py
│   │   │   ├── test_degradation.py
│   │   │   ├── test_recovery.py
│   │   │   └── test_timeouts.py
│   │   └── performance/
│   │       ├── __init__.py
│   │       ├── plugin.py
│   │       ├── conftest.py
│   │       ├── collector.py                # Metrics collector (reuse)
│   │       ├── test_load.py
│   │       ├── test_stress.py
│   │       ├── test_response_time.py
│   │       └── test_throughput.py
│   │
│   ├── reporting/                          # Report generation (reuse + enhance)
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── collector.py
│   │   ├── generator.py
│   │   ├── plugin.py
│   │   └── templates/
│   │       └── report.html
│   │
│   └── utils/
│       ├── __init__.py
│       ├── data_generator.py
│       ├── metrics.py
│       ├── retry.py
│       └── service_detector.py
│
├── generated/                              # Auto-generated scan results (gitignored)
│   └── .gitkeep
│
└── reports/                                # Generated HTML reports (gitignored)
    └── .gitkeep
```

---

## 2. Key Classes and Their Responsibilities

### 2.1 Scanner Models (scanner/models.py)

These dataclasses are the central data contract between the scanner and test modules.

**EndpointParam** - A single parameter for an endpoint.
- name: str (e.g., "userId")
- location: str ("path", "query", "header", "body")
- type: str ("string", "integer", "boolean", "array", "object")
- required: bool
- example: Any (auto-generated)

**DiscoveredEndpoint** - A single API endpoint discovered by the scanner.
- path: str (e.g., "/api/users/{id}")
- methods: list[str] (["GET", "PUT", "DELETE"])
- parameters: list[EndpointParam]
- request_body_schema: Optional[dict] (JSON Schema)
- response_schema: Optional[dict] (JSON Schema)
- auth_required: Optional[bool] (None=unknown, True/False)
- tags: list[str]
- source: str ("openapi", "source_code", "crawling")
- summary: str
- operation_id: str

**DiscoveredResource** - A CRUD resource inferred from endpoint patterns.
- name: str (e.g., "user")
- base_path: str (e.g., "/api/users")
- create: Optional[DiscoveredEndpoint]
- read_one: Optional[DiscoveredEndpoint]
- read_all: Optional[DiscoveredEndpoint]
- update: Optional[DiscoveredEndpoint]
- delete: Optional[DiscoveredEndpoint]
- id_field: str ("id")
- create_body: dict (auto-generated from schema)
- update_body: dict (auto-generated from schema)

**DiscoveredAuth** - Auto-detected authentication configuration.
- type: str ("none", "bearer", "basic", "oauth2", "api_key")
- login_endpoint: Optional[str]
- login_method: str ("POST")
- login_body: dict (auto-detected)
- token_field: str ("token")
- header_name: str ("Authorization")
- header_format: str ("Bearer {token}")
- token: Optional[str] (acquired after login)
- detected_indicators: list[str]

**TableInfo** - Database table metadata.
- name: str
- columns: list[dict]
- foreign_keys: list[dict]

**DiscoveredDatabase** - Auto-detected database configuration.
- type: str ("mysql", "postgresql", "sqlite", "mongodb")
- host, port, database, username, password, pool_size
- tables: list[TableInfo]
- detected_from: str

**DiscoveredProject** - Complete scan result.
- project_type: str ("spring_boot", "fastapi", "flask", "django")
- base_url: str
- endpoints: list[DiscoveredEndpoint]
- resources: list[DiscoveredResource]
- auth: DiscoveredAuth
- database: Optional[DiscoveredDatabase]
- health_endpoint: str
- scan_duration_ms: float
- scan_source: str
- warnings: list[str]

### 2.2 Scanner Components

**ProjectDetector** - Detect project type from filesystem or running service.
- detect_from_source(project_path): Check pom.xml, build.gradle, requirements.txt, pyproject.toml, manage.py
- detect_from_service(base_url): Probe /actuator/health, /openapi.json, response headers
- detect(project_path, base_url): Combine both

**OpenAPIFetcher** - Fetch and parse OpenAPI/Swagger specs.
- fetch(base_url): Try /v3/api-docs, /v2/api-docs, /openapi.json, /swagger.json, /api-docs
- parse_spec(spec): Convert OpenAPI paths to DiscoveredEndpoint list
- extract_resources(endpoints): Group endpoints into CRUD resources

**SourceParser** - Parse source code for routes (fallback when no OpenAPI).
Two sub-parsers:
- SpringBootSourceParser: Regex for @RestController, @RequestMapping, @GetMapping, etc.
- PythonSourceParser: Regex/AST for @app.route, @router.get, @api_view, urlpatterns

**EndpointEnricher** - Validate discovered endpoints by probing the running service.
- For each endpoint: send HEAD/GET, check status (200=exists, 401=auth needed, 404=remove)
- Mark auth_required based on 401 responses
- Remove false positives from source parsing

**ResourceDetector** - Group endpoints into CRUD resources.
- Extract base paths by removing trailing /{id} patterns
- Group endpoints sharing the same base path
- Identify: POST=CREATE, GET base=LIST, GET /{id}=READ, PUT/PATCH /{id}=UPDATE, DELETE /{id}=DELETE
- A resource needs at least CREATE + one other operation
- Infer id_field from response schema

**DatabaseDetector** - Auto-detect database config from source files.
- Spring Boot: Parse application.yml/properties for spring.datasource.*
- Python: Parse .env (DATABASE_URL), settings.py (DATABASES), SQLAlchemy create_engine()
- Service: Try /actuator/env, /actuator/health for DB details

**AuthDetector** - Auto-detect authentication mechanism.
- Check OpenAPI security schemes
- Check source code (Spring Security config, JWT libraries)
- Probe common login endpoints (/auth/login, /api/login, /token, /oauth/token)
- Try POST with common credentials, extract token from response
- Check 401 responses on endpoints

**SchemaDataGenerator** - Generate realistic test data from JSON schemas.
- Field name pattern matching: "email"->random email, "name"->random name, etc.
- Type-based fallback: string->random alphanumeric, integer->random int, etc.
- Recursive handling for nested objects and arrays

**ScanPipeline** - Orchestrates the entire scan process.
1. ProjectDetector.detect() -> project_type
2. OpenAPIFetcher.fetch() -> spec (if available)
3. If spec: parse_spec() -> endpoints; else: SourceParser.parse() -> endpoints
4. EndpointEnricher.enrich() -> validated endpoints
5. ResourceDetector.detect() -> CRUD resources
6. AuthDetector.detect() -> auth config
7. DatabaseDetector.detect() -> db config
8. Build DiscoveredProject, save to YAML

### 2.3 Generator Components

Each generator produces parametrized test data that test modules consume.

**ApiTestGenerator**: Takes discovered endpoints, produces test parameters for endpoint reachability, response time, schema validation.

**CrudTestGenerator**: Takes discovered resources, produces CRUD lifecycle test parameters with auto-generated bodies.

**SecurityTestGenerator**: Takes discovered endpoints + security payloads, produces injection/bypass test parameters.

**ConcurrencyTestGenerator**: Takes discovered endpoints + resources, selects targets for concurrent tests.

**DbTestGenerator**: Takes discovered database, produces connection/integrity/query test parameters.

**FaultTestGenerator**: Takes discovered endpoints, selects targets for timeout/degradation/recovery tests.

### 2.4 Core Components (Evolved)

**config.py** - Extended with:
- ScanConfig dataclass (project_path, base_url, scan_source, cache_ttl)
- load_config() supports loading from discovered_config.yaml
- Auto-populates endpoints, resources, auth, database from discovered data

**context.py** - Extended TestContext:
- discovered: Optional[DiscoveredProject]
- endpoints: list[DiscoveredEndpoint] (convenience)
- resources: list[DiscoveredResource] (convenience)
- load_discovered(config_path) method

**conftest.py** - Root fixtures:
- discovered_project: Loads scan results or runs live scan
- discovered_endpoints: From discovered_project
- discovered_resources: From discovered_project
- discovered_auth: From discovered_project
- discovered_db: From discovered_project

---

## 3. Auto-Detection Algorithms

### 3.1 Project Type Detection

```
FILESYSTEM:
  pom.xml with "spring-boot" -> spring_boot
  build.gradle with "spring-boot" -> spring_boot
  manage.py + settings.py -> django
  requirements.txt with "fastapi" -> fastapi
  requirements.txt with "flask" -> flask
  pyproject.toml with "fastapi" -> fastapi

SERVICE (runtime probing):
  GET /actuator/health returns 200 with "status" -> spring_boot
  GET /openapi.json returns 200 with "openapi" -> fastapi
  GET /swagger.json returns 200 -> flask
  Server header contains "uvicorn" -> fastapi
  Server header contains "gunicorn" -> flask
```

### 3.2 OpenAPI Spec Discovery

```
Priority order:
  /v3/api-docs          (Spring Boot OpenAPI 3)
  /v2/api-docs          (Spring Boot Swagger 2)
  /openapi.json         (FastAPI)
  /swagger.json         (Flask-RESTX)
  /api-docs             (Generic)
  /swagger/v1/swagger.json

For each URL: GET, check status 200, verify "openapi" or "swagger" in response.
```

### 3.3 CRUD Resource Detection

```
1. Extract base paths by removing trailing /{id} segments
2. Group endpoints by base path
3. For each group, identify CRUD operations:
   POST to base = CREATE
   GET to base = LIST
   GET to base/{id} = READ
   PUT/PATCH to base/{id} = UPDATE
   DELETE to base/{id} = DELETE
4. Resource = group with at least CREATE + one read operation
5. Infer id_field from response schema (look for "id", "Id", "{name}Id")
6. Auto-generate test bodies from request_body_schema
```

### 3.4 Database Auto-Detection

```
Spring Boot:
  Parse application.yml -> spring.datasource.url, .username, .password
  Parse application.properties -> same
  Parse pom.xml for driver dependencies

Python:
  Parse .env -> DATABASE_URL, DB_HOST, DB_PORT, etc.
  Parse settings.py -> DATABASES config
  Parse source for create_engine() calls
  Parse requirements.txt for DB drivers

Runtime:
  GET /actuator/env -> spring.datasource properties
  GET /actuator/health -> DB health check details
```

### 3.5 Auth Auto-Detection

```
Phase 1: OpenAPI security schemes
Phase 2: Source code (Spring Security config, JWT libraries)
Phase 3: Probe login endpoints:
  POST /api/auth/login, /auth/login, /api/login, /login, /token, /oauth/token
  Try {"username":"test","password":"test"}, {"email":"test","password":"test"}
  Extract token from response (token, access_token, accessToken, jwt fields)
Phase 4: Check 401 responses on protected endpoints
```

---

## 4. Configuration Flow

```
User runs: python -m autoframe run --project /path/to/app

Step 1: CLI parses arguments
Step 2: ScanPipeline.scan() executes
  -> project_type, endpoints, resources, auth, database
  -> saves to generated/discovered_config.yaml
Step 3: Config loader merges default.yaml + discovered_config.yaml + CLI overrides
Step 4: TestContext initializes with discovered data
Step 5: Test modules run, consuming discovered data via fixtures
Step 6: HTML report generated
```

---

## 5. CLI Commands

```bash
# Scan only
python -m autoframe scan /path/to/project
python -m autoframe scan --url http://localhost:8080

# Full auto test
python -m autoframe run --project /path/to/project
python -m autoframe run --url http://localhost:8080
python -m autoframe run --config generated/discovered_config.yaml
python -m autoframe run --url http://localhost:8080 --modules api,security

# Report generation
python -m autoframe report --input results.json

# List modules
python -m autoframe list-modules
```

---

## 6. Test Module Adaptations

All test modules change from reading hardcoded api_endpoints.yaml to consuming auto-discovered data via fixtures (discovered_endpoints, discovered_resources, discovered_auth, discovered_db).

- API tests: parametrize over discovered endpoints, use auto-generated CRUD bodies
- Security tests: iterate discovered endpoints for injection/bypass testing
- Database tests: use auto-detected DB config and table metadata
- Concurrency tests: pick discovered endpoints/resources for concurrent testing
- Fault tolerance tests: use discovered endpoints for stress/recovery
- Performance tests: use discovered endpoints for load testing

---

## 7. Implementation Sequence

### Phase 1: Foundation (8 files)
pyproject.toml, requirements.txt, pytest.ini, config/, core/ modules

### Phase 2: Scanner (10 files)
models.py, project_detector.py, openapi_fetcher.py, source_parser.py,
endpoint_enricher.py, resource_detector.py, db_detector.py, auth_detector.py,
data_generator.py, pipeline.py

### Phase 3: Generator (6 files)
api_test_gen.py, crud_test_gen.py, security_test_gen.py,
concurrency_test_gen.py, db_test_gen.py, fault_test_gen.py

### Phase 4: Test Modules (35 files)
6 modules x (plugin + conftest + 2-4 test files)

### Phase 5: Reporting & CLI (7 files)
models.py, collector.py, generator.py, template, plugin.py, cli.py, conftest.py

### Phase 6: Utils & Integration (5 files)
data_generator.py, metrics.py, retry.py, service_detector.py, plugins/

---

## 8. Key Dependencies

httpx, pytest, PyYAML, Jinja2, typer, rich, jsonschema, SQLAlchemy, pymysql,
psycopg2-binary, pydantic

---

## 9. Potential Challenges

| Challenge | Mitigation |
|-----------|------------|
| No OpenAPI spec | Source code parsing -> brute-force crawling |
| Source parsing unreliable | Regex + AST hybrid; validate by probing |
| Auth detection fails | Manual config via CLI args |
| DB detection fails | Skip database tests gracefully |
| Path params unresolved | Auto-generated placeholder values |
| Large API surface | --modules flag to limit scope |
| Service not running | Source-only mode, skip enrichment |
