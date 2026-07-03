"""HTML report generator using Jinja2."""

import json
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from autoframe.reporting.models import TestReport

TEST_DESCRIPTIONS = {
    "test_service_is_alive": "验证目标服务是否正常响应",
    "test_health_endpoint": "检测健康检查端点",
    "test_configured_endpoints_reachable": "遍历所有已发现的 API 端点，验证可达性",
    "test_response_time_acceptable": "验证所有端点的响应时间在阈值内",
    "test_404_for_nonexistent_path": "验证不存在的路径返回 404",
    "test_crud_lifecycle": "对所有已发现资源执行完整 CRUD 生命周期",
    "test_response_schemas_valid": "校验 API 响应的 JSON 结构",
    "test_json_response_format": "验证所有 GET 端点返回合法 JSON",
    "test_concurrent_writes_consistency": "并发写入验证数据一致性",
    "test_concurrent_create_no_duplicates": "并发创建验证 ID 唯一性",
    "test_concurrent_reads_consistent": "并发读取验证数据一致",
    "test_shared_client_thread_safety": "验证共享客户端线程安全",
    "test_concurrent_get_requests": "模拟并发 GET 请求",
    "test_concurrent_mixed_methods": "并发发送不同 HTTP 方法",
    "test_request_isolation": "验证并发请求状态隔离",
    "test_connection_established": "验证数据库连接",
    "test_connection_pool_size": "验证连接池并发处理",
    "test_connection_recovery": "验证连接恢复能力",
    "test_concurrent_transactions": "验证并发事务隔离",
    "test_simple_query_performance": "验证简单查询性能",
    "test_repeated_query_performance": "验证重复查询一致性",
    "test_database_tables_exist": "验证数据表存在",
    "test_table_has_primary_key": "验证主键定义",
    "test_foreign_key_constraints": "验证外键约束",
    "test_not_null_constraints": "验证 NOT NULL 约束",
    "test_unauthenticated_access_denied": "验证未认证请求被拒绝",
    "test_invalid_token_rejected": "验证无效 Token 被拒绝",
    "test_expired_token_rejected": "验证过期 Token 被拒绝",
    "test_required_security_headers": "检查安全头信息",
    "test_no_server_info_leakage": "检测服务器信息泄露",
    "test_cors_headers_safe": "验证 CORS 头安全性",
    "test_sql_injection_in_query_params": "SQL 注入检测（查询参数）",
    "test_sql_injection_in_path": "SQL 注入检测（URL 路径）",
    "test_xss_in_reflected_response": "XSS 漏洞检测",
    "test_xss_in_json_response": "JSON XSS 检测",
    "test_service_survives_rapid_requests": "快速请求服务稳定性",
    "test_service_recovers_after_errors": "错误后服务恢复",
    "test_reconnection_after_connection_drop": "连接断开后重连",
    "test_health_endpoint_resilience": "健康检查端点稳定性",
    "test_graceful_error_responses": "规范错误响应",
    "test_service_responds_within_timeout": "超时时间内响应",
    "test_timeout_returns_error_not_hang": "超时返回错误而非挂起",
    "test_concurrent_timeouts_handled": "并发超时处理",
    "test_response_time_benchmark": "响应时间基准测试",
    "test_no_server_errors": "无服务器错误",
    "test_sustained_load": "持续负载测试",
    "test_staged_stress": "阶梯压力测试",
    "test_throughput_meets_minimum": "吞吐量达标测试",
    "test_invalid_query_values_do_not_server_error": "无效查询参数不应导致服务器错误",
    "test_templated_id_paths_reject_invalid_ids_cleanly": "模板 ID 路径应优雅处理非法 ID",
    "test_malformed_json_write_endpoints_do_not_server_error": "畸形 JSON 请求不应导致服务器错误",
    "test_openapi_spec_has_paths_when_available": "OpenAPI 文档存在时必须包含 paths",
    "test_openapi_operations_are_discovered": "OpenAPI 操作应被扫描器发现",
    "test_openapi_operations_declare_success_responses": "OpenAPI 操作应声明成功响应",
    "test_common_debug_endpoints_are_not_public": "常见调试端点不应公开",
    "test_error_pages_do_not_expose_stack_traces": "错误页面不应暴露堆栈信息",
    "test_public_responses_do_not_expose_secret_patterns": "公开响应不应暴露敏感模式",
    "test_head_on_get_endpoints_no_server_error": "GET 端点的 HEAD 请求不应导致服务器错误",
    "test_accept_header_variants_do_not_server_error": "不同 Accept 头不应导致服务器错误",
    "test_options_on_discovered_paths_no_server_error": "OPTIONS 探测不应导致服务器错误",
    "test_download_endpoints_are_binary_contracts": "下载端点应具备二进制响应契约",
    "test_multipart_endpoints_are_not_plain_json_targets": "上传端点不应被当作普通 JSON 接口调用",
    "test_file_like_endpoints_are_classified": "文件类端点应被正确分类",
    "test_health_endpoints_are_fast_and_stable": "健康端点应快速稳定",
    "test_operational_headers_do_not_leak_sensitive_values": "运行时响应头不应泄露敏感信息",
    "test_error_response_shape_is_stable": "错误响应结构应稳定",
    "test_openapi_docs_endpoint_behavior": "OpenAPI 文档端点行为检查",
    "test_swagger_ui_paths_do_not_server_error": "Swagger UI 路径不应导致服务器错误",
    "test_documentation_endpoints_are_not_accidentally_public": "文档端点公开状态检查",
    "test_no_duplicate_method_path_pairs": "扫描结果不应包含重复方法路径",
    "test_endpoint_paths_are_normalized": "API 路径格式应规范",
    "test_http_methods_are_known": "HTTP 方法应为已知类型",
    "test_endpoint_kinds_are_known": "端点类型应为已知分类",
    "test_cache_control_headers_are_parseable_when_present": "Cache-Control 存在时应可解析",
    "test_conditional_get_headers_do_not_server_error": "条件 GET 请求不应导致服务器错误",
    "test_gzip_accept_encoding_does_not_server_error": "压缩协商不应导致服务器错误",
    "test_path_traversal_query_params_do_not_leak_files": "路径穿越参数不应泄露文件",
    "test_sensitive_static_files_are_not_public": "敏感静态配置文件不应公开",
    "test_tables_have_columns": "数据表应能发现列信息",
    "test_tables_have_reasonable_column_names": "数据库列名应规范",
    "test_large_tables_have_primary_keys": "较大数据表应具备主键",
    "test_non_heavy_responses_are_reasonably_sized": "非重型接口响应体大小应合理",
    "test_repeated_light_endpoint_latency_is_stable": "轻量接口重复请求延迟应稳定",
    "test_project_source_path_is_accessible": "项目源码路径应可访问",
    "test_build_or_dependency_manifest_exists": "应存在构建或依赖清单",
    "test_source_config_files_do_not_expose_plaintext_secrets": "源码配置文件不应暴露明文敏感项",
    "test_ci_or_container_metadata_is_detected_when_present": "识别 CI 或容器化元数据",
    "test_endpoint_discovery_matrix": "逐端点扫描矩阵校验",
    "test_safe_get_endpoint_runtime_matrix": "逐安全 GET 端点运行时校验",
    "test_special_endpoint_matrix": "逐特殊端点分类矩阵校验",
    "test_crud_candidate_matrix": "逐 CRUD 候选资源矩阵校验",
    "test_endpoint_method_matrix": "逐端点 HTTP 方法矩阵校验",
    "test_endpoint_path_contract_matrix": "逐端点路径契约矩阵校验",
    "test_endpoint_media_contract_matrix": "逐端点媒体类型契约矩阵校验",
    "test_endpoint_auth_metadata_matrix": "逐端点认证元数据矩阵校验",
    "test_endpoint_parameter_matrix": "逐端点参数矩阵校验",
    "test_endpoint_template_path_matrix": "逐模板路径矩阵校验",
    "test_endpoint_request_schema_matrix": "逐写接口请求体契约矩阵校验",
    "test_endpoint_request_field_matrix": "逐请求字段矩阵校验",
    "test_safe_get_header_variant_runtime_matrix": "逐安全 GET 请求头变体运行时矩阵校验",
    "test_crud_operation_matrix": "逐 CRUD 操作矩阵校验",
    "test_source_file_inventory_matrix": "逐源码文件清单矩阵校验",
    "test_java_package_declaration_matrix": "逐 Java 文件包声明矩阵校验",
    "test_java_type_declaration_matrix": "逐 Java 类型声明矩阵校验",
    "test_spring_component_annotation_matrix": "逐 Spring 组件注解矩阵校验",
    "test_route_annotation_source_matrix": "逐源码路由注解矩阵校验",
    "test_config_property_matrix": "逐配置属性矩阵校验",
    "test_dependency_manifest_matrix": "逐依赖清单项矩阵校验",
    "test_database_table_inventory_matrix": "逐数据库表矩阵校验",
    "test_database_column_inventory_matrix": "逐数据库字段矩阵校验",
    "test_database_primary_key_matrix": "逐数据库主键矩阵校验",
    "test_database_foreign_key_matrix": "逐数据库外键矩阵校验",
    "test_database_index_matrix": "逐数据库索引矩阵校验",
    "test_database_unique_constraint_matrix": "逐数据库唯一约束矩阵校验",
    "test_database_string_column_matrix": "逐字符串字段矩阵校验",
    "test_database_numeric_column_matrix": "逐数值字段矩阵校验",
    "test_database_temporal_column_matrix": "逐时间字段矩阵校验",
    "test_external_tool_command_is_usable_when_available": "外部测试工具可用性检查",
    "test_external_tool_metadata_is_documented": "外部测试工具元数据检查",
    "test_spring_controller_matrix": "逐 Spring Controller 矩阵校验",
    "test_spring_route_method_matrix": "逐 Spring 路由方法矩阵校验",
    "test_spring_service_matrix": "逐 Spring Service/Component 矩阵校验",
    "test_spring_repository_matrix": "逐 Spring Repository 矩阵校验",
    "test_spring_entity_matrix": "逐 JPA Entity 矩阵校验",
    "test_spring_entity_field_matrix": "逐 JPA 字段矩阵校验",
    "test_spring_transactional_method_matrix": "逐事务方法矩阵校验",
    "test_spring_scheduled_method_matrix": "逐定时任务方法矩阵校验",
    "test_spring_injection_matrix": "逐依赖注入点矩阵校验",
}

MODULE_DESCRIPTIONS = {
    "api": "API 功能测试 — 端点可用性、响应格式、CRUD 操作",
    "concurrency": "并发测试 — 竞态条件、线程安全、并发处理",
    "database": "数据库测试 - 连接池、查询性能、数据完整性",
    "database_matrix": "数据库矩阵 - 按表、字段、主键、外键、索引、唯一约束动态展开测试",
    "ecosystem": "生态集成 - Schemathesis、k6、ZAP、RESTler、Docker、Java、Python 工具链可选集成检查",
    "contract": "契约测试 - OpenAPI、Schema、扫描一致性",
    "security": "安全测试 — SQL 注入、XSS、认证绕过、安全头",
    "dast": "动态安全基线 — 调试端点、堆栈泄露、敏感响应",
    "source_quality": "源码质量 - 构建清单、配置卫生、CI/容器元数据",
    "source_matrix": "源码矩阵 - 按源码文件、类型、路由注解、配置属性、依赖项动态展开测试",
    "spring_matrix": "Spring 矩阵 - 按 Controller、Service、Repository、Entity、路由方法、事务和定时任务动态展开测试",
    "endpoint_matrix": "端点矩阵 - 按端点/资源动态展开测试",
    "fault_tolerance": "容错测试 — 超时处理、优雅降级、故障恢复",
    "performance": "性能测试 — 负载测试、压力测试、响应时间",
    "validation": "输入校验测试 — 非法参数、非法 ID、畸形 JSON",
    "compatibility": "协议兼容测试 — HEAD、OPTIONS、Accept 头兼容性",
    "files": "文件接口测试 — 上传、下载、二进制响应契约",
    "observability": "可观测性测试 — 健康检查、错误响应、运行时信号",
    "documentation": "接口文档测试 — OpenAPI、Swagger UI、文档暴露检查",
}


def _get_test_description(test_name: str, fallback: str = "") -> str:
    if test_name in TEST_DESCRIPTIONS:
        return TEST_DESCRIPTIONS[test_name]
    bracket_idx = test_name.find("[")
    if bracket_idx > 0:
        base_name = test_name[:bracket_idx]
        if base_name in TEST_DESCRIPTIONS:
            return TEST_DESCRIPTIONS[base_name]
    return fallback or test_name


class ReportGenerator:
    def __init__(self, template_dir: str | Path | None = None):
        if template_dir is None:
            template_dir = Path(__file__).parent / "templates"
        self.template_dir = Path(template_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=True,
        )

    def generate(self, report: TestReport, output_path: str | Path) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        template = self.env.get_template("report.html")

        for m in report.modules:
            m.name_cn = MODULE_DESCRIPTIONS.get(m.name, m.name).split("—")[0].strip()
            for tc in m.test_cases:
                tc.name_cn = _get_test_description(tc.name, tc.description)

        modules_data = []
        for m in report.modules:
            modules_data.append({
                "name": m.name,
                "name_cn": MODULE_DESCRIPTIONS.get(m.name, m.name).split("—")[0].strip(),
                "description": MODULE_DESCRIPTIONS.get(m.name, ""),
                "passed": m.passed, "failed": m.failed,
                "skipped": m.skipped, "errors": m.errors,
                "total": m.total, "pass_rate": round(m.pass_rate, 1),
                "duration_ms": round(m.duration_ms, 1),
                "duration_s": round(m.duration_ms / 1000, 2),
                "test_cases": [
                    {
                        "name": tc.name,
                        "name_cn": _get_test_description(tc.name, tc.description),
                        "status": tc.status, "duration_ms": round(tc.duration_ms, 1),
                        "error_message": tc.error_message,
                        "error_traceback": tc.error_traceback,
                    }
                    for tc in m.test_cases
                ],
            })

        all_tests = []
        for m in report.modules:
            for tc in m.test_cases:
                all_tests.append({
                    "name": tc.name,
                    "name_cn": _get_test_description(tc.name, tc.description),
                    "module": m.name,
                    "module_cn": MODULE_DESCRIPTIONS.get(m.name, m.name).split("—")[0].strip(),
                    "status": tc.status, "duration_ms": round(tc.duration_ms, 1),
                    "error_message": tc.error_message,
                })

        module_names = [MODULE_DESCRIPTIONS.get(m.name, m.name).split("—")[0].strip() for m in report.modules]
        module_rates = [round(m.pass_rate, 1) for m in report.modules]
        module_durations = [round(m.duration_ms / 1000, 2) for m in report.modules]

        status_counts = {"passed": 0, "failed": 0, "skipped": 0, "error": 0}
        for t in all_tests:
            status_counts[t["status"]] = status_counts.get(t["status"], 0) + 1

        html = template.render(
            report=report,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            modules_json=json.dumps(modules_data, ensure_ascii=False),
            all_tests_json=json.dumps(all_tests, ensure_ascii=False),
            module_labels=json.dumps(module_names, ensure_ascii=False),
            module_passed=json.dumps([m.passed for m in report.modules]),
            module_failed=json.dumps([m.failed for m in report.modules]),
            module_skipped=json.dumps([m.skipped for m in report.modules]),
            module_rates=json.dumps(module_rates),
            module_durations=json.dumps(module_durations),
            latency_labels=json.dumps(["平均", "P50", "P90", "P99", "最大"]),
            latency_values=json.dumps([
                round(report.performance.avg_response_time_ms, 1),
                round(report.performance.p50_response_time_ms, 1),
                round(report.performance.p90_response_time_ms, 1),
                round(report.performance.p99_response_time_ms, 1),
                round(report.performance.max_response_time_ms, 1),
            ]),
            distribution=json.dumps(report.performance.response_time_distribution),
            status_counts=json.dumps(status_counts),
        )

        output_path.write_text(html, encoding="utf-8")
        return output_path
