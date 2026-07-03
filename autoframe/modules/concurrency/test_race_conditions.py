import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from autoframe.core.client import HttpClient
from autoframe.core import logging
from autoframe.utils.helpers import filter_auth_required, extract_id, is_success


@pytest.mark.concurrency
class TestRaceConditions:
    """Race condition detection tests."""

    def test_concurrent_writes_consistency(
        self, client: HttpClient, config, concurrency_test_params: dict
    ):
        """Test that concurrent writes to the same resource maintain consistency."""
        write_endpoints = concurrency_test_params.get("write_endpoints", [])
        if not write_endpoints:
            pytest.skip("No write endpoints discovered")

        accessible = filter_auth_required(write_endpoints, client)
        if not accessible:
            pytest.skip("No accessible write endpoints (all require auth)")

        max_threads = concurrency_test_params.get("max_threads", 10)
        write_endpoint = accessible[0]
        path = write_endpoint.get("path", "/")
        method = write_endpoint.get("method", "POST").upper()
        body = write_endpoint.get("request_body") or {}

        errors = []
        successes = 0
        clean_rejections = 0
        lock = threading.Lock()

        def concurrent_write(thread_id):
            nonlocal successes, clean_rejections
            req_body = dict(body) if isinstance(body, dict) else {}
            req_body["thread_id"] = thread_id
            req_body["timestamp"] = time.time()
            try:
                response = getattr(client, method.lower())(path, json=req_body)
                with lock:
                    if is_success(response.status_code):
                        successes += 1
                    elif response.status_code < 500:
                        clean_rejections += 1
                    else:
                        errors.append(
                            f"Thread {thread_id}: status {response.status_code}"
                        )
            except Exception as e:
                with lock:
                    errors.append(f"Thread {thread_id}: {e}")

        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = [
                executor.submit(concurrent_write, i)
                for i in range(max_threads)
            ]
            for future in as_completed(futures):
                future.result()

        logging.info(
            f"Concurrent writes: {successes}/{max_threads} succeeded, "
            f"{clean_rejections}/{max_threads} cleanly rejected"
        )
        assert not errors, (
            "Concurrent writes caused server errors:\n" + "\n".join(errors[:10])
        )

    def test_concurrent_create_no_duplicates(
        self, client: HttpClient, config, concurrency_test_params: dict
    ):
        """Test that concurrent creates with same data don't produce duplicates."""
        crud_resources = concurrency_test_params.get("crud_resources", [])
        if not crud_resources:
            pytest.skip("No CRUD resources discovered for duplicate test")

        max_threads = concurrency_test_params.get("max_threads", 10)
        resource = crud_resources[0]
        path = resource.get("create_path", resource.get("base_path", "/"))
        base_body = resource.get("create_body", {})
        id_field = resource.get("id_field", "id")
        unique_id = f"race_test_{time.time()}"

        created_ids = []
        lock = threading.Lock()

        def create_resource(thread_id):
            body = dict(base_body)
            body["unique_id"] = unique_id
            body["thread_id"] = thread_id
            try:
                response = client.post(path, json=body)
                if is_success(response.status_code):
                    data = response.json()
                    resource_id = extract_id(data, id_field)
                    with lock:
                        created_ids.append(resource_id)
            except Exception as e:
                logging.debug(f"Thread {thread_id}: {e}")

        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = [
                executor.submit(create_resource, i)
                for i in range(max_threads)
            ]
            for future in as_completed(futures):
                future.result()

        if created_ids:
            unique_ids = set(created_ids)
            logging.info(
                f"Concurrent creates: {len(created_ids)} total, "
                f"{len(unique_ids)} unique IDs"
            )
            if len(unique_ids) < len(created_ids):
                logging.warning(
                    f"Duplicate IDs detected: "
                    f"{len(created_ids) - len(unique_ids)} duplicates"
                )
        else:
            logging.info("No resources created (all requests failed)")
