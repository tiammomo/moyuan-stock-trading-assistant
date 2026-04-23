from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.core.config import get_settings
from app.schemas import (
    ChatMessageRecord,
    ChatMode,
    ChatResponseStatus,
    SessionDetail,
    SessionSummary,
    TemplateCreate,
    TemplateRecord,
    TemplateUpdate,
    UserProfile,
    UserProfileUpdate,
    WatchItemCreate,
    WatchItemRecord,
    WatchItemUpdate,
)

from .json_store import JsonFileStore


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def short_title(text: str, fallback: str = "新会话") -> str:
    stripped = " ".join(text.strip().split())
    if not stripped:
        return fallback
    return stripped[:24] + ("..." if len(stripped) > 24 else "")


def default_profile() -> Dict[str, Any]:
    return {
        "capital": None,
        "position_limit_pct": 20,
        "max_drawdown_pct": 8,
        "holding_horizon": "2-4w",
        "risk_style": "balanced",
        "preferred_sectors": [],
        "default_mode": "swing",
        "default_result_size": 5,
        "gpt_enhancement_enabled": True,
        "gpt_reasoning_policy": "auto",
    }


def default_templates() -> List[Dict[str, Any]]:
    created_at = utc_now_iso()
    return [
        {
            "id": "official_short_term",
            "name": "短线观察股",
            "category": "选股",
            "mode": "short_term",
            "content": "今天适合做什么方向？给我 5 只短线观察股，并说明催化、资金和风险。",
            "default_params": {},
            "created_at": created_at,
        },
        {
            "id": "official_swing",
            "name": "波段趋势候选",
            "category": "选股",
            "mode": "swing",
            "content": "找 5 只未来 2 到 4 周值得跟踪的趋势股，结合行业、资金、财务和事件催化。",
            "default_params": {},
            "created_at": created_at,
        },
        {
            "id": "official_mid_value",
            "name": "中线价值筛选",
            "category": "分析",
            "mode": "mid_term_value",
            "content": "筛几只估值不贵、财务质量不错、现金流较好的 A 股，并给出主要风险。",
            "default_params": {},
            "created_at": created_at,
        },
        {
            "id": "official_compare",
            "name": "Top 3 比较",
            "category": "比较",
            "mode": "compare",
            "content": "把刚才 Top 3 从胜率、赔率、催化确定性、回撤风险、拥挤度五个维度打分比较。",
            "default_params": {},
            "created_at": created_at,
        },
    ]


class Repository:
    def __init__(self) -> None:
        settings = get_settings()
        self.profile_store = JsonFileStore(settings.data_dir / "profile.json", default_profile)
        self.sessions_store = JsonFileStore(settings.data_dir / "sessions.json", lambda: [])
        self.messages_store = JsonFileStore(settings.data_dir / "messages.json", lambda: [])
        self.templates_store = JsonFileStore(settings.data_dir / "templates.json", default_templates)
        self.watchlist_store = JsonFileStore(settings.data_dir / "watchlist.json", lambda: [])

    def get_profile(self) -> UserProfile:
        return UserProfile(**self.profile_store.read())

    def update_profile(self, update: UserProfileUpdate) -> UserProfile:
        patch = update.model_dump(exclude_unset=True)

        def mutate(data: Dict[str, Any]) -> Dict[str, Any]:
            data.update({k: v for k, v in patch.items() if v is not None or k in patch})
            return data

        return UserProfile(**self.profile_store.update(mutate))

    def list_sessions(self) -> List[SessionSummary]:
        data = sorted(
            [item for item in self.sessions_store.read() if not item.get("archived", False)],
            key=lambda item: item.get("updated_at", ""),
            reverse=True,
        )
        return [SessionSummary(**item) for item in data]

    def create_session(self, title: str = "新会话", mode: Optional[ChatMode] = None) -> SessionSummary:
        now = utc_now_iso()
        session = {
            "id": f"s_{uuid4().hex[:12]}",
            "title": title,
            "mode": mode.value if mode else None,
            "archived": False,
            "created_at": now,
            "updated_at": now,
        }

        def mutate(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            data.append(session)
            return data

        self.sessions_store.update(mutate)
        return SessionSummary(**session)

    def ensure_session(
        self,
        session_id: Optional[str],
        title_from_message: str = "",
        mode: Optional[ChatMode] = None,
    ) -> SessionSummary:
        if session_id:
            existing = self._find_session(session_id)
            if existing and not existing.get("archived", False):
                return SessionSummary(**existing)
        return self.create_session(short_title(title_from_message), mode)

    def _find_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        for item in self.sessions_store.read():
            if item["id"] == session_id:
                return item
        return None

    def get_session(self, session_id: str) -> Optional[SessionDetail]:
        session = self._find_session(session_id)
        if not session or session.get("archived", False):
            return None
        messages = [
            ChatMessageRecord(**item)
            for item in self.messages_store.read()
            if item.get("session_id") == session_id
        ]
        messages.sort(key=lambda item: item.created_at)
        return SessionDetail(**session, messages=messages)

    def get_session_summary(self, session_id: str) -> Optional[SessionSummary]:
        session = self._find_session(session_id)
        return SessionSummary(**session) if session and not session.get("archived", False) else None

    def touch_session(
        self,
        session_id: str,
        *,
        title: Optional[str] = None,
        mode: Optional[ChatMode] = None,
    ) -> None:
        now = utc_now_iso()

        def mutate(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            for item in data:
                if item["id"] == session_id:
                    if title and item.get("title") == "新会话":
                        item["title"] = title
                    if mode:
                        item["mode"] = mode.value
                    item["updated_at"] = now
                    break
            return data

        self.sessions_store.update(mutate)

    def archive_session(self, session_id: str) -> bool:
        archived = False

        def mutate(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            nonlocal archived
            for item in data:
                if item["id"] == session_id and not item.get("archived", False):
                    item["archived"] = True
                    item["updated_at"] = utc_now_iso()
                    archived = True
                    break
            return data

        self.sessions_store.update(mutate)
        return archived

    def add_message(self, data: Dict[str, Any]) -> ChatMessageRecord:
        payload = {
            "id": data.get("id") or f"m_{uuid4().hex[:12]}",
            "session_id": data["session_id"],
            "parent_message_id": data.get("parent_message_id"),
            "role": data["role"],
            "content": data.get("content", ""),
            "mode": data.get("mode"),
            "rewritten_query": data.get("rewritten_query"),
            "skills_used": data.get("skills_used", []),
            "result_snapshot": data.get("result_snapshot"),
            "status": data.get("status"),
            "created_at": data.get("created_at") or utc_now_iso(),
        }

        def mutate(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            items.append(payload)
            return items

        self.messages_store.update(mutate)
        self.touch_session(payload["session_id"])
        return ChatMessageRecord(**payload)

    def find_message(self, message_id: str) -> Optional[ChatMessageRecord]:
        for item in self.messages_store.read():
            if item.get("id") == message_id:
                return ChatMessageRecord(**item)
        return None

    def latest_assistant_message(self, session_id: str) -> Optional[ChatMessageRecord]:
        messages = [
            item for item in self.messages_store.read()
            if item.get("session_id") == session_id and item.get("role") == "assistant"
        ]
        if not messages:
            return None
        messages.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return ChatMessageRecord(**messages[0])

    def list_templates(self) -> List[TemplateRecord]:
        return [TemplateRecord(**item) for item in self.templates_store.read()]

    def create_template(self, data: TemplateCreate) -> TemplateRecord:
        payload = data.model_dump()
        payload.update({"id": f"user_{uuid4().hex[:12]}", "created_at": utc_now_iso()})

        def mutate(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            items.append(payload)
            return items

        self.templates_store.update(mutate)
        return TemplateRecord(**payload)

    def update_template(self, template_id: str, update: TemplateUpdate) -> Optional[TemplateRecord]:
        patch = update.model_dump(exclude_unset=True)
        updated: Optional[Dict[str, Any]] = None

        def mutate(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            nonlocal updated
            for item in items:
                if item["id"] == template_id:
                    item.update(patch)
                    updated = item
                    break
            return items

        self.templates_store.update(mutate)
        return TemplateRecord(**updated) if updated else None

    def delete_template(self, template_id: str) -> bool:
        before = len(self.templates_store.read())
        self.templates_store.write([i for i in self.templates_store.read() if i["id"] != template_id])
        return len(self.templates_store.read()) < before

    def list_watchlist(self) -> List[WatchItemRecord]:
        data = sorted(
            self.watchlist_store.read(),
            key=lambda item: item.get("updated_at", ""),
            reverse=True,
        )
        return [WatchItemRecord(**item) for item in data]

    def create_watch_item(self, data: WatchItemCreate) -> WatchItemRecord:
        now = utc_now_iso()
        payload = data.model_dump(exclude={"query"})
        payload.update({"id": f"w_{uuid4().hex[:12]}", "created_at": now, "updated_at": now})

        def mutate(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            items.append(payload)
            return items

        self.watchlist_store.update(mutate)
        return WatchItemRecord(**payload)

    def find_watch_item_by_symbol(self, symbol: str) -> Optional[WatchItemRecord]:
        normalized = str(symbol).strip().upper()
        if not normalized:
            return None
        for item in self.watchlist_store.read():
            if str(item.get("symbol", "")).strip().upper() == normalized:
                return WatchItemRecord(**item)
        return None

    def update_watch_item(self, item_id: str, update: WatchItemUpdate) -> Optional[WatchItemRecord]:
        patch = update.model_dump(exclude_unset=True)
        updated: Optional[Dict[str, Any]] = None

        def mutate(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            nonlocal updated
            for item in items:
                if item["id"] == item_id:
                    item.update(patch)
                    item["updated_at"] = utc_now_iso()
                    updated = item
                    break
            return items

        self.watchlist_store.update(mutate)
        return WatchItemRecord(**updated) if updated else None

    def delete_watch_item(self, item_id: str) -> bool:
        before = len(self.watchlist_store.read())
        self.watchlist_store.write([i for i in self.watchlist_store.read() if i["id"] != item_id])
        return len(self.watchlist_store.read()) < before


repository = Repository()
