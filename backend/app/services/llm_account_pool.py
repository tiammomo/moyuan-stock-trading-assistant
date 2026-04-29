from __future__ import annotations

from dataclasses import dataclass, field
import json
from threading import Lock
from typing import Any, Callable, Dict, List, Protocol

from app.core.config import get_settings


@dataclass(frozen=True)
class LLMAccount:
    account_id: str
    provider_family: str
    base_url: str
    auth_token: str
    model: str
    timeout_seconds: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class LLMAccountPoolAdapter(Protocol):
    name: str

    def list_accounts(self, provider_family: str) -> List[LLMAccount]: ...


class UnsupportedLLMAccountPoolAdapterError(ValueError):
    pass


class EnvLLMAccountPoolAdapter:
    name = "env"

    def __init__(self) -> None:
        self.settings = get_settings()

    def list_accounts(self, provider_family: str) -> List[LLMAccount]:
        if provider_family == "openai":
            pool = self._parse_pool_json(
                provider_family="openai",
                raw_json=self.settings.openai_account_pool_json,
                default_base_url=self.settings.openai_base_url,
                default_model=self.settings.openai_model,
                default_timeout=self.settings.openai_timeout_seconds,
            )
            if pool:
                return pool
            if self.settings.openai_api_key.strip() and self.settings.openai_model.strip():
                return [
                    LLMAccount(
                        account_id="openai-default",
                        provider_family="openai",
                        base_url=self.settings.openai_base_url,
                        auth_token=self.settings.openai_api_key,
                        model=self.settings.openai_model,
                        timeout_seconds=self.settings.openai_timeout_seconds,
                    )
                ]
            return []

        if provider_family == "anthropic":
            pool = self._parse_pool_json(
                provider_family="anthropic",
                raw_json=self.settings.anthropic_account_pool_json,
                default_base_url=self.settings.anthropic_base_url,
                default_model=self.settings.anthropic_model,
                default_timeout=self.settings.anthropic_timeout_seconds,
            )
            if pool:
                return pool
            if (
                self.settings.anthropic_base_url.strip()
                and self.settings.anthropic_auth_token.strip()
                and self.settings.anthropic_model.strip()
            ):
                return [
                    LLMAccount(
                        account_id="anthropic-default",
                        provider_family="anthropic",
                        base_url=self.settings.anthropic_base_url,
                        auth_token=self.settings.anthropic_auth_token,
                        model=self.settings.anthropic_model,
                        timeout_seconds=self.settings.anthropic_timeout_seconds,
                    )
                ]
            return []

        return []

    def _parse_pool_json(
        self,
        *,
        provider_family: str,
        raw_json: str,
        default_base_url: str,
        default_model: str,
        default_timeout: int,
    ) -> List[LLMAccount]:
        text = raw_json.strip()
        if not text:
            return []
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return []
        if not isinstance(payload, list):
            return []

        accounts: List[LLMAccount] = []
        for index, item in enumerate(payload, start=1):
            if not isinstance(item, dict):
                continue
            if item.get("enabled") is False:
                continue

            account_id = str(
                item.get("account_id")
                or item.get("id")
                or item.get("name")
                or f"{provider_family}-{index}"
            ).strip()
            base_url = str(item.get("base_url") or default_base_url or "").strip().rstrip("/")
            auth_token = str(
                item.get("auth_token")
                or item.get("api_key")
                or item.get("token")
                or ""
            ).strip()
            model = str(item.get("model") or default_model or "").strip()
            timeout_value = item.get("timeout_seconds", default_timeout)
            try:
                timeout_seconds = int(timeout_value)
            except (TypeError, ValueError):
                timeout_seconds = default_timeout

            if not account_id or not base_url or not auth_token or not model:
                continue

            metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
            accounts.append(
                LLMAccount(
                    account_id=account_id,
                    provider_family=provider_family,
                    base_url=base_url,
                    auth_token=auth_token,
                    model=model,
                    timeout_seconds=timeout_seconds,
                    metadata=metadata,
                )
            )
        return accounts


class RoundRobinAccountPool:
    def __init__(self, adapter: LLMAccountPoolAdapter) -> None:
        self.adapter = adapter
        self._next_index: Dict[str, int] = {}
        self._lock = Lock()

    @property
    def adapter_name(self) -> str:
        return self.adapter.name

    def has_accounts(self, provider_family: str) -> bool:
        return bool(self.adapter.list_accounts(provider_family))

    def account_count(self, provider_family: str) -> int:
        return len(self.adapter.list_accounts(provider_family))

    def ordered_accounts(self, provider_family: str) -> List[LLMAccount]:
        accounts = self.adapter.list_accounts(provider_family)
        if len(accounts) <= 1:
            return accounts

        with self._lock:
            start = self._next_index.get(provider_family, 0) % len(accounts)
            self._next_index[provider_family] = (start + 1) % len(accounts)

        return accounts[start:] + accounts[:start]


class LLMAccountPoolAdapterFactory:
    _registry: Dict[str, Callable[[], LLMAccountPoolAdapter]] = {
        "env": EnvLLMAccountPoolAdapter,
    }

    @classmethod
    def register(cls, name: str, builder: Callable[[], LLMAccountPoolAdapter]) -> None:
        normalized_name = name.strip().lower()
        if not normalized_name:
            raise UnsupportedLLMAccountPoolAdapterError("账号池适配器名称不能为空")
        cls._registry[normalized_name] = builder

    @classmethod
    def create(cls, name: str) -> LLMAccountPoolAdapter:
        normalized_name = (name or "env").strip().lower()
        builder = cls._registry.get(normalized_name)
        if builder is None:
            supported = ", ".join(sorted(cls._registry))
            raise UnsupportedLLMAccountPoolAdapterError(
                f"不支持的 LLM 账号池适配器: {normalized_name}；当前支持: {supported}"
            )
        return builder()

    @classmethod
    def supported_names(cls) -> List[str]:
        return sorted(cls._registry)


def build_llm_account_pool() -> RoundRobinAccountPool:
    settings = get_settings()
    adapter = LLMAccountPoolAdapterFactory.create(settings.llm_account_pool_adapter)
    return RoundRobinAccountPool(adapter)


llm_account_pool = build_llm_account_pool()
