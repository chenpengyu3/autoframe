"""Test data generators."""

import random
import string
import time


def random_string(length: int = 10) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def random_email() -> str:
    return f"{random_string(8).lower()}@example.com"


def random_int(low: int = 1, high: int = 10000) -> int:
    return random.randint(low, high)


def random_name() -> str:
    first = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Hank"]
    last = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Davis", "Miller"]
    return f"{random.choice(first)} {random.choice(last)}"


def random_user() -> dict:
    return {"name": random_name(), "email": random_email(), "age": random_int(18, 80)}


def timestamp_id() -> str:
    return f"{int(time.time() * 1000)}_{random_string(4)}"


def generate_from_schema(schema: dict) -> dict:
    """Generate test data from a JSON schema."""
    if not schema or not isinstance(schema, dict):
        return {}

    result = {}
    properties = schema.get("properties", {})
    for field_name, field_def in properties.items():
        field_type = field_def.get("type", "string")
        if field_type == "string":
            fmt = field_def.get("format", "")
            if fmt == "email":
                result[field_name] = random_email()
            elif "name" in field_name.lower():
                result[field_name] = random_name()
            elif "title" in field_name.lower():
                result[field_name] = f"Test {random_string(6)}"
            elif "description" in field_name.lower():
                result[field_name] = f"Test description {random_string(6)}"
            elif "password" in field_name.lower():
                result[field_name] = f"Pass_{random_string(8)}!"
            elif "url" in field_name.lower() or fmt == "uri":
                result[field_name] = f"https://example.com/{random_string(6)}"
            elif "phone" in field_name.lower():
                result[field_name] = f"138{random_int(10000000, 99999999)}"
            else:
                result[field_name] = f"test_{random_string(8)}"
        elif field_type == "integer":
            result[field_name] = random_int(1, 100)
        elif field_type == "number":
            result[field_name] = round(random.uniform(1.0, 100.0), 2)
        elif field_type == "boolean":
            result[field_name] = random.choice([True, False])
        elif field_type == "array":
            result[field_name] = []
        elif field_type == "object":
            result[field_name] = {}

    return result
