"""Test context for sharing state across modules."""

from typing import Any, Optional

from autoframe.core.config import FrameworkConfig
from autoframe.core.client import HttpClient, metrics as global_metrics


class TestContext:
    def __init__(self, config: FrameworkConfig):
        self.config = config
        self.client = HttpClient(
            base_url=config.service.base_url,
            auth=config.auth,
            timeout=30.0,
            retry_count=2,
        )
        self.metrics = global_metrics
        self.service_type: Optional[str] = None
        self._data: dict[str, Any] = {}

    def set(self, key: str, value: Any):
        self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def detect_service_type(self) -> str:
        if self.config.service.type != "auto":
            self.service_type = self.config.service.type
            return self.service_type

        try:
            resp = self.client.get("/actuator/health")
            if resp.status_code == 200:
                self.service_type = "spring_boot"
                return self.service_type
        except Exception:
            pass

        for endpoint in ["/health", "/healthz", "/api/health", "/ping", "/docs", "/openapi.json"]:
            try:
                resp = self.client.get(endpoint)
                if resp.status_code == 200:
                    self.service_type = "python"
                    return self.service_type
            except Exception:
                continue

        self.service_type = "unknown"
        return self.service_type
