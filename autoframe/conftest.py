"""Shared pytest fixtures - bridges scanner data into test modules."""

import os
import pytest
from pathlib import Path

from autoframe.core.config import load_config, FrameworkConfig
from autoframe.core.context import TestContext
from autoframe.core.client import HttpClient, metrics as global_metrics
from autoframe.core import logging
from autoframe.scanner.pipeline import ScanPipeline
from autoframe.scanner.models import DiscoveredProject
from autoframe.generator.api_gen import ApiTestGenerator
from autoframe.generator.crud_gen import CrudTestGenerator
from autoframe.generator.security_gen import SecurityTestGenerator
from autoframe.generator.concurrency_gen import ConcurrencyTestGenerator
from autoframe.generator.database_gen import DatabaseTestGenerator
from autoframe.generator.fault_gen import FaultTestGenerator


@pytest.fixture(scope="session")
def config():
    """Load framework configuration with CLI overrides from environment."""
    cli_overrides = {}
    base_url = os.environ.get("AUTOFRAME_BASE_URL")
    project_path = os.environ.get("AUTOFRAME_PROJECT_PATH")
    if base_url:
        cli_overrides["service"] = {"base_url": base_url}
    if project_path:
        cli_overrides.setdefault("service", {})["project_path"] = project_path
    cfg = load_config(cli_overrides=cli_overrides if cli_overrides else None)
    if not cfg.service.base_url or cfg.service.base_url == "${AUTOFRAME_BASE_URL}":
        pytest.fail(
            "鏈彁渚涚洰鏍囧湴鍧€銆傝浣跨敤 --url 鍙傛暟鎴栬缃?AUTOFRAME_BASE_URL 鐜鍙橀噺銆俓n"
            "  绀轰緥: python -m autoframe run --url http://浣犵殑鏈嶅姟鍦板潃:绔彛"
        )
    return cfg


@pytest.fixture(scope="session")
def context(config):
    """Create test context."""
    ctx = TestContext(config)
    ctx.detect_service_type()
    return ctx


@pytest.fixture(scope="session")
def client(context, discovered_auth):
    """Provide the HTTP client, configured with discovered auth."""
    c = context.client
    logging.info(f"client fixture: auth token configured={bool(discovered_auth.token)}")
    logging.info(f"client fixture: discovered_auth.acquisition_failed={discovered_auth.acquisition_failed}")

    if discovered_auth.acquisition_failed:
        logging.warning(f"Auth endpoint discovered ({discovered_auth.login_endpoint}) but token acquisition failed; auth-required tests may be skipped.")
    if discovered_auth.token:
        c.auth.token = discovered_auth.token
        c.auth.type = discovered_auth.auth_type
        logging.success(f"Configured client auth: {discovered_auth.auth_type}, token=<redacted>")
    else:
        logging.warning("Client auth token is not configured")

    return c


@pytest.fixture(scope="session")
def metrics_collector():
    """Provide the global metrics collector."""
    return global_metrics


@pytest.fixture(scope="session")
def discovered_project(config, context) -> DiscoveredProject:
    """Run the scanner pipeline, return DiscoveredProject."""
    project_path = config.service.project_path
    pipeline = ScanPipeline(
        base_url=config.service.base_url,
        project_path=project_path,
        project_type=context.service_type,
    )
    project = pipeline.run()

    # 浠庣幆澧冨彉閲忚鍙?CLI 闃舵鑾峰彇鐨?token
    auth_token = os.environ.get("AUTOFRAME_AUTH_TOKEN")
    logging.info(f"Environment AUTOFRAME_AUTH_TOKEN configured={bool(auth_token)}")
    logging.info(f"Auth state: acquisition_failed={project.auth.acquisition_failed}, token_configured={bool(project.auth.token)}")

    if auth_token:
        project.auth.token = auth_token
        project.auth.auth_type = "bearer"
        project.auth.acquisition_failed = False
        logging.success("Loaded auth token from environment: <redacted>")

    # 浠庣幆澧冨彉閲忚鍙栨暟鎹簱閰嶇疆
    db_url = os.environ.get("AUTOFRAME_DB_URL")
    logging.info(f"Environment AUTOFRAME_DB_URL configured={bool(db_url)}")

    if db_url and not project.database:
        from autoframe.scanner.database_detector import _parse_url
        # 杞崲 JDBC URL 涓?Python 鏍煎紡
        python_url = _jdbc_to_python_url(db_url)
        db = _parse_url(python_url)
        if db:
            project.database = db
            logging.success(f"宸蹭粠鐜鍙橀噺鍔犺浇鏁版嵁搴撻厤缃? {db.db_type} @ {db.host}:{db.port}/{db.database}")
        else:
            logging.warning("鏁版嵁搴?URL 瑙ｆ瀽澶辫触")

    return project


@pytest.fixture(scope="session")
def discovered_endpoints(discovered_project):
    """Auto-discovered API endpoints."""
    return discovered_project.endpoints


@pytest.fixture(scope="session")
def discovered_resources(discovered_project):
    """Auto-discovered CRUD resources."""
    return discovered_project.resources


@pytest.fixture(scope="session")
def discovered_auth(discovered_project):
    """Auto-discovered auth configuration."""
    auth = discovered_project.auth
    logging.info(f"discovered_auth fixture: token_configured={bool(auth.token)}, type={auth.auth_type}, acquisition_failed={auth.acquisition_failed}")
    return auth


@pytest.fixture(scope="session")
def security_payloads():
    """Built-in security test payloads."""
    from autoframe.scanner.schema_data_generator import SECURITY_PAYLOADS
    return SECURITY_PAYLOADS


@pytest.fixture(scope="session")
def api_test_params(discovered_project):
    """Generate API test parameters from discovered project."""
    gen = ApiTestGenerator(discovered_project)
    return gen.generate()


@pytest.fixture(scope="session")
def crud_test_params(discovered_project):
    """Generate CRUD test parameters from discovered project."""
    gen = CrudTestGenerator(discovered_project)
    return gen.generate()


@pytest.fixture(scope="session")
def security_test_params(discovered_project):
    """Generate security test parameters from discovered project."""
    gen = SecurityTestGenerator(discovered_project)
    return gen.generate()


@pytest.fixture(scope="session")
def concurrency_test_params(discovered_project, config):
    """Generate concurrency test parameters from discovered project."""
    gen = ConcurrencyTestGenerator(discovered_project, max_threads=config.concurrency.max_threads)
    return gen.generate()


@pytest.fixture(scope="session")
def db_test_params(discovered_project):
    """Generate database test parameters from discovered project."""
    gen = DatabaseTestGenerator(discovered_project)
    return gen.generate()


@pytest.fixture(scope="session")
def fault_test_params(discovered_project, config):
    """Generate fault tolerance test parameters from discovered project."""
    gen = FaultTestGenerator(
        discovered_project,
        timeout_seconds=config.fault_tolerance.timeout_seconds,
        rapid_requests=config.fault_tolerance.rapid_requests,
        recovery_wait_seconds=config.fault_tolerance.recovery_wait_seconds,
    )
    return gen.generate()


def _jdbc_to_python_url(jdbc_url: str) -> str:
    """Convert JDBC URL to Python database URL format.

    jdbc:mysql://host:port/db -> mysql+pymysql://host:port/db
    jdbc:postgresql://host:port/db -> postgresql://host:port/db
    """
    import re

    # 绉婚櫎鏌ヨ鍙傛暟
    base_url = jdbc_url.split("?")[0]

    # jdbc:mysql://host:port/db -> mysql+pymysql://host:port/db
    match = re.match(r'jdbc:(\w+)://(.+)', base_url)
    if match:
        db_type = match.group(1)
        rest = match.group(2)

        if db_type == "mysql":
            return f"mysql+pymysql://{rest}"
        elif db_type == "postgresql":
            return f"postgresql://{rest}"
        elif db_type == "sqlserver":
            return f"mssql+pyodbc://{rest}"
        elif db_type == "oracle":
            return f"oracle+cx_oracle://{rest}"
        else:
            return f"{db_type}://{rest}"

    return jdbc_url
