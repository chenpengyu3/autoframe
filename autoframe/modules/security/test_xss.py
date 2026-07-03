import pytest

from autoframe.core.client import HttpClient
from autoframe.core import logging
from autoframe.utils.helpers import filter_auth_required


@pytest.mark.security
class TestXss:
    """XSS (Cross-Site Scripting) detection tests."""

    def test_xss_reflection(
        self, client: HttpClient, security_test_params: dict
    ):
        """Inject XSS payloads and check for unescaped reflection in responses."""
        payloads = security_test_params.get("xss", [])
        if not payloads:
            pytest.skip("No XSS payloads configured")

        endpoints = security_test_params.get("endpoints", [])
        injectable = [
            ep for ep in filter_auth_required(endpoints, client)
            if ep.get("accepts_params", False)
        ]
        if not injectable:
            injectable = filter_auth_required(endpoints, client)[:5]
        if not injectable:
            pytest.skip("No accessible endpoints for XSS testing")

        vulnerabilities = []
        for endpoint in injectable:
            path = endpoint.get("path", "/")
            for payload in payloads:
                try:
                    response = client.get(
                        path, params={"q": payload, "input": payload, "name": payload}
                    )
                    body = response.text
                    if payload in body:
                        content_type = response.headers.get("content-type", "")
                        if "html" in content_type or "json" in content_type:
                            vulnerabilities.append(
                                f"{path} reflects unescaped XSS payload: "
                                f"'{str(payload)[:50]}...'"
                            )
                            logging.error(
                                f"Potential XSS at {path}: "
                                f"payload reflected unescaped"
                            )
                except Exception as e:
                    logging.debug(
                        f"{path} with XSS payload raised "
                        f"{type(e).__name__}: {e}"
                    )

        assert not vulnerabilities, (
            f"Potential XSS vulnerabilities found:\n"
            + "\n".join(vulnerabilities)
        )
