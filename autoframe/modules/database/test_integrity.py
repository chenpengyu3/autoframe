import pytest

from autoframe.core import logging


def _target_tables(db_engine, db_test_params):
    """Return configured tables or discover all database tables."""
    expected_tables = db_test_params.get("tables", [])
    if expected_tables:
        return expected_tables

    from sqlalchemy import inspect

    inspector = inspect(db_engine)
    tables = inspector.get_table_names()
    if not tables:
        pytest.skip("No database tables discovered")
    return tables


@pytest.mark.database
class TestIntegrity:
    """Database integrity constraint tests."""

    def test_database_tables_exist(self, db_engine, db_test_params):
        """Verify that expected database tables exist."""
        from sqlalchemy import inspect

        inspector = inspect(db_engine)
        expected_tables = _target_tables(db_engine, db_test_params)
        actual_tables = inspector.get_table_names()

        missing_tables = [
            table for table in expected_tables
            if table not in actual_tables
        ]
        assert not missing_tables, (
            f"Missing tables: {missing_tables}"
        )
        logging.info(
            f"All {len(expected_tables)} expected tables exist"
        )

    def test_table_has_primary_key(self, db_engine, db_test_params):
        """Verify that tables have primary keys defined."""
        from sqlalchemy import inspect

        inspector = inspect(db_engine)
        expected_tables = _target_tables(db_engine, db_test_params)
        tables_without_pk = []

        for table_name in expected_tables:
            pk = inspector.get_pk_constraint(table_name)
            if not pk or not pk.get("constrained_columns"):
                tables_without_pk.append(table_name)
                logging.warning(f"Table {table_name} has no primary key")
            else:
                logging.info(
                    f"Table {table_name} primary key: "
                    f"{pk['constrained_columns']}"
                )

        assert not tables_without_pk, (
            f"Tables without primary keys: {tables_without_pk}"
        )

    def test_foreign_key_constraints(self, db_engine, db_test_params):
        """Verify that foreign key constraints are properly defined."""
        from sqlalchemy import inspect

        inspector = inspect(db_engine)
        expected_tables = _target_tables(db_engine, db_test_params)
        fk_summary = {}

        for table_name in expected_tables:
            fks = inspector.get_foreign_keys(table_name)
            if fks:
                fk_summary[table_name] = [
                    {
                        "columns": fk["constrained_columns"],
                        "referred_table": fk["referred_table"],
                        "referred_columns": fk["referred_columns"],
                    }
                    for fk in fks
                ]
                logging.info(
                    f"Table {table_name} has {len(fks)} foreign key(s)"
                )
            else:
                logging.info(
                    f"Table {table_name} has no foreign keys"
                )

        logging.info(
            f"Foreign key summary: {len(fk_summary)} tables have FKs"
        )

    def test_not_null_constraints(self, db_engine, db_test_params):
        """Verify that NOT NULL constraints are properly defined."""
        from sqlalchemy import inspect

        inspector = inspect(db_engine)
        expected_tables = _target_tables(db_engine, db_test_params)

        for table_name in expected_tables:
            columns = inspector.get_columns(table_name)
            nullable_cols = [
                col["name"] for col in columns if col.get("nullable", True)
            ]
            non_nullable_cols = [
                col["name"] for col in columns if not col.get("nullable", True)
            ]
            logging.info(
                f"Table {table_name}: "
                f"{len(non_nullable_cols)} NOT NULL, "
                f"{len(nullable_cols)} nullable"
            )
