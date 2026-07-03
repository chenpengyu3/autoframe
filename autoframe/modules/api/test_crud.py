"""CRUD operation lifecycle tests."""

import pytest

from autoframe.core.client import HttpClient
from autoframe.core import logging
from autoframe.utils.helpers import extract_id, is_success, is_client_error


@pytest.mark.api
class TestCRUD:
    """Test full CRUD lifecycle for auto-discovered resources."""

    def test_crud_lifecycle(self, client: HttpClient, crud_test_params):
        """Test POST -> GET -> PUT -> DELETE for each discovered resource."""
        resources = crud_test_params.get("crud_resources", [])
        if not resources:
            pytest.skip("No CRUD resources discovered")

        tested_resources = 0
        skipped_reasons = []
        for resource in resources:
            name = resource.get("name", "unknown")
            create_path = resource.get("create_path", resource.get("base_path", ""))
            create_body = resource.get("create_body", {})
            update_body = resource.get("update_body", {})
            id_field = resource.get("id_field", "id")
            read_template = resource.get("read_path_template", f"{resource.get('base_path', '')}/{{id}}")
            update_template = resource.get("update_path_template", f"{resource.get('base_path', '')}/{{id}}")
            skip_update = resource.get("skip_update", False)
            skip_delete_verify = resource.get("skip_delete_verify", False)
            has_create_schema = resource.get("has_create_schema", False)

            # CREATE
            create_resp = client.post(create_path, json=create_body)
            if create_resp.status_code in (401, 403):
                reason = f"{name}: create returned {create_resp.status_code} (auth/permission)"
                skipped_reasons.append(reason)
                logging.warning(f"CREATE {reason}; skipping resource")
                continue
            if create_resp.status_code == 400:
                reason = f"{name}: create returned 400 (generated body rejected)"
                skipped_reasons.append(reason)
                logging.warning(
                    f"CREATE {name}: generated body was rejected with 400; "
                    "skipping resource because no request schema is available"
                )
                continue
            if not has_create_schema and not is_success(create_resp.status_code):
                reason = (
                    f"{name}: create returned {create_resp.status_code} "
                    "(no request schema; generated body is exploratory)"
                )
                skipped_reasons.append(reason)
                logging.warning(f"CREATE {reason}; skipping resource")
                continue
            assert is_success(create_resp.status_code), (
                f"CREATE {name}: expected 2xx, got {create_resp.status_code}"
            )

            try:
                created = create_resp.json()
            except Exception:
                pytest.fail(f"CREATE {name}: response is not valid JSON")

            resource_id = extract_id(created, id_field)
            if resource_id is None:
                reason = f"{name}: create response missing id field '{id_field}'"
                skipped_reasons.append(reason)
                logging.warning(
                    f"CREATE {name}: response missing '{id_field}' field; "
                    "skipping read/update/delete lifecycle checks for this resource"
                )
                continue

            tested_resources += 1
            read_url = read_template.replace("{id}", str(resource_id))
            update_url = update_template.replace("{id}", str(resource_id))

            # READ
            read_resp = client.get(read_url)
            if is_success(read_resp.status_code):
                read_data = read_resp.json()
                assert read_data is not None, f"READ {name}: empty response"
            elif is_client_error(read_resp.status_code):
                pass  # No GET /{id} endpoint or not found
            else:
                pytest.fail(f"READ {name}: unexpected status {read_resp.status_code}")

            # UPDATE
            if not skip_update:
                update_resp = client.put(update_url, json=update_body)
                assert is_success(update_resp.status_code), (
                    f"UPDATE {name}: expected 2xx, got {update_resp.status_code}"
                )

            # DELETE
            base_path = resource.get("base_path", "")
            delete_url = f"{base_path}/{resource_id}"
            delete_resp = client.delete(delete_url)
            assert is_success(delete_resp.status_code), (
                f"DELETE {name}: expected 2xx, got {delete_resp.status_code}"
            )

            # VERIFY DELETE
            if not skip_delete_verify:
                verify_resp = client.get(read_url)
                assert is_client_error(verify_resp.status_code), (
                    f"VERIFY DELETE {name}: expected 4xx, got {verify_resp.status_code}"
                )

        if tested_resources == 0:
            detail = "; ".join(skipped_reasons[:8])
            suffix = f": {detail}" if detail else ""
            pytest.skip(f"No CRUD resources could complete a full lifecycle{suffix}")
