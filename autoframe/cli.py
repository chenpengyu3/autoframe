"""AutoFrame v2 自动化测试框架 - 命令行入口。"""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from autoframe.core.config import load_config
from autoframe.core.context import TestContext
from autoframe.core import logging
from autoframe.reporting.models import TestReport
from autoframe.reporting.collector import ReportCollector
from autoframe.reporting.generator import ReportGenerator
from autoframe.plugins.registry import registry

app = typer.Typer(
    name="autoframe",
    help="AutoFrame v2 - 适用于 Spring Boot 和 Python 项目的自动化测试框架。",
    no_args_is_help=True,
)
console = Console()


@app.command()
def run(
    env: str = typer.Option("dev", help="环境名称 (dev/staging/prod)"),
    config_dir: str = typer.Option("config", help="配置文件目录"),
    modules: Optional[str] = typer.Option(None, "--modules", "-m", help="要运行的模块，逗号分隔"),
    url: Optional[str] = typer.Option(None, "--url", "-u", help="目标服务地址"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="项目源码路径"),
    report_dir: str = typer.Option("reports", help="报告输出目录"),
    no_report: bool = typer.Option(False, "--no-report", help="跳过 HTML 报告生成"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="详细输出"),
):
    """对目标服务运行自动化测试（自动发现一切）。"""
    import os
    logging.header("AutoFrame v2 自动化测试")

    cli_overrides = {}
    if url:
        cli_overrides["service"] = {"base_url": url}
        os.environ["AUTOFRAME_BASE_URL"] = url
    if project:
        cli_overrides["service"] = cli_overrides.get("service", {})
        cli_overrides["service"]["project_path"] = project
        os.environ["AUTOFRAME_PROJECT_PATH"] = project
    if modules:
        cli_overrides["test_suite"] = {"modules": [m.strip() for m in modules.split(",")]}

    config = load_config(env=env, config_dir=config_dir, cli_overrides=cli_overrides)

    logging.info(f"环境: {config.environment}")
    logging.info(f"目标地址: {config.service.base_url}")
    logging.info(f"测试模块: {', '.join(config.test_suite.modules)}")

    context = TestContext(config)
    service_type = context.detect_service_type()
    config.service.type = service_type
    logging.info(f"服务类型: {service_type}")

    # 在运行测试前扫描并获取认证信息
    _scan_and_auth(config, context, os)

    registry.discover()
    enabled = registry.enabled_modules(context)
    if not enabled:
        logging.error("没有启用的测试模块！")
        raise typer.Exit(code=1)

    logging.info(f"已启用模块: {', '.join(m.name for m in enabled)}")

    pytest_args = [
        "-v" if verbose else "-x",
        "--tb=short",
        "-rs",
        "-p", "autoframe.reporting.plugin",
    ]
    from datetime import datetime
    junit_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    junit_path = Path(report_dir) / f"junit_{env}_{junit_timestamp}.xml"
    junit_path.parent.mkdir(parents=True, exist_ok=True)
    pytest_args.append(f"--junitxml={junit_path}")

    test_paths = []
    module_paths = {}
    for module in enabled:
        module_path = Path(__file__).parent / "modules" / module.name
        if not module_path.exists():
            logging.error(f"已启用模块缺少测试目录: {module.name} -> {module_path}")
            raise typer.Exit(code=1)
        test_paths.append(str(module_path))
        module_paths[module.name] = module_path

    if not test_paths:
        logging.error("未找到已启用模块的测试路径！")
        raise typer.Exit(code=1)

    marker_expr = " or ".join(m.name for m in enabled)
    _audit_pytest_collection(module_paths, marker_expr)
    pytest_args.extend(["-m", marker_expr])
    pytest_args.extend(test_paths)

    logging.info(f"正在运行测试...")

    import pytest
    exit_code = pytest.main(pytest_args)

    if not no_report:
        from autoframe.reporting.collector import collector
        report = collector.report
        report.environment = env
        report.service_name = config.service.name
        report.service_type = service_type
        report.service_url = config.service.base_url

        import shutil

        generator = ReportGenerator()
        report_dir_path = Path(report_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = report_dir_path / f"report_{env}_{timestamp}.html"
        report_file = generator.generate(report, output_path)
        latest_file = report_dir_path / f"report_{env}.html"
        shutil.copyfile(report_file, latest_file)
        logging.success(f"报告已生成: {report_file}")
        logging.info(f"最新报告副本: {latest_file}")
        logging.info(f"JUnit XML: {junit_path}")

        try:
            choice = typer.confirm("是否在浏览器中打开报告", default=True)
            if choice:
                _open_report_file(report_file)
                logging.info("已在浏览器中打开报告")
        except (typer.Abort, EOFError, KeyboardInterrupt):
            pass

    logging.header("测试汇总")
    if exit_code == 0:
        logging.success("所有测试通过！")
    else:
        logging.error(f"测试未全部通过（退出码: {exit_code}）")

    raise typer.Exit(code=exit_code)


def _audit_pytest_collection(module_paths: dict[str, Path], marker_expr: str):
    """Verify enabled modules are actually collected by pytest."""
    import subprocess

    command = [
        sys.executable,
        "-m",
        "pytest",
        "--collect-only",
        "-q",
        "-m",
        marker_expr,
        *[str(path) for path in module_paths.values()],
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        logging.error("测试收集预检失败，pytest 无法收集测试用例")
        if result.stdout:
            logging.error(result.stdout.strip())
        if result.stderr:
            logging.error(result.stderr.strip())
        raise typer.Exit(code=1)

    counts = {name: 0 for name in module_paths}
    total = 0
    for line in result.stdout.splitlines():
        nodeid = line.strip().replace("\\", "/")
        if "::" not in nodeid:
            continue
        for name in counts:
            if f"/modules/{name}/" in nodeid:
                counts[name] += 1
                total += 1
                break

    missing = [name for name, count in counts.items() if count == 0]
    if missing:
        logging.error("以下已启用模块没有被 pytest 收集到任何测试: " + ", ".join(missing))
        raise typer.Exit(code=1)

    detail = ", ".join(f"{name}:{count}" for name, count in counts.items())
    logging.success(f"测试收集预检通过: 共 {total} 个测试用例")
    logging.info(f"模块测试数: {detail}")


def _scan_and_auth(config, context, os):
    """扫描项目并在需要时提示用户输入认证信息。"""
    from autoframe.scanner.pipeline import ScanPipeline

    # 如果没有提供项目路径，提示用户是否要输入数据库信息
    if not config.service.project_path:
        logging.info("提示：提供 --project 参数可以自动发现数据库配置")
        try:
            choice = typer.prompt(
                "\n是否手动输入数据库连接信息？\n"
                "  1 - 输入数据库连接信息\n"
                "  2 - 跳过（数据库测试将被跳过）\n"
                "请选择",
                default="2"
            )
            if choice == "1":
                db_type = typer.prompt("数据库类型", default="mysql")
                db_host = typer.prompt("数据库地址", default="127.0.0.1")
                db_port = typer.prompt("数据库端口", default="3306")
                db_name = typer.prompt("数据库名称")
                db_user = typer.prompt("数据库用户名")
                db_password = typer.prompt("数据库密码", hide_input=True)

                if db_type == "mysql":
                    db_url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
                elif db_type == "postgresql":
                    db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
                else:
                    db_url = f"{db_type}://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

                os.environ["AUTOFRAME_DB_URL"] = db_url
                logging.success("已设置数据库连接信息")
        except (typer.Abort, EOFError, KeyboardInterrupt):
            logging.info("跳过数据库配置")

    pipeline = ScanPipeline(
        base_url=config.service.base_url,
        project_path=config.service.project_path,
        project_type=context.service_type,
    )

    # 运行扫描
    logging.info("正在扫描项目...")
    project = pipeline.run()

    # 检查是否需要认证
    if project.auth.acquisition_failed and project.auth.login_endpoint:
        logging.warning(f"发现登录端点: {project.auth.login_endpoint}，但未能自动获取令牌")

        try:
            choice = typer.prompt(
                "\n是否提供认证信息？\n"
                "  1 - 直接输入 Token\n"
                "  2 - 输入用户名和密码登录\n"
                "  3 - 跳过（跳过需要认证的测试）\n"
                "请选择",
                default="3"
            )

            if choice == "1":
                token = typer.prompt("请输入 Token")
                if token:
                    os.environ["AUTOFRAME_AUTH_TOKEN"] = token
                    logging.success("已设置 Token")

            elif choice == "2":
                username = typer.prompt("请输入用户名")
                password = typer.prompt("请输入密码", hide_input=True)

                # 尝试登录
                import httpx
                login_url = f"{config.service.base_url.rstrip('/')}{project.auth.login_endpoint}"
                login_bodies = [
                    {"username": username, "password": password},
                    {"email": username, "password": password},
                    {"account": username, "password": password},
                ]

                for body in login_bodies:
                    try:
                        resp = httpx.post(login_url, json=body, timeout=5.0)
                        if resp.status_code in (200, 201):
                            data = resp.json()
                            token = _extract_token(data)
                            if token:
                                os.environ["AUTOFRAME_AUTH_TOKEN"] = token
                                logging.success("登录成功！Token 已获取")
                                return
                    except Exception:
                        continue

                logging.error("登录失败，请检查用户名和密码")

            else:
                logging.info("跳过认证，需要认证的测试将被跳过")

        except (typer.Abort, EOFError, KeyboardInterrupt):
            logging.info("跳过认证")


def _extract_token(data: dict):
    """从登录响应中提取 token。"""
    token_fields = ["token", "access_token", "jwt", "accessToken", "data.token", "result.token"]
    for field_path in token_fields:
        value = data
        for key in field_path.split("."):
            if isinstance(value, dict):
                value = value.get(key)
            else:
                value = None
                break
        if isinstance(value, str) and len(value) > 10:
            return value
    return None


def _open_report_file(report_file):
    """Open a generated report using the most reliable local method."""
    import os
    import webbrowser

    report_path = Path(report_file).resolve()
    try:
        if os.name == "nt":
            os.startfile(str(report_path))  # type: ignore[attr-defined]
            return
    except Exception as exc:
        logging.warning(f"系统默认方式打开报告失败: {exc}")

    opened = webbrowser.open(report_path.as_uri(), new=2)
    if not opened:
        logging.warning(f"浏览器未自动打开，请手动打开报告: {report_path}")


@app.command()
def scan(
    url: Optional[str] = typer.Option(None, "--url", "-u", help="要扫描的服务地址"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="项目源码路径"),
):
    """扫描项目/服务，展示发现的端点、资源、认证、数据库信息。"""
    from autoframe.scanner.pipeline import ScanPipeline

    if not url:
        logging.error("请提供 --url 参数以扫描目标服务")
        raise typer.Exit(code=1)

    logging.header("AutoFrame 扫描器")
    pipeline = ScanPipeline(base_url=url, project_path=project)
    project = pipeline.run()

    logging.info(f"\n发现 {len(project.endpoints)} 个端点:")
    for ep in project.endpoints:
        logging.info(f"  {', '.join(ep.methods)} {ep.path} (来源: {ep.source})")

    testable_resources = [r for r in project.resources if r.testable]
    logging.info(
        f"\n发现 {len(project.resources)} 个 CRUD 候选资源，"
        f"{len(testable_resources)} 个生命周期候选:"
    )
    for r in project.resources:
        ops = "/".join(r.operations) if r.operations else "unknown"
        marker = "可测" if r.testable else r.confidence
        logging.info(f"  {r.name}: {ops} ({marker})")

    if project.auth.auth_type != "none":
        logging.info(f"\n认证方式: {project.auth.auth_type}，登录端点: {project.auth.login_endpoint}")

    if project.database:
        logging.info(f"\n数据库: {project.database.db_type} @ {project.database.host}:{project.database.port}/{project.database.database}")


@app.command("export")
def export_inventory(
    url: Optional[str] = typer.Option(None, "--url", "-u", help="Target service URL"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project source path"),
    output_dir: str = typer.Option("reports/inventory", "--output-dir", "-o", help="Scan export directory"),
    formats: str = typer.Option("json,openapi,postman,markdown", "--formats", help="Comma-separated export formats"),
):
    """Scan and export discovered inventory as JSON, OpenAPI, Postman, and Markdown."""
    from autoframe.reporting.exporters import export_project_inventory
    from autoframe.scanner.pipeline import ScanPipeline

    if not url:
        logging.error("Please provide --url for the target service")
        raise typer.Exit(code=1)

    logging.header("AutoFrame Inventory Export")
    pipeline = ScanPipeline(base_url=url, project_path=project)
    discovered = pipeline.run()
    written = export_project_inventory(
        discovered,
        output_dir,
        formats=[item.strip() for item in formats.split(",")],
        project_path=project,
    )

    logging.success(f"Exported inventory to: {Path(output_dir).resolve()}")
    for name, path in written.items():
        logging.info(f"  {name}: {path}")


@app.command()
def detect(
    url: str = typer.Argument(..., help="要检测的服务地址"),
):
    """检测运行中服务的类型。"""
    from autoframe.utils.service_detector import detect_service_type

    logging.info(f"正在检测服务类型: {url}")
    service_type = detect_service_type(url)

    if service_type == "spring_boot":
        logging.success("检测到: Spring Boot")
    elif service_type == "python":
        logging.success("检测到: Python (Flask/FastAPI)")
    else:
        logging.warning("无法确定服务类型")

    typer.echo(service_type)


@app.command()
def report(
    input_file: str = typer.Option(..., "--input", "-i", help="测试结果 JSON 文件路径"),
    output_dir: str = typer.Option("reports", help="报告输出目录"),
):
    """从已有测试结果生成 HTML 报告。"""
    import json

    logging.info(f"正在加载测试结果: {input_file}")

    with open(input_file, encoding="utf-8") as f:
        data = json.load(f)

    report_obj = TestReport()
    generator = ReportGenerator()
    output_path = Path(output_dir) / "report.html"
    generator.generate(report_obj, output_path)
    logging.success(f"报告已生成: {output_path}")


@app.command()
def list_modules():
    """列出所有可用的测试模块。"""
    registry.discover()
    modules = registry.all_modules()

    if not modules:
        logging.warning("未找到任何模块")
        return

    from rich.table import Table
    table = Table(title="可用测试模块")
    table.add_column("名称", style="cyan")
    table.add_column("说明", style="white")
    table.add_column("标记", style="green")

    for module in modules:
        table.add_row(module.name, module.description, module.marker)

    console.print(table)


if __name__ == "__main__":
    app()
