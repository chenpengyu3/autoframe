"""Database schema quality checks."""

import pytest


def _schema_tables(db_engine, db_test_params):
    db_config = db_test_params.get("db_config")
    if not db_config:
        pytest.skip("No database configuration discovered")

    configured_tables = db_config.get("tables") or []
    if any(table.get("columns") for table in configured_tables):
        return configured_tables

    from sqlalchemy import inspect

    inspector = inspect(db_engine)
    table_names = inspector.get_table_names()
    if not table_names:
        pytest.skip("No database tables discovered")

    tables = []
    for table_name in table_names:
        columns = inspector.get_columns(table_name)
        primary_key = inspector.get_pk_constraint(table_name)
        tables.append(
            {
                "name": table_name,
                "columns": columns,
                "primary_key": primary_key.get("constrained_columns", []),
            }
        )
    return tables


@pytest.mark.database
class TestSchemaQuality:
    def test_tables_have_columns(self, db_engine, db_test_params):
        tables = _schema_tables(db_engine, db_test_params)
        failures = [
            table.get("name", "<unknown>")
            for table in tables
            if not table.get("columns")
        ]
        assert not failures, "Tables without discovered columns:\n" + "\n".join(failures)

    def test_tables_have_reasonable_column_names(self, db_engine, db_test_params):
        tables = _schema_tables(db_engine, db_test_params)
        failures = []
        for table in tables:
            for column in table.get("columns", []):
                name = str(column.get("name", ""))
                if not name or " " in name:
                    failures.append(f"{table.get('name')}.{name}: malformed column name")

        assert not failures, "Malformed column names:\n" + "\n".join(failures[:20])

    def test_large_tables_have_primary_keys(self, db_engine, db_test_params):
        tables = _schema_tables(db_engine, db_test_params)
        failures = []
        for table in tables:
            columns = table.get("columns", [])
            if len(columns) >= 3 and not table.get("primary_key"):
                failures.append(table.get("name", "<unknown>"))

        assert not failures, "Larger tables without primary keys:\n" + "\n".join(failures)
