import pytest

from autoframe.core.client import HttpClient
from autoframe.core import logging
from autoframe.utils.helpers import filter_auth_required

SQL_ERROR_PATTERNS = [
    "sql syntax",
    "mysql",
    "sqlite",
    "postgresql",
    "ORA-",
    "SQL Server",
    "syntax error",
    "unterminated quoted string",
    "you have an error in your sql",
    "microsoft ole db",
    "unclosed quotation mark",
    "quoted string not properly terminated",
]


@pytest.mark.security
class TestSqlInjection:
    """SQL injection detection tests."""

    def test_sql_injection_query_params(
        self, client: HttpClient, security_test_params: dict
    ):
        """Inject SQL payloads as query parameters and check for SQL error patterns."""
        payloads = security_test_params.get("sql_injection", [])
        if not payloads:
            pytest.skip("No SQL injection payloads configured")

        endpoints = security_test_params.get("endpoints", [])
        # Use endpoints that accept params and don't require auth
        injectable = [
            ep for ep in filter_auth_required(endpoints, client)
            if ep.get("accepts_params", False)
        ]
        if not injectable:
            injectable = filter_auth_required(endpoints, client)[:5]
        if not injectable:
            pytest.skip("No accessible endpoints for SQL injection testing")

        vulnerabilities = []
        for endpoint in injectable:
            path = endpoint.get("path", "/")
            for payload in payloads:
                try:
                    response = client.get(
                        path, params={"q": payload, "search": payload, "id": payload}
                    )
                    body = response.text.lower()
                    for pattern in SQL_ERROR_PATTERNS:
                        if pattern.lower() in body:
                            vulnerabilities.append(
                                f"{path} with payload '{str(payload)[:30]}...' "
                                f"exposed pattern '{pattern}'"
                            )
                            logging.error(
                                f"Potential SQL injection at {path}: "
                                f"pattern '{pattern}' found"
                            )
                            break
                except Exception as e:
                    logging.debug(
                        f"{path} with payload '{str(payload)[:30]}...' "
                        f"raised {type(e).__name__}: {e}"
                    )

        assert not vulnerabilities, (
            f"Potential SQL injection vulnerabilities found:\n"
            + "\n".join(vulnerabilities)
        )
