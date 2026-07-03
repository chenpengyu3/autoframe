"""Data models for auto-discovered project information."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DiscoveredEndpoint:
    path: str
    methods: list[str] = field(default_factory=lambda: ["GET"])
    parameters: list[dict] = field(default_factory=list)
    request_schema: Optional[dict] = None
    response_schema: Optional[dict] = None
    auth_required: bool = False
    tags: list[str] = field(default_factory=list)
    source: str = "probe"  # "openapi" | "source" | "probe"
    verified: bool = False
    status_code: Optional[int] = None
    safe_to_call: bool = False
    kind: str = "http"  # http | actuator | graphql | websocket | sse | download
    consumes: list[str] = field(default_factory=list)
    produces: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class DiscoveredResource:
    name: str
    base_path: str
    create_endpoint: Optional[DiscoveredEndpoint] = None
    read_endpoint: Optional[DiscoveredEndpoint] = None
    update_endpoint: Optional[DiscoveredEndpoint] = None
    delete_endpoint: Optional[DiscoveredEndpoint] = None
    id_field: str = "id"
    create_body: dict = field(default_factory=dict)
    update_body: dict = field(default_factory=dict)
    read_path_template: str = ""
    update_path_template: str = ""
    skip_update: bool = False
    skip_delete_verify: bool = False
    operations: list[str] = field(default_factory=list)
    confidence: str = "medium"
    testable: bool = False


@dataclass
class DiscoveredAuth:
    auth_type: str = "none"
    login_endpoint: Optional[str] = None
    login_body: Optional[dict] = None
    token_field: str = "token"
    token: Optional[str] = field(default=None, repr=False)
    detected_from_source: bool = False
    acquisition_failed: bool = False  # True if login endpoint found but token not obtained


@dataclass
class DiscoveredDatabase:
    db_type: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = field(default=None, repr=False)
    connection_url: Optional[str] = field(default=None, repr=False)
    tables: list[dict] = field(default_factory=list)


@dataclass
class DiscoveredProject:
    project_type: str = "unknown"
    endpoints: list[DiscoveredEndpoint] = field(default_factory=list)
    resources: list[DiscoveredResource] = field(default_factory=list)
    auth: DiscoveredAuth = field(default_factory=DiscoveredAuth)
    database: Optional[DiscoveredDatabase] = None
    base_url: str = ""
    health_endpoints: list[str] = field(default_factory=list)
    coverage: dict = field(default_factory=dict)
