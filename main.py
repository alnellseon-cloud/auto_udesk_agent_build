"""
UAgent 智能工作流搭建工具 —— CLI 入口

用法：
  python main.py build spec.yaml       # 从规范文件部署工作流
  python main.py list                  # 列出所有应用
  python main.py delete <app_id>       # 删除应用
  python main.py test <app_id> <query> # 测试工作流
  python main.py publish <app_id>      # 发布草稿

环境变量（或 .env 文件）：
  UAGENT_TOKEN   UAgent Bearer Token（必须）
"""

import sys
import os
import datetime
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

import config
from uagent.client import UAgentClient
from uagent import apps as apps_api
from uagent import workflow as wf_api
from builder.builder import WorkflowBuilder

console = Console()


def get_client() -> UAgentClient:
    if not config.TOKEN:
        console.print("[red]错误：UAGENT_TOKEN 未设置。请在 .env 文件中配置。[/red]")
        sys.exit(1)
    return UAgentClient()


@click.group()
def cli():
    """UAgent 智能工作流搭建工具"""
    pass


@cli.command()
@click.argument("spec_file")
@click.option("--no-publish", is_flag=True, default=False, help="不自动发布")
@click.option("--app-id", default=None, help="更新已有应用（不新建）")
def build(spec_file, no_publish, app_id):
    """从 YAML/JSON 规范文件部署工作流。"""
    client = get_client()
    builder = WorkflowBuilder(client)

    if not os.path.exists(spec_file):
        console.print(f"[red]文件不存在：{spec_file}[/red]")
        sys.exit(1)

    with console.status(f"[dim]正在部署 {spec_file}...[/dim]"):
        try:
            if app_id:
                import yaml, json
                with open(spec_file, "r", encoding="utf-8") as f:
                    spec = yaml.safe_load(f) if spec_file.endswith((".yaml", ".yml")) else json.load(f)
                result = builder.update(app_id, spec, publish=not no_publish)
                result["app_id"] = app_id
            else:
                result = builder.deploy_from_file(spec_file, publish=not no_publish)
        except Exception as e:
            console.print(f"[red]部署失败：{e}[/red]")
            sys.exit(1)

    console.print(Panel(
        f"[bold green]✓ 部署成功[/bold green]\n"
        f"应用名称：{result.get('title', '')}\n"
        f"app_id：[cyan]{result['app_id']}[/cyan]\n"
        f"已发布：{'是' if result.get('published') else '否'}",
        border_style="green",
    ))


@cli.command(name="list")
@click.option("--name", default="", help="按名称过滤")
def list_apps(name):
    """列出平台上的所有工作流应用。"""
    client = get_client()
    resp = apps_api.list_apps(client, name=name)
    apps = resp.get("data", {}).get("list", [])

    if not apps:
        console.print("[dim]没有找到应用。[/dim]")
        return

    table = Table(title="应用列表", border_style="blue")
    table.add_column("app_id", style="cyan", no_wrap=True)
    table.add_column("名称", style="bold")
    table.add_column("类型")
    table.add_column("创建时间")

    for a in apps:
        ts = datetime.datetime.fromtimestamp(a.get("created_time", 0)).strftime("%Y-%m-%d %H:%M")
        table.add_row(a["app_id"], a["title"], a.get("mode_type", ""), ts)

    console.print(table)


@cli.command()
@click.argument("app_id")
@click.confirmation_option(prompt="确认删除该应用？此操作不可恢复")
def delete(app_id):
    """删除指定应用。"""
    client = get_client()
    try:
        apps_api.delete_app(client, app_id)
        console.print(f"[green]✓ 应用 {app_id} 已删除。[/green]")
    except Exception as e:
        console.print(f"[red]删除失败：{e}[/red]")


@cli.command()
@click.argument("app_id")
@click.argument("query")
@click.option("--dialog-id", default="", help="对话 ID（多轮时传上次返回值）")
def test(app_id, query, dialog_id):
    """测试工作流（发送一条消息并显示结果）。"""
    client = get_client()

    with console.status("[dim]运行中...[/dim]"):
        try:
            events = wf_api.run_preview(client, app_id, query, dialog_id=dialog_id)
        except Exception as e:
            console.print(f"[red]运行失败：{e}[/red]")
            sys.exit(1)

    answer = None
    conversation_id = None
    status = None
    node_results = []

    for ev in events:
        t = ev.get("type")
        if t == "workflow_started":
            conversation_id = ev.get("conversation_id")
        if t == "workflow_finished":
            status = ev.get("data", {}).get("status")
        if t == "node_finished":
            d = ev.get("data", {})
            node_results.append({
                "node": d.get("title", d.get("node_id", "")),
                "type": d.get("node_type", ""),
                "status": d.get("status", ""),
            })
            if d.get("node_type") == "answer":
                answer = d.get("outputs", {}).get("answer", "")

    status_color = "green" if status == "succeeded" else "red"
    console.print(Panel(
        f"[bold]查询：[/bold]{query}\n"
        f"[bold]状态：[/bold][{status_color}]{status or '未知'}[/{status_color}]\n"
        f"[bold]回答：[/bold]{answer or '（无 answer 节点输出）'}\n"
        f"[dim]conversation_id={conversation_id}[/dim]",
        title="运行结果",
        border_style=status_color,
    ))

    if node_results:
        table = Table(title="节点执行情况", border_style="dim")
        table.add_column("节点")
        table.add_column("类型")
        table.add_column("状态")
        for nr in node_results:
            c = "green" if nr["status"] == "succeeded" else "red"
            table.add_row(nr["node"], nr["type"], f"[{c}]{nr['status']}[/{c}]")
        console.print(table)


@cli.command()
@click.argument("app_id")
def publish(app_id):
    """发布工作流草稿为正式版本。"""
    client = get_client()
    try:
        wf_api.publish(client, app_id)
        console.print(f"[green]✓ 应用 {app_id} 已发布。[/green]")
    except Exception as e:
        console.print(f"[red]发布失败：{e}[/red]")


if __name__ == "__main__":
    cli()
