from __future__ import annotations

from dataclasses import dataclass
import json
import socket
from typing import Any, Dict, List, Optional, Protocol
import urllib.error
import urllib.request

from app.core.config import get_settings

from .llm_account_pool import LLMAccount, llm_account_pool


class LLMProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class LLMRequest:
    system_prompt: str
    user_prompt: str
    reasoning_effort: Optional[str] = None
    max_output_tokens: int = 1200


@dataclass(frozen=True)
class LLMTextResult:
    provider: str
    text: str


class LLMProvider(Protocol):
    name: str

    @property
    def enabled(self) -> bool: ...

    def generate_text(self, request: LLMRequest) -> str: ...


class BaseJSONLLMProvider:
    name: str = "base"
    provider_family: str = "base"

    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def enabled(self) -> bool:
        return llm_account_pool.has_accounts(self.provider_family)

    def _ordered_accounts(self) -> List[LLMAccount]:
        return llm_account_pool.ordered_accounts(self.provider_family)

    def _post_json(
        self,
        *,
        url: str,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        timeout: int,
        error_prefix: str,
    ) -> Dict[str, Any]:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (TimeoutError, socket.timeout) as exc:
            raise LLMProviderError(f"{error_prefix} 请求超时（{timeout}s）") from exc
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            raise LLMProviderError(f"{error_prefix} HTTP {exc.code}: {body[:300]}") from exc
        except urllib.error.URLError as exc:
            raise LLMProviderError(f"{error_prefix} 网络错误: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise LLMProviderError(f"{error_prefix} 返回非 JSON 数据") from exc


class OpenAIResponsesProvider(BaseJSONLLMProvider):
    name = "openai_responses"
    provider_family = "openai"

    def generate_text(self, request: LLMRequest) -> str:
        accounts = self._ordered_accounts()
        if not accounts:
            raise LLMProviderError("OPENAI_API_KEY 或 OPENAI_MODEL 未配置")

        last_error: Optional[Exception] = None
        for account in accounts:
            try:
                return self._generate_text_with_account(request, account)
            except LLMProviderError as exc:
                last_error = exc
                continue
        raise LLMProviderError(str(last_error) if last_error else "OpenAI Responses 账号池无可用账号")

    def _generate_text_with_account(self, request: LLMRequest, account: LLMAccount) -> str:
        payload = {
            "model": account.model,
            "reasoning": {
                "effort": request.reasoning_effort or self.settings.openai_model_reasoning_effort
            },
            "max_output_tokens": request.max_output_tokens,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": request.system_prompt}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": request.user_prompt}],
                },
            ],
        }
        response = self._post_json(
            url=f"{account.base_url}/responses",
            payload=payload,
            headers={
                "Authorization": f"Bearer {account.auth_token}",
                "Content-Type": "application/json",
            },
            timeout=account.timeout_seconds,
            error_prefix=f"OpenAI Responses 接口[{account.account_id}]",
        )
        output_text = response.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        texts: List[str] = []
        for item in response.get("output", []):
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []):
                if (
                    isinstance(content, dict)
                    and content.get("type") in {"output_text", "text"}
                    and isinstance(content.get("text"), str)
                ):
                    texts.append(content["text"])
        text = "\n".join(texts).strip()
        if not text:
            raise LLMProviderError("OpenAI Responses 接口未返回文本内容")
        return text


class OpenAIChatCompletionsProvider(BaseJSONLLMProvider):
    name = "openai_chat_completions"
    provider_family = "openai"

    def generate_text(self, request: LLMRequest) -> str:
        accounts = self._ordered_accounts()
        if not accounts:
            raise LLMProviderError("OPENAI_API_KEY 或 OPENAI_MODEL 未配置")
        last_error: Optional[Exception] = None
        for account in accounts:
            try:
                return self._generate_text_with_account(request, account)
            except LLMProviderError as exc:
                last_error = exc
                continue
        raise LLMProviderError(str(last_error) if last_error else "OpenAI Chat Completions 账号池无可用账号")

    def _generate_text_with_account(self, request: LLMRequest, account: LLMAccount) -> str:
        payload = {
            "model": account.model,
            "reasoning_effort": request.reasoning_effort or self.settings.openai_model_reasoning_effort,
            "max_tokens": request.max_output_tokens,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
        }
        response = self._post_json(
            url=f"{account.base_url}/chat/completions",
            payload=payload,
            headers={
                "Authorization": f"Bearer {account.auth_token}",
                "Content-Type": "application/json",
            },
            timeout=account.timeout_seconds,
            error_prefix=f"OpenAI Chat Completions 接口[{account.account_id}]",
        )
        choices = response.get("choices") or []
        if not choices:
            raise LLMProviderError("OpenAI Chat Completions 接口未返回 choices")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
        if isinstance(content, list):
            texts = []
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    texts.append(item["text"])
            text = "\n".join(texts).strip()
            if text:
                return text
        raise LLMProviderError("OpenAI Chat Completions 接口未返回文本内容")


class MiniMaxAnthropicProvider(BaseJSONLLMProvider):
    name = "minimax_anthropic"
    provider_family = "anthropic"

    def generate_text(self, request: LLMRequest) -> str:
        accounts = self._ordered_accounts()
        if not accounts:
            raise LLMProviderError("ANTHROPIC_BASE_URL、ANTHROPIC_AUTH_TOKEN 或 ANTHROPIC_MODEL 未配置")
        last_error: Optional[Exception] = None
        for account in accounts:
            try:
                return self._generate_text_with_account(request, account)
            except LLMProviderError as exc:
                last_error = exc
                continue
        raise LLMProviderError(str(last_error) if last_error else "MiniMax Anthropic 账号池无可用账号")

    def _generate_text_with_account(self, request: LLMRequest, account: LLMAccount) -> str:
        payload = {
            "model": account.model,
            "max_tokens": request.max_output_tokens,
            "system": request.system_prompt,
            "messages": [{"role": "user", "content": request.user_prompt}],
        }
        response = self._post_json(
            url=self._join_url(account.base_url, "/v1/messages"),
            payload=payload,
            headers={
                "x-api-key": account.auth_token,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            timeout=account.timeout_seconds,
            error_prefix=f"MiniMax Anthropic 接口[{account.account_id}]",
        )
        content = response.get("content") or []
        if isinstance(content, str) and content.strip():
            return content.strip()
        if not isinstance(content, list):
            raise LLMProviderError("MiniMax Anthropic 接口未返回文本内容")

        texts: List[str] = []
        for item in content:
            if isinstance(item, str):
                texts.append(item)
                continue
            if (
                isinstance(item, dict)
                and item.get("type") == "text"
                and isinstance(item.get("text"), str)
            ):
                texts.append(item["text"])
        text = "\n".join(texts).strip()
        if not text:
            raise LLMProviderError("MiniMax Anthropic 接口未返回文本内容")
        return text

    def _join_url(self, base_url: str, path: str) -> str:
        base_url = base_url.rstrip("/")
        if base_url.endswith("/v1") and path.startswith("/v1/"):
            return f"{base_url}{path.removeprefix('/v1')}"
        return f"{base_url}{path}"


class LLMProviderManager:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.providers: Dict[str, LLMProvider] = {
            "openai_responses": OpenAIResponsesProvider(),
            "openai_chat_completions": OpenAIChatCompletionsProvider(),
            "minimax_anthropic": MiniMaxAnthropicProvider(),
        }

    @property
    def enabled(self) -> bool:
        return llm_account_pool.has_accounts("openai") or llm_account_pool.has_accounts("anthropic")

    @property
    def account_pool_adapter_name(self) -> str:
        return llm_account_pool.adapter_name

    def account_count(self, provider_family: str) -> int:
        return llm_account_pool.account_count(provider_family)

    def resolve_chain(self) -> List[LLMProvider]:
        mode = (self.settings.llm_chain_mode or "auto").strip().lower()
        chain_names = self._resolve_chain_names(mode)
        chain = [
            self.providers[name]
            for name in chain_names
            if name in self.providers and self.providers[name].enabled
        ]
        return chain

    def generate_text(self, request: LLMRequest) -> Optional[LLMTextResult]:
        chain = self.resolve_chain()
        if not chain:
            return None

        last_error: Optional[Exception] = None
        for provider in chain:
            try:
                text = provider.generate_text(request)
                return LLMTextResult(provider=provider.name, text=text)
            except LLMProviderError as exc:
                last_error = exc
                continue

        if last_error is None:
            return None
        raise LLMProviderError(str(last_error)) from last_error

    def _resolve_chain_names(self, mode: str) -> List[str]:
        if mode == "openai":
            return ["openai_responses", "openai_chat_completions"]
        if mode == "minimax":
            return ["minimax_anthropic"]
        return ["openai_responses", "openai_chat_completions", "minimax_anthropic"]


llm_provider_manager = LLMProviderManager()
