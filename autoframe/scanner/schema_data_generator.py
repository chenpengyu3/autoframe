"""Generate test data from JSON schemas and field name heuristics."""

import random
import string
from typing import Optional

from autoframe.scanner.models import DiscoveredEndpoint, DiscoveredResource
from autoframe.utils.data_generator import (
    random_string, random_email, random_name, random_int, generate_from_schema,
)


def generate_resource_test_data(resource: DiscoveredResource) -> DiscoveredResource:
    """Generate create and update body data for a CRUD resource."""
    if resource.create_endpoint and resource.create_endpoint.request_schema:
        resource.create_body = generate_from_schema(resource.create_endpoint.request_schema)
    elif not resource.create_body:
        resource.create_body = generate_endpoint_body(resource.create_endpoint) if resource.create_endpoint else {
            "name": f"test_{resource.name}_{random_string(6)}"
        }

    if resource.update_endpoint and resource.update_endpoint.request_schema:
        resource.update_body = generate_from_schema(resource.update_endpoint.request_schema)
    elif not resource.update_body:
        resource.update_body = generate_endpoint_body(resource.update_endpoint) if resource.update_endpoint else {
            "name": f"updated_{resource.name}_{random_string(6)}"
        }

    return resource


def generate_endpoint_body(endpoint: DiscoveredEndpoint) -> dict:
    """Generate a request body for an endpoint based on its schema."""
    if endpoint.request_schema:
        return generate_from_schema(endpoint.request_schema)

    # Try to infer from path
    path_lower = endpoint.path.lower()
    body = {}

    if "user" in path_lower:
        body = {"name": random_name(), "email": random_email()}
    elif "order" in path_lower:
        body = {"amount": random_int(1, 100), "product": f"product_{random_string(4)}"}
    elif "category" in path_lower or "folder" in path_lower:
        body = {"name": f"category_{random_string(6)}"}
    elif "message" in path_lower or "chat" in path_lower or "conversation" in path_lower:
        body = {"title": f"conversation_{random_string(6)}", "content": f"test content {random_string(4)}"}
    elif "card" in path_lower or "review" in path_lower:
        body = {"question": f"test question {random_string(4)}?", "answer": f"test answer {random_string(4)}"}
    elif "note" in path_lower or "error" in path_lower:
        body = {"title": f"note_{random_string(6)}", "content": f"test content {random_string(4)}"}
    else:
        body = {"name": f"test_{random_string(8)}"}

    return body


SECURITY_PAYLOADS = {
    "sql_injection": [
        "' OR '1'='1",
        "' OR '1'='1' --",
        "'; DROP TABLE users; --",
        "1 UNION SELECT * FROM users --",
        "admin'--",
        "' OR 1=1 #",
        "\" OR \"\"=\"",
        "1; WAITFOR DELAY '0:0:5' --",
    ],
    "xss": [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "<svg onload=alert('XSS')>",
        "javascript:alert('XSS')",
        "'-alert('XSS')-'",
        "\"><script>alert('XSS')</script>",
    ],
    "path_traversal": [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "....//....//....//etc/passwd",
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    ],
    "command_injection": [
        "; ls -la",
        "| cat /etc/passwd",
        "$(whoami)",
        "`id`",
    ],
    "security_headers": {
        "required": [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "Content-Security-Policy",
            "Strict-Transport-Security",
        ],
        "recommended": [
            "X-XSS-Protection",
            "Referrer-Policy",
            "Permissions-Policy",
        ],
    },
}
