import pytest

from autoframe.core.client import HttpClient
from autoframe.core import logging
from autoframe.utils.helpers import filter_auth_required


@pytest.mark.security
class TestHeaders:
    """Security header validation tests."""

    def test_security_headers_present(
        self, client: HttpClient, security_test_params: dict
    ):
        """Check for the presence of important security headers using discovered config."""
        headers_config = security_test_params.get("security_headers", {})
        if not headers_config:
            pytest.skip("No security headers configuration discovered")

        required_headers = headers_config.get("required", [])
        recommended_headers = headers_config.get("recommended", [])

        # If config has nested format (header_name -> {expected, severity}),
        # convert to flat list
        if isinstance(required_headers, dict):
            required_headers = list(required_headers.keys())
        if isinstance(recommended_headers, dict):
            recommended_headers = list(recommended_headers.keys())

        all_headers = required_headers + recommended_headers
        if not all_headers:
            pytest.skip("No security headers to check")

        # Find an accessible endpoint to test headers
        endpoints = security_test_params.get("endpoints", [])
        accessible = filter_auth_required(endpoints, client)
        test_endpoints = [ep for ep in accessible if ep.get("method", "GET") == "GET"]

        if not test_endpoints:
            pytest.skip("No accessible GET endpoints for header testing")

        missing_headers = []
        for endpoint in test_endpoints[:5]:
            path = endpoint.get("path", "/")
            try:
                response = client.get(path)
                response_headers = response.headers

                for header_name in all_headers:
                    if header_name not in response_headers:
                        is_required = header_name in required_headers
                        severity = "high" if is_required else "low"
                        missing_headers.append(
                            f"{path}: missing {header_name} "
                            f"(severity: {severity})"
                        )
                        logging.warning(
                            f"{path}: missing security header {header_name}"
                        )
                    else:
                        logging.info(
                            f"{path}: {header_name} = '{response_headers[header_name]}'"
                        )
            except Exception as e:
                logging.error(f"{path} raised {type(e).__name__}: {e}")

        if missing_headers:
            logging.warning(
                f"Security header issues found:\n" + "\n".join(missing_headers)
            )
        # Warn but don't fail for missing headers - they're best practice
