"""Generated live database schema matrix tests."""

import re

import pytest


def _column_names(table: dict) -> set[str]:
    return {column.get("name") for column in table.get("columns", [])}


@pytest.mark.database_matrix
class TestDatabaseMatrix:
    def test_database_table_inventory_matrix(self, db_table_case):
        name = db_table_case.get("name", "")
        assert name
        assert " " not in name
        assert db_table_case.get("columns"), f"Table has no columns: {name}"

    def test_database_column_inventory_matrix(self, db_column_case):
        table = db_column_case["table"]
        column = db_column_case["column"]
        name = column.get("name", "")
        assert name, f"Column without name in table {table.get('name')}"
        assert " " not in name, f"Column name contains spaces: {table.get('name')}.{name}"
        assert column.get("type") is not None, f"Column missing type: {table.get('name')}.{name}"
        assert isinstance(column.get("nullable", True), bool)

    def test_database_primary_key_matrix(self, db_primary_key_case):
        table = db_primary_key_case["table"]
        column_name = db_primary_key_case["column_name"]
        assert column_name in _column_names(table), (
            f"Primary key column not present in table {table.get('name')}: {column_name}"
        )

    def test_database_foreign_key_matrix(self, db_foreign_key_case):
        table = db_foreign_key_case["table"]
        foreign_key = db_foreign_key_case["foreign_key"]
        constrained = foreign_key.get("constrained_columns") or []
        referred = foreign_key.get("referred_columns") or []
        assert constrained, f"Foreign key without constrained columns: {table.get('name')}"
        assert referred, f"Foreign key without referred columns: {table.get('name')}"
        assert len(constrained) == len(referred), f"Foreign key column count mismatch: {table.get('name')}"
        for column_name in constrained:
            assert column_name in _column_names(table), (
                f"Foreign key column not present in table {table.get('name')}: {column_name}"
            )

    def test_database_index_matrix(self, db_index_case):
        table = db_index_case["table"]
        index = db_index_case["index"]
        columns = index.get("column_names") or []
        assert columns, f"Index without columns: {table.get('name')}.{index.get('name')}"
        for column_name in columns:
            assert column_name in _column_names(table), (
                f"Index column not present in table {table.get('name')}: {column_name}"
            )

    def test_database_unique_constraint_matrix(self, db_unique_constraint_case):
        table = db_unique_constraint_case["table"]
        constraint = db_unique_constraint_case["constraint"]
        columns = constraint.get("column_names") or []
        assert columns, f"Unique constraint without columns: {table.get('name')}.{constraint.get('name')}"
        for column_name in columns:
            assert column_name in _column_names(table), (
                f"Unique constraint column not present in table {table.get('name')}: {column_name}"
            )

    def test_database_string_column_matrix(self, db_string_column_case):
        column = db_string_column_case["column"]
        column_type = str(column.get("type", ""))
        assert column_type
        assert column.get("name")

    def test_database_numeric_column_matrix(self, db_numeric_column_case):
        column = db_numeric_column_case["column"]
        assert str(column.get("type", ""))
        assert column.get("name")

    def test_database_temporal_column_matrix(self, db_temporal_column_case):
        column = db_temporal_column_case["column"]
        name = column.get("name", "")
        assert name
        assert str(column.get("type", ""))
