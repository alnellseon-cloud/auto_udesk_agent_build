from .client import UAgentClient


def get_models(client: UAgentClient, model_type: str = "llm") -> dict:
    return client.get(f"/api/backend/ws/get/models/modelType/{model_type}")


def get_default_model(client: UAgentClient) -> dict:
    return client.get("/api/backend/ws/defaultModel", {"type": "llm"})


from typing import List


def list_model_names(client: UAgentClient) -> List[str]:
    """返回所有可用 LLM 模型名列表。"""
    resp = get_models(client)
    names = []
    for provider in resp.get("data", {}).get("result", []):
        for m in provider.get("models", []):
            names.append(m["model"])
    return names
