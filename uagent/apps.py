from .client import UAgentClient


def create_app(
    client: UAgentClient,
    title: str,
    model_type: str = "advanced-chat",
    icon_type: str = "emoji",
    icon: str = "",
    icon_bk: str = "",
    desc: str = "",
) -> dict:
    return client.post("/api/backend/new/apps", {
        "title": title,
        "model_type": model_type,
        "image_icon_type": icon_type,
        "image_icon": icon,
        "image_icon_bk": icon_bk,
        "desc": desc,
    })


def list_apps(
    client: UAgentClient,
    page: int = 1,
    page_size: int = 30,
    name: str = "",
    created_by_me: bool = False,
) -> dict:
    return client.get("/api/backend/new/apps", {
        "page_number": page,
        "page_size": page_size,
        "app_name": name,
        "created_by_me": created_by_me,
    })


def get_app(client: UAgentClient, app_id: str) -> dict:
    return client.get(f"/api/backend/new/apps/{app_id}")


def delete_app(client: UAgentClient, app_id: str) -> dict:
    return client.delete(f"/api/backend/new/apps/{app_id}")
