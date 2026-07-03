"""Auto-detect database configuration from project source."""

import os
import re
from pathlib import Path
from typing import Optional

from autoframe.scanner.models import DiscoveredDatabase


def detect_database(project_path: Optional[str] = None) -> Optional[DiscoveredDatabase]:
    """Detect database configuration from project files."""
    env_url = os.environ.get("AUTOFRAME_DB_URL") or os.environ.get("DATABASE_URL")
    if env_url:
        db = _parse_url(_jdbc_to_python_url(env_url))
        if db:
            return db

    if not project_path:
        return None

    root = Path(project_path)
    if not root.exists():
        return None

    # Try Spring Boot first
    db = _detect_spring_boot_db(root)
    if db:
        return db

    # Try Python
    db = _detect_python_db(root)
    if db:
        return db

    return None


def _detect_spring_boot_db(root: Path) -> Optional[DiscoveredDatabase]:
    """Parse Spring Boot application.yml/properties for datasource config."""
    config_files = []

    # application.yml / application.properties
    for name in ["application.yml", "application.yaml", "application.properties"]:
        p = root / "src" / "main" / "resources" / name
        if p.exists():
            config_files.append(p)

    # application-*.yml (profiles)
    resources_dir = root / "src" / "main" / "resources"
    if resources_dir.exists():
        for f in resources_dir.glob("application-*.yml"):
            config_files.append(f)
        for f in resources_dir.glob("application-*.yaml"):
            config_files.append(f)

    for config_file in config_files:
        try:
            content = config_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        # Parse YAML-style config
        db_config = _parse_spring_datasource(content)
        if db_config:
            return db_config

        # Parse properties-style config
        db_config = _parse_spring_properties(content)
        if db_config:
            return db_config

    return None


def _parse_spring_datasource(content: str) -> Optional[DiscoveredDatabase]:
    """Parse spring.datasource from YAML content."""
    # Simple regex-based parsing (not full YAML to avoid dependency)
    url_match = re.search(
        r'(?:url|jdbc-url)\s*:\s*["\']?(jdbc:(\w+)://([^:/]+)(?::(\d+))?/(\w+))',
        content,
    )
    if url_match:
        jdbc_url = url_match.group(1)
        db_type = url_match.group(2)
        host = url_match.group(3)
        port = int(url_match.group(4)) if url_match.group(4) else _default_port(db_type)
        database = url_match.group(5)

        username_match = re.search(r'username\s*:\s*["\']?(\S+)', content)
        password_match = re.search(r'password\s*:\s*["\']?(\S+)', content)

        return DiscoveredDatabase(
            db_type=db_type,
            host=host,
            port=port,
            database=database,
            username=username_match.group(1) if username_match else None,
            password=password_match.group(1) if password_match else None,
            connection_url=jdbc_url,
        )

    return None


def _parse_spring_properties(content: str) -> Optional[DiscoveredDatabase]:
    """Parse spring.datasource from .properties content."""
    url_match = re.search(
        r'spring\.datasource\.(?:url|jdbc-url)\s*=\s*(jdbc:(\w+)://([^:/]+)(?::(\d+))?/(\w+))',
        content,
    )
    if url_match:
        jdbc_url = url_match.group(1)
        db_type = url_match.group(2)
        host = url_match.group(3)
        port = int(url_match.group(4)) if url_match.group(4) else _default_port(db_type)
        database = url_match.group(5)

        username_match = re.search(r'spring\.datasource\.username\s*=\s*(\S+)', content)
        password_match = re.search(r'spring\.datasource\.password\s*=\s*(\S+)', content)

        return DiscoveredDatabase(
            db_type=db_type,
            host=host,
            port=port,
            database=database,
            username=username_match.group(1) if username_match else None,
            password=password_match.group(1) if password_match else None,
            connection_url=jdbc_url,
        )

    return None


def _detect_python_db(root: Path) -> Optional[DiscoveredDatabase]:
    """Parse Python project for database configuration."""
    # Check .env file
    env_file = root / ".env"
    if env_file.exists():
        try:
            content = env_file.read_text(encoding="utf-8", errors="ignore")
            db = _parse_database_url(content)
            if db:
                return db
        except Exception:
            pass

    # Check settings.py (Django)
    for settings_file in root.rglob("settings.py"):
        try:
            content = settings_file.read_text(encoding="utf-8", errors="ignore")
            db = _parse_django_settings(content)
            if db:
                return db
        except Exception:
            continue

    # Check config.py / database.py
    for config_name in ["config.py", "database.py", "db.py", "app.py", "main.py"]:
        for config_file in root.rglob(config_name):
            try:
                content = config_file.read_text(encoding="utf-8", errors="ignore")
                db = _parse_sqlalchemy_url(content)
                if db:
                    return db
            except Exception:
                continue

    return None


def _parse_database_url(content: str) -> Optional[DiscoveredDatabase]:
    """Parse DATABASE_URL from env file."""
    match = re.search(
        r'(?:DATABASE_URL|DB_URL|SQLALCHEMY_DATABASE_URL)\s*=\s*["\']?(\S+)',
        content,
    )
    if match:
        url = match.group(1).strip('"\'')
        return _parse_url(url)
    return None


def _parse_sqlalchemy_url(content: str) -> Optional[DiscoveredDatabase]:
    """Parse SQLAlchemy database URL from Python source."""
    match = re.search(
        r'(?:SQLALCHEMY_DATABASE_URL|DATABASE_URL|db_url|database_url)\s*=\s*["\']([^"\']+)',
        content,
    )
    if match:
        url = match.group(1)
        return _parse_url(url)
    return None


def _parse_django_settings(content: str) -> Optional[DiscoveredDatabase]:
    """Parse Django DATABASES setting."""
    engine_match = re.search(r"'ENGINE'\s*:\s*'([^']+)'", content)
    name_match = re.search(r"'NAME'\s*:\s*'([^']+)'", content)
    host_match = re.search(r"'HOST'\s*:\s*'([^']+)'", content)
    port_match = re.search(r"'PORT'\s*:\s*'([^']+)'", content)
    user_match = re.search(r"'USER'\s*:\s*'([^']+)'", content)
    pass_match = re.search(r"'PASSWORD'\s*:\s*'([^']+)'", content)

    if engine_match and name_match:
        engine = engine_match.group(1)
        db_type = "unknown"
        if "mysql" in engine:
            db_type = "mysql"
        elif "postgresql" in engine:
            db_type = "postgresql"
        elif "sqlite" in engine:
            db_type = "sqlite"

        return DiscoveredDatabase(
            db_type=db_type,
            host=host_match.group(1) if host_match else "localhost",
            port=int(port_match.group(1)) if port_match else None,
            database=name_match.group(1),
            username=user_match.group(1) if user_match else None,
            password=pass_match.group(1) if pass_match else None,
        )

    return None


def _parse_url(url: str) -> Optional[DiscoveredDatabase]:
    """Parse a database connection URL."""
    # mysql+pymysql://user:pass@host:port/db
    # postgresql://user:pass@host:port/db
    # sqlite:///path/to/db
    match = re.match(
        r'(\w+)(?:\+\w+)?://(?:(\w+)(?::(\S+))?@)?([^:/]+)(?::(\d+))?/(\S+)',
        url,
    )
    if match:
        return DiscoveredDatabase(
            db_type=match.group(1),
            host=match.group(4),
            port=int(match.group(5)) if match.group(5) else None,
            database=match.group(6),
            username=match.group(2),
            password=match.group(3),
            connection_url=url,
        )

    # sqlite:///path
    sqlite_match = re.match(r'sqlite:///(\S+)', url)
    if sqlite_match:
        return DiscoveredDatabase(
            db_type="sqlite",
            database=sqlite_match.group(1),
            connection_url=url,
        )

    return None


def _jdbc_to_python_url(jdbc_url: str) -> str:
    """Convert JDBC URLs to SQLAlchemy-style URLs."""
    base_url = jdbc_url.split("?")[0]
    match = re.match(r"jdbc:(\w+)://(.+)", base_url)
    if not match:
        return jdbc_url

    db_type = match.group(1)
    rest = match.group(2)
    if db_type == "mysql":
        return f"mysql+pymysql://{rest}"
    if db_type == "postgresql":
        return f"postgresql://{rest}"
    if db_type == "sqlserver":
        return f"mssql+pyodbc://{rest}"
    if db_type == "oracle":
        return f"oracle+cx_oracle://{rest}"
    return f"{db_type}://{rest}"


def _default_port(db_type: str) -> int:
    ports = {"mysql": 3306, "postgresql": 5432, "mssql": 1433, "oracle": 1521}
    return ports.get(db_type, 3306)
