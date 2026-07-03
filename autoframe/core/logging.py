"""结构化日志输出，带 rich 格式化。"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()


def info(message: str, title: str = ""):
    if title:
        console.print(Panel(message, title=title, border_style="blue"))
    else:
        console.print(f"[blue]信息[/blue] {message}")


def success(message: str):
    console.print(f"[green]通过[/green] {message}")


def warning(message: str):
    console.print(f"[yellow]警告[/yellow] {message}")


def error(message: str):
    console.print(f"[red]失败[/red] {message}")


def header(title: str):
    console.print()
    console.rule(f"[bold cyan]{title}[/bold cyan]")


def module_start(module_name: str):
    console.print()
    console.print(f"[bold magenta]▶ 正在运行模块: {module_name}[/bold magenta]")
    console.print(f"{'─' * 60}")


def module_result(module_name: str, passed: int, failed: int, skipped: int = 0):
    total = passed + failed + skipped
    status = "[green]通过[/green]" if failed == 0 else "[red]失败[/red]"
    table = Table(box=box.SIMPLE, show_header=False)
    table.add_column("项目", style="bold")
    table.add_column("结果")
    table.add_row("模块", module_name)
    table.add_row("状态", status)
    table.add_row("通过", str(passed))
    table.add_row("失败", str(failed) if failed else "0")
    if skipped:
        table.add_row("跳过", str(skipped))
    table.add_row("总计", str(total))
    console.print(table)


def test_result(name: str, passed: bool, duration_ms: float = 0, detail: str = ""):
    status = "[green]✓[/green]" if passed else "[red]✗[/red]"
    duration_str = f" ({duration_ms:.1f}ms)" if duration_ms > 0 else ""
    msg = f"  {status} {name}{duration_str}"
    if detail and not passed:
        msg += f"\n    [dim]{detail}[/dim]"
    console.print(msg)
