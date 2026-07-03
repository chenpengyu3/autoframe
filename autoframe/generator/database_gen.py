"""Generate database test parameters from discovered database configuration."""

from autoframe.generator.base import BaseTestGenerator


class DatabaseTestGenerator(BaseTestGenerator):
    """Produces parameters for database integration tests.

    If no database was discovered, ``db_config`` will be ``None`` and the
    corresponding tests should skip themselves.
    """

    def generate(self) -> dict:
        db = self.project.database
        if db is None:
            return {"db_config": None}

        return {
            "db_config": {
                "db_type": db.db_type,
                "host": db.host,
                "port": db.port,
                "database": db.database,
                "username": db.username,
                "password": db.password,
                "tables": db.tables or [],
            },
        }
