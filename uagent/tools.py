from .client import UAgentClient


def get_builtin_tools(client: UAgentClient) -> dict:
    return client.get("/api/backend/ws/current/tools/builtin")


def get_wf_tools(client: UAgentClient) -> dict:
    return client.get("/api/backend/ws/current/tools/wf")


def get_api_tools(client: UAgentClient) -> dict:
    return client.get("/api/backend/ws/current/tools/api")
