import json
from typing import Optional
from .client import UAgentClient


def get_design(client: UAgentClient, app_id: str) -> dict:
    return client.get(f"/api/backend/new/apps/{app_id}/wf/design")


def save_design(
    client: UAgentClient,
    app_id: str,
    nodes: list,
    edges: list,
    feature: Optional[dict] = None,
    env_var: Optional[list] = None,
    con_var: Optional[list] = None,
    viewport: Optional[dict] = None,
    uuid: Optional[str] = None,
) -> dict:
    payload = {
        "grap": {
            "nodes": nodes,
            "edges": edges,
            "viewport": viewport or {"x": 0, "y": 0, "zoom": 1},
        },
        "feature": feature or {"retriever_resource": {"enabled": True}},
        "env_var": env_var or [],
        "con_var": con_var or [],
    }
    if uuid:
        payload["uuid"] = uuid
    return client.post(f"/api/backend/new/apps/{app_id}/wf/design", payload)


def get_default_config(client: UAgentClient, app_id: str) -> dict:
    return client.get(f"/api/backend/new/apps/{app_id}/wf/defaultConfig")


def get_publish(client: UAgentClient, app_id: str) -> dict:
    return client.get(f"/api/backend/new/apps/{app_id}/wf/publish")


def publish(client: UAgentClient, app_id: str) -> dict:
    return client.post(f"/api/backend/new/apps/{app_id}/wf/publish")


def run_preview(
    client: UAgentClient,
    app_id: str,
    query: str,
    dialog_id: str = "",
    inputs: Optional[dict] = None,
) -> list:
    """运行工作流预览，解析 SSE 流，返回事件列表。"""
    resp = client.post_stream(
        f"/api/backend/new/apps/{app_id}/advancedChat/wf/design/run",
        {"query_content": query, "dialog_id": dialog_id, "input": inputs or {}, "file": []},
    )
    events = []
    for raw_line in resp.iter_lines():
        if not raw_line:
            continue
        line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass
    return events


def get_run(client: UAgentClient, app_id: str, run_id: str) -> dict:
    return client.get(f"/api/backend/new/apps/{app_id}/wfRuns/{run_id}")


def get_node_executions(client: UAgentClient, app_id: str, run_id: str) -> dict:
    return client.get(f"/api/backend/new/apps/{app_id}/wfRuns/{run_id}/nodeExecutions")
