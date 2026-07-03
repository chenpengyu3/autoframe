"""Dynamic pytest case generation for live database schema inventory."""

import os
import re

import pytest

from autoframe.scanner.database_detector import detect_database


_SCHEMA_CACHE = None


def _db_url(db) -> str | None:
    if not db:
        return None
    if db.connection_url:
        url = db.connection_url
        if url.startswith("jdbc:"):
            if db.db_type == "mysql":
                return f"mysql+pymysql://{db.username}:{db.password}@{db.host}:{db.port}/{db.database}"
            if db.db_type == "postgresql":
                return f"postgresql://{db.username}:{db.password}@{db.host}:{db.port}/{db.database}"
        return url
    if db.db_type == "mysql":
        return f"mysql+pymysql://{db.username}:{db.password}@{db.host}:{db.port}/{db.database}"
    if db.db_type == "postgresql":
        return f"postgresql://{db.username}:{db.password}@{db.host}:{db.port}/{db.database}"
    if db.db_type == "sqlite":
        return f"sqlite:///{db.database}"
    return None


def _schema():
    global _SCHEMA_CACHE
    if _SCHEMA_CACHE is not None:
        return _SCHEMA_CACHE

    project_path = os.environ.get("AUTOFRAME_PROJECT_PATH")
    db = detect_database(project_path)
    url = _db_url(db)
    if not url:
        _SCHEMA_CACHE = {}
        return _SCHEMA_CACHE

    try:
        from sqlalchemy import create_engine, inspect

        engine = create_engine(url, pool_pre_ping=True)
        inspector = inspect(engine)
        tables = []
        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            primary_key = inspector.get_pk_constraint(table_name) or {}
            foreign_keys = inspector.get_foreign_keys(table_name) or []
            indexes = inspector.get_indexes(table_name) or []
            unique_constraints = inspector.get_unique_constraints(table_name) or []
            tables.append(
                {
                    "name": table_name,
                    "columns": columns,
                    "primary_key": primary_key,
                    "foreign_keys": foreign_keys,
                    "indexes": indexes,
                    "unique_constraints": unique_constraints,
                }
            )
        engine.dispose()
    except Exception:
        _SCHEMA_CACHE = {}
        return _SCHEMA_CACHE

    table_names = {table["name"] for table in tables}
    _SCHEMA_CACHE = {"tables": tables, "table_names": table_names}
    return _SCHEMA_CACHE


def _table_cases():
    return _schema().get("tables", [])


def _column_cases():
    cases = []
    for table in _table_cases():
        for column in table.get("columns", []):
            cases.append({"table": table, "column": column})
    return cases


def _primary_key_cases():
    cases = []
    for table in _table_cases():
        for column_name in table.get("primary_key", {}).get("constrained_columns", []) or []:
            cases.append({"table": table, "column_name": column_name, "primary_key": table.get("primary_key", {})})
    return cases


def _foreign_key_cases():
    cases = []
    for table in _table_cases():
        for foreign_key in table.get("foreign_keys", []):
            cases.append({"table": table, "foreign_key": foreign_key})
    return cases


def _index_cases():
    cases = []
    for table in _table_cases():
        for index in table.get("indexes", []):
            cases.append({"table": table, "index": index})
    return cases


def _unique_constraint_cases():
    cases = []
    for table in _table_cases():
        for constraint in table.get("unique_constraints", []):
            cases.append({"table": table, "constraint": constraint})
    return cases


def _typed_column_cases(type_tokens: tuple[str, ...]):
    cases = []
    for case in _column_cases():
        column_type = str(case["column"].get("type", "")).lower()
        if any(token in column_type for token in type_tokens):
            cases.append(case)
    return cases


def _case_id(value) -> str:
    if value is None:
        return "unavailable"
    if isinstance(value, dict):
        table = value.get("table", value)
        table_name = table.get("name", "table") if isinstance(table, dict) else "table"
        column = value.get("column", {})
        pieces = [
            table_name,
            column.get("name", ""),
            value.get("column_name", ""),
            value.get("index", {}).get("name", ""),
            value.get("constraint", {}).get("name", ""),
            value.get("foreign_key", {}).get("name", ""),
        ]
        return re.sub(r"[^A-Za-z0-9_.-]+", "_", "_".join(str(piece) for piece in pieces if piece))[:180]
    return str(value)


def _parametrize_or_skip(metafunc, fixture_name: str, values: list, reason: str):
    if values:
        metafunc.parametrize(fixture_name, values, ids=[_case_id(value) for value in values])
    else:
        metafunc.parametrize(fixture_name, [pytest.param(None, marks=pytest.mark.skip(reason=reason))])


def pytest_generate_tests(metafunc):
    if "db_table_case" in metafunc.fixturenames:
        _parametrize_or_skip(metafunc, "db_table_case", _table_cases(), "No database tables discovered")

    if "db_column_case" in metafunc.fixturenames:
        _parametrize_or_skip(metafunc, "db_column_case", _column_cases(), "No database columns discovered")

    if "db_primary_key_case" in metafunc.fixturenames:
        _parametrize_or_skip(metafunc, "db_primary_key_case", _primary_key_cases(), "No primary key columns discovered")

    if "db_foreign_key_case" in metafunc.fixturenames:
        _parametrize_or_skip(metafunc, "db_foreign_key_case", _foreign_key_cases(), "No foreign key constraints discovered")

    if "db_index_case" in metafunc.fixturenames:
        _parametrize_or_skip(metafunc, "db_index_case", _index_cases(), "No database indexes discovered")

    if "db_unique_constraint_case" in metafunc.fixturenames:
        _parametrize_or_skip(metafunc, "db_unique_constraint_case", _unique_constraint_cases(), "No unique constraints discovered")

    if "db_string_column_case" in metafunc.fixturenames:
        _parametrize_or_skip(
            metafunc,
            "db_string_column_case",
            _typed_column_cases(("char", "text", "string", "varchar")),
            "No string-like database columns discovered",
        )

    if "db_numeric_column_case" in metafunc.fixturenames:
        _parametrize_or_skip(
            metafunc,
            "db_numeric_column_case",
            _typed_column_cases(("int", "number", "decimal", "numeric", "float", "double")),
            "No numeric database columns discovered",
        )

    if "db_temporal_column_case" in metafunc.fixturenames:
        _parametrize_or_skip(
            metafunc,
            "db_temporal_column_case",
            _typed_column_cases(("date", "time", "timestamp")),
            "No temporal database columns discovered",
        )
