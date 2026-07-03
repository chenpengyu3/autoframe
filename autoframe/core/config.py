"""Configuration loader and dataclass models."""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass
class ServiceConfig:
    name: str = "my-app"
    base_url: str = ""  # REQUIRED: must be provided via --url or config
    type: str = "auto"
    health_endpoint: str = ""  # deprecated: auto-discovered by scanner
    project_path: Optional[str] = None


@dataclass
class AuthConfig:
    type: str = "none"
    token: Optional[str] = field(default=None, repr=False)
    username: Optional[str] = None
    password: Optional[str] = field(default=None, repr=False)
    token_url: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = field(default=None, repr=False)


@dataclass
class ThresholdConfig:
    max_response_time_ms: int = 2000
    max_error_rate_percent: float = 5.0
    min_throughput_rps: float = 10.0
    max_p99_latency_ms: int = 5000


@dataclass
class TestSuiteConfig:
    modules: list[str] = field(default_factory=lambda: [
        "api", "performance", "security", "database", "concurrency", "fault_tolerance"
    ])
    parallel: bool = False
    tags: list[str] = field(default_factory=list)
    exclude_tags: list[str] = field(default_factory=list)


@dataclass
class LoadTestConfig:
    users: int = 10
    spawn_rate: int = 5
    duration_seconds: int = 10


@dataclass
class StressTestConfig:
    stages: list[int] = field(default_factory=lambda: [5, 10, 20])
    step_duration_seconds: int = 5


@dataclass
class ResponseTimeConfig:
    sample_size: int = 20
    concurrency: int = 5


@dataclass
class PerformanceConfig:
    load_test: LoadTestConfig = field(default_factory=LoadTestConfig)
    stress_test: StressTestConfig = field(default_factory=StressTestConfig)
    response_time: ResponseTimeConfig = field(default_factory=ResponseTimeConfig)


@dataclass
class DatabaseConfig:
    type: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = field(default=None, repr=False)
    pool_size: int = 10


@dataclass
class SecurityConfig:
    check_headers: bool = True
    auth_bypass: bool = True


@dataclass
class ConcurrencyConfig:
    max_threads: int = 10
    requests_per_thread: int = 5


@dataclass
class FaultToleranceConfig:
    timeout_seconds: int = 10
    rapid_requests: int = 30
    recovery_wait_seconds: int = 3


@dataclass
class ReportConfig:
    output_dir: str = "reports/"
    format: str = "html"


@dataclass
class FrameworkConfig:
    environment: str = "dev"
    service: ServiceConfig = field(default_factory=ServiceConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    thresholds: ThresholdConfig = field(default_factory=ThresholdConfig)
    test_suite: TestSuiteConfig = field(default_factory=TestSuiteConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    concurrency: ConcurrencyConfig = field(default_factory=ConcurrencyConfig)
    fault_tolerance: FaultToleranceConfig = field(default_factory=FaultToleranceConfig)
    report: ReportConfig = field(default_factory=ReportConfig)


def _resolve_env_vars(value: Any) -> Any:
    if isinstance(value, str):
        pattern = re.compile(r"\$\{(\w+)\}")
        matches = pattern.findall(value)
        for var_name in matches:
            env_val = os.environ.get(var_name, "")
            value = value.replace(f"${{{var_name}}}", env_val)
        return value
    elif isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_env_vars(item) for item in value]
    return value


def _merge_dicts(base: dict, override: dict) -> dict:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def _dict_to_dataclass(cls, data: dict):
    if not isinstance(data, dict):
        return data
    field_types = {f.name: f.type for f in cls.__dataclass_fields__.values()}
    kwargs = {}
    for key, value in data.items():
        if key not in field_types:
            continue
        field_type = field_types[key]
        if hasattr(field_type, "__origin__"):
            kwargs[key] = value
        elif isinstance(value, dict) and hasattr(field_type, "__dataclass_fields__"):
            kwargs[key] = _dict_to_dataclass(field_type, value)
        else:
            kwargs[key] = value
    return cls(**kwargs)


def load_config(
    env: str = "dev",
    config_dir: str | Path = "config",
    cli_overrides: Optional[dict] = None,
) -> FrameworkConfig:
    config_dir = Path(config_dir)
    default_path = config_dir / "default.yaml"
    env_path = config_dir / f"{env}.yaml"

    raw: dict = {}
    if default_path.exists():
        with open(default_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            env_data = yaml.safe_load(f) or {}
        raw = _merge_dicts(raw, env_data)

    raw = _resolve_env_vars(raw)

    if cli_overrides:
        raw = _merge_dicts(raw, cli_overrides)

    service = _dict_to_dataclass(ServiceConfig, raw.get("service", {}))
    auth = _dict_to_dataclass(AuthConfig, raw.get("auth", {}))
    thresholds = _dict_to_dataclass(ThresholdConfig, raw.get("thresholds", {}))
    test_suite = _dict_to_dataclass(TestSuiteConfig, raw.get("test_suite", {}))

    perf_data = raw.get("performance", {})
    performance = PerformanceConfig(
        load_test=_dict_to_dataclass(LoadTestConfig, perf_data.get("load_test", {})),
        stress_test=_dict_to_dataclass(StressTestConfig, perf_data.get("stress_test", {})),
        response_time=_dict_to_dataclass(ResponseTimeConfig, perf_data.get("response_time", {})),
    )

    database = _dict_to_dataclass(DatabaseConfig, raw.get("database", {}))
    security = _dict_to_dataclass(SecurityConfig, raw.get("security", {}))
    concurrency = _dict_to_dataclass(ConcurrencyConfig, raw.get("concurrency", {}))
    fault_tolerance = _dict_to_dataclass(FaultToleranceConfig, raw.get("fault_tolerance", {}))
    report = _dict_to_dataclass(ReportConfig, raw.get("report", {}))

    return FrameworkConfig(
        environment=env,
        service=service,
        auth=auth,
        thresholds=thresholds,
        test_suite=test_suite,
        performance=performance,
        database=database,
        security=security,
        concurrency=concurrency,
        fault_tolerance=fault_tolerance,
        report=report,
    )
