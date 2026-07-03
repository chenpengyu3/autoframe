"""扫描流水线 - 自动发现项目的全部信息。"""

from typing import Optional

from rich.console import Console
from rich.table import Table

from autoframe.scanner.models import DiscoveredProject, DiscoveredAuth, DiscoveredDatabase
from autoframe.scanner.project_detector import detect_from_source, detect_from_service
from autoframe.scanner.openapi_fetcher import fetch_openapi_spec, parse_openapi_endpoints
from autoframe.scanner.source_parser import parse_routes
from autoframe.scanner.endpoint_enricher import probe_endpoints, probe_untested_paths
from autoframe.scanner.resource_detector import detect_crud_resources
from autoframe.scanner.auth_detector import detect_auth
from autoframe.scanner.database_detector import detect_database
from autoframe.scanner.schema_data_generator import generate_resource_test_data
from autoframe.scanner.coverage_auditor import audit_scan_coverage

console = Console(force_terminal=True)


class ScanPipeline:
    """编排完整的自动发现扫描流程。"""

    def __init__(
        self,
        base_url: str,
        project_path: Optional[str] = None,
        project_type: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.project_path = project_path
        self.project_type = project_type or "unknown"

    def run(self) -> DiscoveredProject:
        """运行完整扫描流水线。"""
        console.rule("[bold cyan]AutoFrame 扫描流水线[/bold cyan]")

        # 步骤 1：检测项目类型
        self._step("正在检测项目类型...")
        if self.project_type == "unknown":
            if self.project_path:
                self.project_type = detect_from_source(self.project_path) or "unknown"
            if self.project_type == "unknown":
                self.project_type = detect_from_service(self.base_url)
        console.print(f"  项目类型: [green]{self.project_type}[/green]")

        # 步骤 2：发现端点
        self._step("正在发现 API 端点...")
        endpoints = []

        # 第一层：OpenAPI 规范
        spec = fetch_openapi_spec(self.base_url)
        if spec:
            endpoints = parse_openapi_endpoints(spec)
            console.print(f"  找到 OpenAPI 规范: [green]{len(endpoints)} 个端点[/green]")
        else:
            console.print("  未找到 OpenAPI 规范，尝试解析源码...")

        # 第二层：源码解析
        if not endpoints and self.project_path:
            endpoints = parse_routes(self.project_path, self.project_type)
            console.print(f"  源码解析: [green]{len(endpoints)} 个端点[/green]")

        # 第三层：暴力探测
        if not endpoints:
            console.print("  未发现端点，尝试暴力探测...")
            known_paths = {ep.path for ep in endpoints}
            endpoints = probe_untested_paths(self.base_url, known_paths)
            console.print(f"  探测发现: [green]{len(endpoints)} 个端点[/green]")
        else:
            known_paths = {ep.path for ep in endpoints}
            probed = probe_untested_paths(self.base_url, known_paths)
            if probed:
                endpoints.extend(probed)
                console.print(f"  运行时补充探测: [green]{len(probed)} 个端点[/green]")

        # 验证端点（检测存在性、认证）
        if endpoints:
            endpoints = probe_endpoints(self.base_url, endpoints)
            verified_count = sum(1 for ep in endpoints if ep.verified)
            safe_count = sum(1 for ep in endpoints if ep.safe_to_call)
            console.print(
                f"  保留端点: [green]{len(endpoints)} 个[/green] "
                f"(已验证 {verified_count} 个，可安全调用 {safe_count} 个)"
            )

        # 步骤 3：检测 CRUD 资源
        self._step("正在检测 CRUD 资源...")
        resources = detect_crud_resources(endpoints)
        for r in resources:
            r = generate_resource_test_data(r)
        testable_count = sum(1 for r in resources if r.testable)
        console.print(
            f"  发现 [green]{len(resources)}[/green] 个 CRUD 候选资源，"
            f"[green]{testable_count}[/green] 个生命周期候选"
        )

        # 步骤 4：检测认证
        self._step("正在检测认证方式...")
        auth = detect_auth(self.base_url, self.project_path)
        console.print(f"  认证类型: [green]{auth.auth_type}[/green]")
        if auth.login_endpoint:
            console.print(f"  登录端点: [green]{auth.login_endpoint}[/green]")

        # 步骤 5：检测数据库
        self._step("正在检测数据库...")
        database = detect_database(self.project_path)
        if database:
            console.print(f"  数据库: [green]{database.db_type}[/green] @ {database.host}:{database.port}/{database.database}")
        else:
            console.print("  未检测到数据库配置")

        # 步骤 6：发现健康检查端点
        self._step("正在发现健康检查端点...")
        health_endpoints = self._discover_health_endpoints(endpoints)
        console.print(f"  健康检查端点: [green]{len(health_endpoints)} 个[/green]")

        # 步骤 7：估算源码路由扫描覆盖率
        self._step("正在评估扫描覆盖率...")
        coverage = audit_scan_coverage(self.project_path, self.project_type, endpoints)
        if coverage.get("not_applicable"):
            console.print("  源码路由覆盖率: [yellow]未评估[/yellow] (未提供项目源码路径)")
        else:
            coverage_color = "green" if coverage.get("meets_95_percent") else "yellow"
            console.print(
                f"  源码路由覆盖率: [{coverage_color}]"
                f"{coverage.get('estimated_percent', 0):.2f}%[/{coverage_color}] "
                f"({coverage.get('parsed_source_routes', 0)}/"
                f"{coverage.get('candidate_routes', 0)})"
            )
        if coverage.get("meets_95_percent") is False:
            console.print(
                f"  [yellow]警告: 估算缺失 {coverage.get('estimated_missing', 0)} 个路由声明，"
                "建议提供 OpenAPI 或检查动态路由。[/yellow]"
            )

        # 构建结果
        project = DiscoveredProject(
            project_type=self.project_type,
            endpoints=endpoints,
            resources=resources,
            auth=auth,
            database=database,
            base_url=self.base_url,
            health_endpoints=health_endpoints,
            coverage=coverage,
        )

        # 打印摘要
        self._print_summary(project)

        return project

    def _discover_health_endpoints(self, endpoints) -> list[str]:
        """从端点列表中发现健康/状态检查端点。"""
        health_keywords = ("health", "ping", "status", "alive", "ready", "info")
        candidates = []
        for ep in endpoints:
            path_lower = ep.path.lower()
            if any(kw in path_lower for kw in health_keywords):
                candidates.append(ep.path)
        return candidates

    def _step(self, message: str):
        console.print(f"\n[bold blue]>>[/bold blue] {message}")

    def _print_summary(self, project: DiscoveredProject):
        console.rule("[bold cyan]扫描结果[/bold cyan]")

        table = Table(title="项目发现摘要")
        table.add_column("类别", style="bold")
        table.add_column("数量", style="green")
        table.add_column("详情")

        table.add_row("项目类型", "1", project.project_type)
        table.add_row("API 端点", str(len(project.endpoints)),
                       ", ".join(f"{ep.methods[0]} {ep.path}" for ep in project.endpoints[:5]) +
                       (f" ... 等 {len(project.endpoints)} 个" if len(project.endpoints) > 5 else ""))
        table.add_row("CRUD 候选资源", str(len(project.resources)),
                       self._format_resource_list(project.resources))
        testable_resources = [r for r in project.resources if r.testable]
        table.add_row("生命周期候选", str(len(testable_resources)),
                       self._format_resource_list(testable_resources))
        kind_counts = {}
        for ep in project.endpoints:
            kind_counts[ep.kind] = kind_counts.get(ep.kind, 0) + 1
        special = ", ".join(
            f"{kind}:{count}" for kind, count in sorted(kind_counts.items()) if kind != "http"
        )
        multipart_count = sum(1 for ep in project.endpoints if "multipart/form-data" in ep.consumes)
        if multipart_count:
            special = (special + ", " if special else "") + f"multipart:{multipart_count}"
        table.add_row("特殊端点", str(sum(count for kind, count in kind_counts.items() if kind != "http") + multipart_count),
                      special or "未发现")
        coverage = project.coverage or {}
        if coverage.get("not_applicable"):
            table.add_row("扫描覆盖率", "未评估", "未提供项目源码路径")
        else:
            table.add_row("扫描覆盖率", f"{coverage.get('estimated_percent', 0):.2f}%",
                          f"{coverage.get('parsed_source_routes', 0)}/{coverage.get('candidate_routes', 0)}"
                          + ("，达到95%" if coverage.get("meets_95_percent") else "，未达到95%"))
        table.add_row("认证", "1", f"{project.auth.auth_type}" +
                       (f" ({project.auth.login_endpoint})" if project.auth.login_endpoint else ""))
        db_detail = "未检测到"
        if project.database:
            db_detail = (
                f"{project.database.db_type}://"
                f"{project.database.host or ''}/"
                f"{project.database.database or ''}"
            )
        table.add_row("数据库", "1" if project.database else "0", db_detail)

        console.print(table)

    def _format_resource_list(self, resources, limit: int = 20) -> str:
        if not resources:
            return "未发现"
        names = []
        for resource in resources[:limit]:
            ops = "/".join(resource.operations) if resource.operations else "unknown"
            marker = "可测" if resource.testable else resource.confidence
            names.append(f"{resource.name}({ops},{marker})")
        suffix = f" ... 等 {len(resources)} 个" if len(resources) > limit else ""
        return ", ".join(names) + suffix
