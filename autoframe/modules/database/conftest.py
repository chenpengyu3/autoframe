import pytest
from autoframe.generator.database_gen import DatabaseTestGenerator


@pytest.fixture(scope="session")
def db_test_params(discovered_project):
    gen = DatabaseTestGenerator(discovered_project)
    return gen.generate()


@pytest.fixture(scope="session")
def db_config(db_test_params):
    cfg = db_test_params.get("db_config")
    if not cfg:
        pytest.skip("No database configuration detected")
    return cfg


@pytest.fixture(scope="session")
def db_engine(db_config):
    from sqlalchemy import create_engine

    # Support both dict and object formats
    if isinstance(db_config, dict):
        db_type = db_config.get("db_type")
        username = db_config.get("username")
        password = db_config.get("password")
        host = db_config.get("host")
        port = db_config.get("port")
        database = db_config.get("database")
    else:
        db_type = db_config.db_type
        username = db_config.username
        password = db_config.password
        host = db_config.host
        port = db_config.port
        database = db_config.database

    if db_type == "mysql":
        url = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
    elif db_type == "postgresql":
        url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
    elif db_type == "sqlite":
        url = f"sqlite:///{database}"
    else:
        pytest.skip(f"Unsupported database type: {db_type}")

    engine = create_engine(url, pool_size=10, max_overflow=5)
    yield engine
    engine.dispose()
