import pytest

from autoframe.core.client import HttpClient
from autoframe.core import logging
from autoframe.utils.helpers import (
    make_no_auth_client, make_fake_token_client, dispatch_request, is_success,
)


@pytest.mark.security
class TestAuthBypass:
    """Authentication bypass detection tests."""

    def test_no_auth_access(
        self, client: HttpClient, config, security_test_params: dict
    ):
        """Test that protected endpoints reject requests with no authentication."""
        protected_endpoints = security_test_params.get("protected_endpoints", [])
        if not protected_endpoints:
            pytest.skip("No protected endpoints discovered for auth bypass testing")

        no_auth_client = make_no_auth_client(config)

        bypasses = []
        for endpoint in protected_endpoints:
            path = endpoint.get("path", "/")
            method = endpoint.get("method", "GET").upper()
            try:
                response = dispatch_request(no_auth_client, method, path, json={})
                if is_success(response.status_code):
                    bypasses.append(
                        f"{method} {path}: returned {response.status_code} "
                        f"without authentication"
                    )
                    logging.error(
                        f"Auth bypass: {method} {path} returned "
                        f"{response.status_code} without auth"
                    )
                else:
                    logging.info(
                        f"{method} {path}: correctly returned "
                        f"{response.status_code} without auth"
                    )
            except Exception as e:
                logging.debug(
                    f"{method} {path} raised {type(e).__name__}: {e}"
                )

        assert not bypasses, (
            f"Authentication bypass vulnerabilities:\n" + "\n".join(bypasses)
        )

    def test_fake_token_rejected(
        self, client: HttpClient, config, security_test_params: dict
    ):
        """Test that protected endpoints reject requests with fake tokens."""
        protected_endpoints = security_test_params.get("protected_endpoints", [])
        if not protected_endpoints:
            pytest.skip("No protected endpoints discovered for auth bypass testing")

        fake_client = make_fake_token_client(config)

        bypasses = []
        for endpoint in protected_endpoints:
            path = endpoint.get("path", "/")
            method = endpoint.get("method", "GET").upper()
            try:
                response = dispatch_request(fake_client, method, path, json={})
                if is_success(response.status_code):
                    bypasses.append(
                        f"{method} {path}: returned {response.status_code} "
                        f"with fake token"
                    )
                    logging.error(
                        f"Auth bypass: {method} {path} accepted fake token"
                    )
                else:
                    logging.info(
                        f"{method} {path}: correctly returned "
                        f"{response.status_code} with fake token"
                    )
            except Exception as e:
                logging.debug(
                    f"{method} {path} raised {type(e).__name__}: {e}"
                )

        assert not bypasses, (
            f"Fake token accepted for:\n" + "\n".join(bypasses)
        )

    def test_expired_token_rejected(
        self, client: HttpClient, config, security_test_params: dict
    ):
        """Test that protected endpoints reject requests with expired tokens."""
        protected_endpoints = security_test_params.get("protected_endpoints", [])
        if not protected_endpoints:
            pytest.skip("No protected endpoints discovered for auth bypass testing")

        expired_token = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyLCJleHAiOjE1MTYyMzkwMjJ9."
            "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        )
        expired_client = make_fake_token_client(config, token=expired_token)

        bypasses = []
        for endpoint in protected_endpoints[:3]:
            path = endpoint.get("path", "/")
            method = endpoint.get("method", "GET").upper()
            try:
                response = dispatch_request(expired_client, method, path, json={})
                if is_success(response.status_code):
                    bypasses.append(
                        f"{method} {path}: returned {response.status_code} "
                        f"with expired token"
                    )
                    logging.error(
                        f"Auth bypass: {method} {path} accepted expired token"
                    )
                else:
                    logging.info(
                        f"{method} {path}: correctly returned "
                        f"{response.status_code} with expired token"
                    )
            except Exception as e:
                logging.debug(
                    f"{method} {path} raised {type(e).__name__}: {e}"
                )

        assert not bypasses, (
            f"Expired token accepted for:\n" + "\n".join(bypasses)
        )
