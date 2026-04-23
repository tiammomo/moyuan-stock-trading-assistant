from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional
import urllib.error
import urllib.request

from app.core.config import get_settings


class WencaiClientError(RuntimeError):
    pass


class WencaiClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def has_api_key(self) -> bool:
        return bool(self.settings.iwencai_api_key.strip())

    def _post_json(self, path: str, payload: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
        if not self.has_api_key:
            raise WencaiClientError("IWENCAI_API_KEY 未配置，无法调用问财开放接口")

        url = f"{self.settings.iwencai_base_url}{path}"
        request = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.settings.iwencai_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            raise WencaiClientError(f"问财接口 HTTP {exc.code}: {body[:200]}") from exc
        except urllib.error.URLError as exc:
            raise WencaiClientError(f"问财接口网络错误: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise WencaiClientError("问财接口返回非 JSON 数据") from exc

    def query2data(
        self,
        query: str,
        *,
        page: int = 1,
        limit: int = 10,
        is_cache: str = "1",
        expand_index: str = "true",
    ) -> Dict[str, Any]:
        started = time.perf_counter()
        result = self._post_json(
            "/v1/query2data",
            {
                "query": query,
                "page": str(page),
                "limit": str(limit),
                "is_cache": is_cache,
                "expand_index": expand_index,
            },
        )
        status_code = result.get("status_code", 0)
        if status_code != 0:
            raise WencaiClientError(result.get("status_msg") or "问财接口返回错误")
        result["_latency_ms"] = int((time.perf_counter() - started) * 1000)
        return result

    def comprehensive_search(
        self,
        channel: str,
        query: str,
        *,
        limit: int = 3,
    ) -> Dict[str, Any]:
        started = time.perf_counter()
        result = self._post_json(
            "/v1/comprehensive/search",
            {
                "channels": [channel],
                "app_id": "AIME_SKILL",
                "query": query,
            },
        )
        status_code = result.get("status_code", 0)
        if status_code != 0:
            raise WencaiClientError(result.get("status_msg") or "问财综合搜索接口返回错误")
        data = result.get("data") or []
        result["data"] = data[:limit] if isinstance(data, list) else []
        result["_latency_ms"] = int((time.perf_counter() - started) * 1000)
        return result


wencai_client = WencaiClient()
