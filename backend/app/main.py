from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.schemas import (
    ChatCompareRequest,
    ChatFollowUpRequest,
    ChatMode,
    ChatRequest,
    ChatResponseStatus,
    EnvironmentStatus,
    SessionSummary,
    TemplateCreate,
    TemplateUpdate,
    UserProfileUpdate,
    WatchItemCreate,
    WatchStockResolveRequest,
    WatchItemUpdate,
)
from app.services.chat_engine import (
    build_route,
    compare_from_snapshot,
    detect_mode,
    execute_plan,
    result_to_chat_response,
    to_plain_json,
)
from app.services.llm_manager import llm_provider_manager
from app.services.langgraph_stock_agent import langgraph_stock_agent
from app.services.repository import repository, short_title
from app.services.watchlist_chat import (
    detect_watchlist_add_intent,
    execute_watchlist_add_intent,
)
from app.services.watchlist_resolver import (
    WatchlistResolveError,
    normalize_tags,
    prepare_watch_item_create,
    resolve_watch_stock,
)


settings = get_settings()

app = FastAPI(title=settings.app_name, version=settings.app_version)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def sse_payload(event: str, data: Dict[str, Any]) -> str:
    payload = {
        "event": event,
        "emitted_at": datetime.now(timezone.utc).isoformat(),
        **to_plain_json(data),
    }
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


def _complete_chat(request: ChatRequest):
    profile = repository.get_profile()
    session_summary = repository.get_session_summary(request.session_id) if request.session_id else None
    detection = detect_mode(
        request.message,
        mode_hint=request.mode_hint,
        session_mode=session_summary.mode if session_summary else None,
    )
    session = repository.ensure_session(request.session_id, request.message, detection.mode)
    repository.touch_session(session.id, title=short_title(request.message), mode=detection.mode)

    user_message = repository.add_message(
        {
            "session_id": session.id,
            "role": "user",
            "content": request.message,
            "mode": detection.mode.value,
            "status": ChatResponseStatus.COMPLETED.value,
        }
    )

    route = build_route(request.message, detection.mode, profile)
    result, skills_used, rewritten_query = execute_plan(route, profile, user_message=request.message)
    assistant_message = repository.add_message(
        {
            "session_id": session.id,
            "parent_message_id": user_message.id,
            "role": "assistant",
            "content": result.summary,
            "mode": detection.mode.value,
            "rewritten_query": rewritten_query,
            "skills_used": [skill.model_dump(mode="json") for skill in skills_used],
            "result_snapshot": result.model_dump(mode="json"),
            "status": ChatResponseStatus.COMPLETED.value,
        }
    )
    return detection, route, result_to_chat_response(
        session_id=session.id,
        message_id=assistant_message.id,
        mode=detection.mode,
        result=result,
        skills_used=skills_used,
    )


def _watchlist_response_mode(
    *,
    message: str,
    session_mode: Optional[ChatMode],
    mode_hint: Optional[ChatMode],
):
    if "短线" in message:
        return ChatMode.SHORT_TERM
    if "波段" in message:
        return ChatMode.SWING
    if "中线" in message or "价值" in message:
        return ChatMode.MID_TERM_VALUE
    if mode_hint:
        return mode_hint
    if session_mode:
        return session_mode
    return ChatMode.FOLLOW_UP


def _complete_watchlist_action(request: ChatRequest):
    session_summary = repository.get_session_summary(request.session_id) if request.session_id else None
    intent = detect_watchlist_add_intent(
        request.message,
        mode_hint=request.mode_hint,
        session_mode=session_summary.mode if session_summary else None,
    )
    if intent is None:
        return None

    response_mode = _watchlist_response_mode(
        message=request.message,
        session_mode=session_summary.mode if session_summary else None,
        mode_hint=request.mode_hint,
    )
    session = repository.ensure_session(request.session_id, request.message, response_mode)
    latest_assistant = repository.latest_assistant_message(session.id)
    repository.touch_session(session.id, title=short_title(request.message))
    user_message = repository.add_message(
        {
            "session_id": session.id,
            "parent_message_id": latest_assistant.id if latest_assistant else None,
            "role": "user",
            "content": request.message,
            "mode": response_mode.value,
            "status": ChatResponseStatus.COMPLETED.value,
        }
    )

    result = execute_watchlist_add_intent(
        repository=repository,
        intent=intent,
        session_id=session.id,
        message=request.message,
        latest_assistant=latest_assistant,
    )
    assistant_message = repository.add_message(
        {
            "session_id": session.id,
            "parent_message_id": user_message.id,
            "role": "assistant",
            "content": result.summary,
            "mode": response_mode.value,
            "skills_used": [],
            "result_snapshot": result.model_dump(mode="json"),
            "status": ChatResponseStatus.COMPLETED.value,
        }
    )
    return result_to_chat_response(
        session_id=session.id,
        message_id=assistant_message.id,
        mode=response_mode,
        result=result,
        skills_used=[],
    )


def _stream_chat(request: ChatRequest):
    def generate():
        yield sse_payload("analysis_started", {"status": "analyzing"})
        session_summary = repository.get_session_summary(request.session_id) if request.session_id else None
        detection = detect_mode(
            request.message,
            mode_hint=request.mode_hint,
            session_mode=session_summary.mode if session_summary else None,
        )
        yield sse_payload(
            "mode_detected",
            {"mode": detection.mode.value, "confidence": detection.confidence, "source": detection.source},
        )

        profile = repository.get_profile()
        session = repository.ensure_session(request.session_id, request.message, detection.mode)
        repository.touch_session(session.id, title=short_title(request.message), mode=detection.mode)
        user_message = repository.add_message(
            {
                "session_id": session.id,
                "role": "user",
                "content": request.message,
                "mode": detection.mode.value,
                "status": ChatResponseStatus.COMPLETED.value,
            }
        )

        route = build_route(request.message, detection.mode, profile)
        yield sse_payload(
            "skill_routing_ready",
            {
                "strategy": route.strategy.value,
                "skills": [
                    {"name": plan.name, "query": plan.query, "reason": plan.reason}
                    for plan in route.skills
                ],
            },
        )
        for plan in route.skills:
            yield sse_payload("skill_started", {"name": plan.name, "query": plan.query})

        result, skills_used, rewritten_query = execute_plan(route, profile, user_message=request.message)
        for skill in skills_used:
            yield sse_payload("skill_finished", skill.model_dump(mode="json"))

        yield sse_payload("partial_result", result.model_dump(mode="json"))
        assistant_message = repository.add_message(
            {
                "session_id": session.id,
                "parent_message_id": user_message.id,
                "role": "assistant",
                "content": result.summary,
                "mode": detection.mode.value,
                "rewritten_query": rewritten_query,
                "skills_used": [skill.model_dump(mode="json") for skill in skills_used],
                "result_snapshot": result.model_dump(mode="json"),
                "status": ChatResponseStatus.COMPLETED.value,
            }
        )
        response = result_to_chat_response(
            session_id=session.id,
            message_id=assistant_message.id,
            mode=detection.mode,
            result=result,
            skills_used=skills_used,
        )
        yield sse_payload("completed", response.model_dump(mode="json"))

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/health")
def health():
    return {"ok": True, "version": settings.app_version}


@app.get("/api/meta/status", response_model=EnvironmentStatus)
def meta_status():
    skills_lock = settings.skills_root / ".skills_store_lock.json"
    skill_count = 0
    openai_account_count = llm_provider_manager.account_count("openai")
    anthropic_account_count = llm_provider_manager.account_count("anthropic")
    if skills_lock.exists():
        try:
            payload = json.loads(skills_lock.read_text(encoding="utf-8"))
            skill_count = len(payload.get("skills", {}))
        except json.JSONDecodeError:
            skill_count = 0
    return {
        "api_base_url": settings.iwencai_base_url,
        "api_key_configured": bool(settings.iwencai_api_key),
        "skill_count": skill_count,
        "llm_chain_mode": settings.llm_chain_mode,
        "llm_agent_runtime": langgraph_stock_agent.runtime,
        "llm_enabled": llm_provider_manager.enabled,
        "llm_account_pool_adapter": llm_provider_manager.account_pool_adapter_name,
        "llm_system_prompt_source": settings.llm_system_prompt_source,
        "llm_system_prompt_role": settings.llm_system_prompt_role,
        "openai_base_url": settings.openai_base_url,
        "openai_api_key_configured": openai_account_count > 0,
        "openai_model": settings.openai_model,
        "openai_reasoning_effort": settings.openai_model_reasoning_effort,
        "openai_enabled": openai_account_count > 0,
        "openai_account_count": openai_account_count,
        "anthropic_base_url": settings.anthropic_base_url,
        "anthropic_auth_token_configured": anthropic_account_count > 0,
        "anthropic_model": settings.anthropic_model,
        "anthropic_enabled": anthropic_account_count > 0,
        "anthropic_account_count": anthropic_account_count,
        "version": settings.app_version,
    }


@app.get("/api/sessions", response_model=list[SessionSummary])
def list_sessions():
    return repository.list_sessions()


@app.post("/api/sessions", response_model=SessionSummary)
def create_session():
    return repository.create_session()


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    detail = repository.get_session(session_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Session not found")
    return detail


@app.delete("/api/sessions/{session_id}")
def close_session(session_id: str):
    if not repository.archive_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"ok": True}


@app.post("/api/chat")
def chat(request: ChatRequest):
    watchlist_response = _complete_watchlist_action(request)
    if watchlist_response is not None:
        if request.stream:
            return StreamingResponse(
                iter(
                    [
                        sse_payload("analysis_started", {"status": "analyzing"}),
                        sse_payload(
                            "mode_detected",
                            {
                                "mode": watchlist_response.mode.value,
                                "confidence": 1.0,
                                "source": "watchlist_action",
                            },
                        ),
                        sse_payload("completed", watchlist_response.model_dump(mode="json")),
                    ]
                ),
                media_type="text/event-stream",
            )
        return watchlist_response
    if request.stream:
        return _stream_chat(request)
    _, _, response = _complete_chat(request)
    return response


@app.post("/api/chat/follow-up")
def chat_follow_up(request: ChatFollowUpRequest):
    parent = repository.find_message(request.parent_message_id) or repository.latest_assistant_message(request.session_id)
    result = compare_from_snapshot(parent.result_snapshot if parent else None, request.message)
    mode = ChatMode.COMPARE if "比" in request.message or "排序" in request.message else ChatMode.FOLLOW_UP
    user_message = repository.add_message(
        {
            "session_id": request.session_id,
            "parent_message_id": parent.id if parent else request.parent_message_id,
            "role": "user",
            "content": request.message,
            "mode": mode.value,
            "status": ChatResponseStatus.COMPLETED.value,
        }
    )
    assistant_message = repository.add_message(
        {
            "session_id": request.session_id,
            "parent_message_id": user_message.id,
            "role": "assistant",
            "content": result.summary,
            "mode": mode.value,
            "skills_used": [],
            "result_snapshot": result.model_dump(mode="json"),
            "status": ChatResponseStatus.COMPLETED.value,
        }
    )
    response = result_to_chat_response(
        session_id=request.session_id,
        message_id=assistant_message.id,
        mode=mode,
        result=result,
        skills_used=[],
    )
    if request.stream:
        return StreamingResponse(
            iter([sse_payload("completed", response.model_dump(mode="json"))]),
            media_type="text/event-stream",
        )
    return response


@app.post("/api/chat/compare")
def chat_compare(request: ChatCompareRequest):
    parent = (
        repository.find_message(request.parent_message_id)
        if request.parent_message_id
        else repository.latest_assistant_message(request.session_id)
    )
    prompt = request.message or "比较上一轮结果"
    result = compare_from_snapshot(parent.result_snapshot if parent else None, prompt)
    user_message = repository.add_message(
        {
            "session_id": request.session_id,
            "parent_message_id": parent.id if parent else request.parent_message_id,
            "role": "user",
            "content": prompt,
            "mode": ChatMode.COMPARE.value,
            "status": ChatResponseStatus.COMPLETED.value,
        }
    )
    assistant_message = repository.add_message(
        {
            "session_id": request.session_id,
            "parent_message_id": user_message.id,
            "role": "assistant",
            "content": result.summary,
            "mode": ChatMode.COMPARE.value,
            "skills_used": [],
            "result_snapshot": result.model_dump(mode="json"),
            "status": ChatResponseStatus.COMPLETED.value,
        }
    )
    response = result_to_chat_response(
        session_id=request.session_id,
        message_id=assistant_message.id,
        mode=ChatMode.COMPARE,
        result=result,
        skills_used=[],
    )
    if request.stream:
        return StreamingResponse(
            iter([sse_payload("completed", response.model_dump(mode="json"))]),
            media_type="text/event-stream",
        )
    return response


@app.get("/api/profile")
def get_profile():
    return repository.get_profile()


@app.put("/api/profile")
def update_profile(update: UserProfileUpdate):
    return repository.update_profile(update)


@app.get("/api/templates")
def list_templates():
    return repository.list_templates()


@app.post("/api/templates")
def create_template(data: TemplateCreate):
    return repository.create_template(data)


@app.put("/api/templates/{template_id}")
def update_template(template_id: str, update: TemplateUpdate):
    template = repository.update_template(template_id, update)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@app.delete("/api/templates/{template_id}")
def delete_template(template_id: str):
    return {"ok": repository.delete_template(template_id)}


@app.get("/api/watchlist")
def list_watchlist():
    return repository.list_watchlist()


@app.post("/api/watchlist/resolve")
def resolve_watch_item(data: WatchStockResolveRequest):
    try:
        return resolve_watch_stock(data.query)
    except WatchlistResolveError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/watchlist")
def create_watch_item(data: WatchItemCreate):
    try:
        prepared = prepare_watch_item_create(data)
    except WatchlistResolveError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    existing = repository.find_watch_item_by_symbol(prepared.symbol or "")
    if existing:
        raise HTTPException(status_code=409, detail=f"{existing.name}（{existing.symbol}）已在候选池中")
    return repository.create_watch_item(prepared)


@app.patch("/api/watchlist/{item_id}")
def update_watch_item(item_id: str, update: WatchItemUpdate):
    normalized = WatchItemUpdate(
        bucket=update.bucket,
        tags=normalize_tags(update.tags or []) if update.tags is not None else None,
        note=update.note.strip() if isinstance(update.note, str) and update.note.strip() else None,
    )
    item = repository.update_watch_item(item_id, normalized)
    if not item:
        raise HTTPException(status_code=404, detail="Watch item not found")
    return item


@app.delete("/api/watchlist/{item_id}")
def delete_watch_item(item_id: str):
    return {"ok": repository.delete_watch_item(item_id)}
