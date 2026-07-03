"""HTTP client wrapper with auto metrics collection and authentication."""

import time
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

from autoframe.core.config import AuthConfig


@dataclass
class RequestMetrics:
    method: str
    url: str
    status_code: int
    elapsed_ms: float
    request_body: Any = None
    response_body: Any = None
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


class MetricsCollector:
    def __init__(self):
        self.records: list[RequestMetrics] = []

    def record(self, metrics: RequestMetrics):
        self.records.append(metrics)

    def clear(self):
        self.records.clear()

    @property
    def count(self) -> int:
        return len(self.records)

    @property
    def error_count(self) -> int:
        return sum(1 for r in self.records if r.error or r.status_code >= 400)

    @property
    def error_rate(self) -> float:
        if not self.records:
            return 0.0
        return self.error_count / self.count * 100

    @property
    def avg_response_time_ms(self) -> float:
        if not self.records:
            return 0.0
        return sum(r.elapsed_ms for r in self.records) / self.count

    @property
    def p50_response_time_ms(self) -> float:
        return self._percentile(50)

    @property
    def p90_response_time_ms(self) -> float:
        return self._percentile(90)

    @property
    def p99_response_time_ms(self) -> float:
        return self._percentile(99)

    @property
    def max_response_time_ms(self) -> float:
        if not self.records:
            return 0.0
        return max(r.elapsed_ms for r in self.records)

    @property
    def min_response_time_ms(self) -> float:
        if not self.records:
            return 0.0
        return min(r.elapsed_ms for r in self.records)

    def _percentile(self, p: int) -> float:
        if not self.records:
            return 0.0
        sorted_times = sorted(r.elapsed_ms for r in self.records)
        index = int(len(sorted_times) * p / 100)
        index = min(index, len(sorted_times) - 1)
        return sorted_times[index]


metrics = MetricsCollector()


def _build_auth_headers(auth: AuthConfig) -> dict[str, str]:
    headers: dict[str, str] = {}
    if auth.type == "bearer" and auth.token:
        headers["Authorization"] = f"Bearer {auth.token}"
    elif auth.type == "basic" and auth.username and auth.password:
        import base64
        credentials = base64.b64encode(f"{auth.username}:{auth.password}".encode()).decode()
        headers["Authorization"] = f"Basic {credentials}"
    return headers


class HttpClient:
    def __init__(
        self,
        base_url: str,
        auth: Optional[AuthConfig] = None,
        timeout: float = 30.0,
        retry_count: int = 0,
        retry_delay: float = 1.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.auth = auth or AuthConfig()
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self._extra_headers: dict[str, str] = {}
        self.metrics = metrics

    def set_header(self, key: str, value: str):
        self._extra_headers[key] = value

    def _make_request(self, method: str, path: str, **kwargs) -> httpx.Response:
        url = f"{self.base_url}{path}"
        headers = _build_auth_headers(self.auth)
        headers.update(self._extra_headers)
        kwargs.setdefault("headers", {}).update(headers)

        last_error = None
        for attempt in range(self.retry_count + 1):
            start_time = time.perf_counter()
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.request(method, url, **kwargs)
                elapsed_ms = (time.perf_counter() - start_time) * 1000

                request_body = kwargs.get("content") or kwargs.get("json")
                try:
                    response_body = response.json()
                except Exception:
                    response_body = response.text

                req_metrics = RequestMetrics(
                    method=method, url=url, status_code=response.status_code,
                    elapsed_ms=elapsed_ms, request_body=request_body,
                    response_body=response_body,
                )
                metrics.record(req_metrics)
                return response

            except Exception as e:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                last_error = e
                req_metrics = RequestMetrics(
                    method=method, url=url, status_code=0,
                    elapsed_ms=elapsed_ms, error=str(e),
                )
                metrics.record(req_metrics)
                if attempt < self.retry_count:
                    time.sleep(self.retry_delay * (2 ** attempt))

        raise last_error

    def get(self, path: str, **kwargs) -> httpx.Response:
        return self._make_request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> httpx.Response:
        return self._make_request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> httpx.Response:
        return self._make_request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs) -> httpx.Response:
        return self._make_request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs) -> httpx.Response:
        return self._make_request("DELETE", path, **kwargs)

    def head(self, path: str, **kwargs) -> httpx.Response:
        return self._make_request("HEAD", path, **kwargs)

    def options(self, path: str, **kwargs) -> httpx.Response:
        return self._make_request("OPTIONS", path, **kwargs)
