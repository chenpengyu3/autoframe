import time

import pytest

from autoframe.core import logging


@pytest.mark.database
class TestQueries:
    """Database query performance tests."""

    def test_simple_query_performance(self, db_engine):
        """Verify that simple queries execute within acceptable time."""
        from sqlalchemy import text
        conn = db_engine.connect()
        try:
            start = time.time()
            conn.execute(text("SELECT 1"))
            elapsed = time.time() - start
            logging.info(f"Simple query took {elapsed:.4f}s")
            assert elapsed < 1.0, (
                f"Simple query took {elapsed:.4f}s (expected < 1.0s)"
            )
        finally:
            conn.close()

    def test_repeated_query_performance(self, db_engine):
        """Verify that repeated queries maintain consistent performance."""
        conn = db_engine.connect()
        try:
            times = []
            num_iterations = 50
            for _ in range(num_iterations):
                start = time.time()
                from sqlalchemy import text as sql_text
                conn.execute(sql_text("SELECT 1"))
                elapsed = time.time() - start
                times.append(elapsed)

            avg_time = sum(times) / len(times)
            max_time = max(times)
            logging.info(
                f"Repeated query ({num_iterations} iterations): "
                f"avg={avg_time:.4f}s, max={max_time:.4f}s"
            )
            assert avg_time < 0.5, (
                f"Average query time {avg_time:.4f}s exceeds 0.5s"
            )
            assert max_time < 2.0, (
                f"Max query time {max_time:.4f}s exceeds 2.0s"
            )
        finally:
            conn.close()
