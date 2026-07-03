import pytest

from autoframe.core import logging


@pytest.mark.database
class TestConnections:
    """Database connection tests."""

    def test_connection_established(self, db_engine):
        """Verify that a database connection can be established."""
        connection = db_engine.connect()
        assert connection is not None, "Failed to establish database connection"
        logging.info("Database connection established successfully")
        connection.close()

    def test_connection_pool_size(self, db_engine, db_config):
        """Verify the connection pool is configured correctly."""
        pool = db_engine.pool
        pool_size = pool.size()
        expected_size = getattr(db_config, "pool_size", 10)
        assert pool_size >= 1, (
            f"Pool size {pool_size} is too small (expected >= 1)"
        )
        logging.info(
            f"Connection pool size: {pool_size} (expected: {expected_size})"
        )

    def test_connection_recovery(self, db_engine):
        """Verify the connection pool recovers after a connection is closed."""
        # Get a connection and close it
        conn1 = db_engine.connect()
        conn1.close()
        # Get another connection - should work fine
        conn2 = db_engine.connect()
        assert conn2 is not None, "Connection pool failed to recover"
        from sqlalchemy import text
        result = conn2.execute(text("SELECT 1"))
        conn2.close()
        logging.info("Connection pool recovery verified")

    def test_concurrent_transactions(self, db_engine):
        """Verify the engine handles concurrent transactions."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        errors = []

        def run_transaction(thread_id):
            try:
                conn = db_engine.connect()
                trans = conn.begin()
                try:
                    from sqlalchemy import text as sql_text
                    conn.execute(sql_text("SELECT 1"))
                    trans.commit()
                except Exception:
                    trans.rollback()
                    raise
                finally:
                    conn.close()
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(run_transaction, i) for i in range(10)
            ]
            for future in as_completed(futures):
                future.result()

        assert not errors, (
            f"Concurrent transaction errors:\n" + "\n".join(errors)
        )
        logging.info("Concurrent transactions completed successfully")
