"""Generate CRUD lifecycle test parameters from discovered resources."""

from autoframe.generator.base import BaseTestGenerator


class CrudTestGenerator(BaseTestGenerator):
    """Produces parameters for CRUD lifecycle tests."""

    def generate(self) -> dict:
        crud_resources = []
        for res in self.project.resources:
            if not res.testable:
                continue
            crud_resources.append({
                "name": res.name,
                "base_path": res.base_path,
                "create_path": res.create_endpoint.path if res.create_endpoint else res.base_path,
                "create_body": res.create_body or {"name": f"test_{res.name}"},
                "update_body": res.update_body or {"name": f"updated_{res.name}"},
                "id_field": res.id_field or "id",
                "read_path_template": res.read_path_template or f"{res.base_path}/{{id}}",
                "update_path_template": res.update_path_template or f"{res.base_path}/{{id}}",
                "skip_update": res.skip_update,
                "skip_delete_verify": res.skip_delete_verify,
                "operations": res.operations,
                "confidence": res.confidence,
                "has_create_schema": bool(res.create_endpoint and res.create_endpoint.request_schema),
                "has_update_schema": bool(res.update_endpoint and res.update_endpoint.request_schema),
            })

        return {"crud_resources": crud_resources}
