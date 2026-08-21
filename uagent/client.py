import requests
from typing import Optional
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config


class UAgentClient:
    def __init__(self, token: Optional[str] = None, base_url: Optional[str] = None):
        self.base_url = (base_url or config.BASE_URL).rstrip("/")
        if not self.base_url:
            raise ValueError("UAGENT_BASE_URL 未设置，请在 .env 或环境变量中配置平台地址")
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.session.trust_env = False

        raw = token or config.TOKEN
        if raw:
            t = raw[len("Bearer "):] if raw.startswith("Bearer ") else raw
            self._set_token(t)
        elif config.UC_EMAIL and config.UC_PASSWORD_MD5:
            self._auto_login()
        else:
            raise ValueError(
                "需要在 .env 中配置 UAGENT_TOKEN，"
                "或同时配置 UAGENT_EMAIL 和 UAGENT_PASSWORD_MD5"
            )

    def _set_token(self, token: str) -> None:
        self._token = token
        self.session.headers["Authorization"] = f"Bearer {token}"

    def _auto_login(self) -> None:
        """UC 登录两步换取 Agent JWT，自动写回 .env。"""
        if not config.UC_BASE_URL:
            raise ValueError("使用自动登录时必须配置 UC_BASE_URL")
        auth = requests.Session()
        auth.trust_env = False

        # Step 1: UC 登录 → UC JWT (RS256, iss=km)
        uc = auth.post(
            f"{config.UC_BASE_URL}/backend/internal/login",
            json={
                "email": config.UC_EMAIL,
                "password": config.UC_PASSWORD_MD5,
                "type": "U_agent",
            },
            timeout=15,
        )
        uc.raise_for_status()
        uc_jwt = uc.json()["data"]

        # Step 2: UC JWT → Agent JWT (HS256, iss=SELF_HOSTED)
        ag = auth.post(
            f"{self.base_url}/api/backend/login",
            json={},
            headers={"Authorization": f"Bearer {uc_jwt}"},
            timeout=15,
        )
        ag.raise_for_status()
        agent_jwt = ag.json()["data"]["auth"]

        self._set_token(agent_jwt)
        self._persist_token(agent_jwt)

    def _persist_token(self, token: str) -> None:
        """把新 token 写回 .env 文件，方便下次直接用。"""
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        if not os.path.exists(env_path):
            return
        with open(env_path, encoding="utf-8") as f:
            lines = f.readlines()
        new_lines = []
        found = False
        for line in lines:
            if line.startswith("UAGENT_TOKEN="):
                new_lines.append(f"UAGENT_TOKEN=Bearer {token}\n")
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f"UAGENT_TOKEN=Bearer {token}\n")
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        resp = self.session.request(method, f"{self.base_url}{path}", **kwargs)
        if resp.status_code == 401 and config.UC_EMAIL and config.UC_PASSWORD_MD5:
            self._auto_login()
            resp = self.session.request(method, f"{self.base_url}{path}", **kwargs)
        resp.raise_for_status()
        return resp

    def get(self, path: str, params: Optional[dict] = None) -> dict:
        return self._request("GET", path, params=params).json()

    def post(self, path: str, json: Optional[dict] = None) -> dict:
        return self._request("POST", path, json=json or {}).json()

    def delete(self, path: str) -> dict:
        return self._request("DELETE", path).json()

    def post_stream(self, path: str, json: Optional[dict] = None) -> requests.Response:
        resp = self.session.post(
            f"{self.base_url}{path}",
            json=json or {},
            stream=True,
        )
        if resp.status_code == 401 and config.UC_EMAIL and config.UC_PASSWORD_MD5:
            self._auto_login()
            resp = self.session.post(
                f"{self.base_url}{path}",
                json=json or {},
                stream=True,
            )
        resp.raise_for_status()
        return resp
