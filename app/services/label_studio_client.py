from typing import Any, Dict, Optional

import httpx


class LabelStudioClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Token {self.api_key}"}

    async def create_project(self, name: str, label_config: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=30.0) as client:
            response = await client.post(
                "/api/projects/",
                headers=self._headers(),
                json={"title": name, "label_config": label_config},
            )
            response.raise_for_status()
            data = response.json()

        project_id = data.get("id")
        project_url = data.get("url") or (
            f"{self.base_url}/projects/{project_id}" if project_id else None
        )
        return {"id": project_id, "url": project_url, "raw": data}

    async def create_task(self, project_id: str, payload: Dict[str, Any]) -> str:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=30.0) as client:
            response = await client.post(
                f"/api/projects/{project_id}/tasks/",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        if isinstance(data, list) and data:
            return str(data[0].get("id"))
        return str(data.get("id"))

    async def get_task(self, task_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=30.0) as client:
            response = await client.get(
                f"/api/tasks/{task_id}/",
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    async def get_project_export(self, project_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=60.0) as client:
            response = await client.get(
                f"/api/projects/{project_id}/export",
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    async def register_webhook(self, project_id: str, url: str, secret: str) -> None:
        payload = {"project": project_id, "url": url, "secret": secret}
        async with httpx.AsyncClient(base_url=self.base_url, timeout=30.0) as client:
            response = await client.post(
                "/api/webhooks/",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
