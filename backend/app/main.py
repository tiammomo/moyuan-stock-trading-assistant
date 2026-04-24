from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
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
    ChatResponse,
    ChatResponseStatus,
    EnvironmentStatus,
    ResultCard,
    StructuredResult,
    SessionSummary,
    TemplateCreate,
    TemplateUpdate,
    MonitorRuleCreate,
    MonitorRuleRecord,
    MonitorRuleUpdate,
    PortfolioAccountCreate,
    PortfolioAccountRecord,
    PortfolioScreenshotImportRequest,
    PortfolioScreenshotImportResponse,
    PortfolioAccountUpdate,
    PortfolioPositionCreate,
    PortfolioPositionRecord,
    PortfolioPositionUpdate,
    PortfolioSummary,
    UserProfileUpdate,
    UserVisibleError,
    UserVisibleErrorSeverity,
    WatchMonitorEvent,
    WatchMonitorScanResponse,
    WatchMonitorStatus,
    WatchlistBackfillResponse,
    WatchItemCreate,
    WatchStockResolveRequest,
    WatchItemUpdate,
)
from app.services.chat_engine import (
    build_route,
    compare_from_snapshot,
    detect_mode,
    enhance_plan_result,
    execute_plan,
    execute_plan_base,
    is_compare_follow_up,
    plan_follow_up_route,
    refine_follow_up_from_snapshot,
    result_to_chat_response,
    to_plain_json,
)
from app.services.llm_manager import llm_provider_manager
from app.services.langgraph_stock_agent import langgraph_stock_agent
from app.services.portfolio_screenshot_importer import (
    PortfolioScreenshotImportError,
    portfolio_screenshot_importer,
)
from app.services.portfolio_store import portfolio_store
from app.services.repository import repository, short_title
from app.services.skill_registry import skill_registry
from app.services.watchlist_chat import (
    detect_watchlist_add_intent,
    execute_watchlist_add_intent,
)
from app.services.watchlist_backfill import backfill_watchlist
from app.services.watch_monitor import watch_monitor_service
from app.services.watch_rule_store import WatchRuleStoreError, watch_rule_store
from app.services.watchlist_resolver import (
    WatchlistResolveError,
    normalize_tags,
    prepare_watch_item_create,
    resolve_watch_stock,
)


settings = get_settings()
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, version=settings.app_version)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def start_background_services() -> None:
    watch_rule_store.ensure_default_rules(repository.list_watchlist())
    watch_monitor_service.start()


@app.on_event("shutdown")
async def stop_background_services() -> None:
    await watch_monitor_service.shutdown()


def sse_payload(event: str, data: Dict[str, Any]) -> str:
    payload = {
        "event": event,
        "emitted_at": datetime.now(timezone.utc).isoformat(),
        **to_plain_json(data),
    }
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


def _resolved_mode_or_default(mode: Optional[ChatMode]) -> ChatMode:
    return mode or ChatMode.GENERIC_DATA_QUERY


def _default_chat_error(exc: Exception) -> UserVisibleError:
    if isinstance(exc, HTTPException):
        detail = exc.detail if isinstance(exc.detail, str) and exc.detail else "请求失败"
        return UserVisibleError(
            code=f"http_{exc.status_code}",
            severity=UserVisibleErrorSeverity.ERROR,
            title="请求失败",
            message=detail,
            retryable=exc.status_code >= 500,
        )

    return UserVisibleError(
        code="chat_internal_error",
        severity=UserVisibleErrorSeverity.ERROR,
        title="本次分析失败",
        message="系统处理这次请求时失败，请稍后重试。",
        retryable=True,
    )


def _failed_structured_result(error: UserVisibleError) -> StructuredResult:
    return StructuredResult(
        summary=error.message,
        cards=[
            ResultCard(
                type="chat_error",
                title=error.title,
                content=error.message,
                metadata={
                    "code": error.code,
                    "severity": error.severity.value,
                    "retryable": error.retryable,
                },
            )
        ],
    )


def _ephemeral_failed_response(
    *,
    session_id: str,
    mode: ChatMode,
    error: UserVisibleError,
) -> ChatResponse:
    return result_to_chat_response(
        session_id=session_id,
        message_id=f"m_failed_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
        mode=mode,
        result=_failed_structured_result(error),
        skills_used=[],
        status=ChatResponseStatus.FAILED,
        user_visible_error=error,
    )


def _persist_failed_response(
    *,
    session_id: str,
    parent_message_id: Optional[str],
    mode: ChatMode,
    error: UserVisibleError,
) -> ChatResponse:
    failed_result = _failed_structured_result(error)
    assistant_message = repository.add_message(
        {
            "session_id": session_id,
            "parent_message_id": parent_message_id,
            "role": "assistant",
            "content": error.message,
            "mode": mode.value,
            "skills_used": [],
            "result_snapshot": failed_result.model_dump(mode="json"),
            "status": ChatResponseStatus.FAILED.value,
            "user_visible_error": error.model_dump(mode="json"),
        }
    )
    return result_to_chat_response(
        session_id=session_id,
        message_id=assistant_message.id,
        mode=mode,
        result=failed_result,
        skills_used=[],
        status=ChatResponseStatus.FAILED,
        user_visible_error=error,
    )


def _persist_assistant_response(
    *,
    session_id: str,
    parent_message_id: Optional[str],
    mode: ChatMode,
    result: StructuredResult,
    skills_used,
    rewritten_query: str = "",
    user_visible_error: Optional[UserVisibleError] = None,
):
    assistant_message = repository.add_message(
        {
            "session_id": session_id,
            "parent_message_id": parent_message_id,
            "role": "assistant",
            "content": result.summary,
            "mode": mode.value,
            "rewritten_query": rewritten_query,
            "skills_used": [skill.model_dump(mode="json") for skill in skills_used],
            "result_snapshot": result.model_dump(mode="json"),
            "status": ChatResponseStatus.COMPLETED.value,
            "user_visible_error": (
                user_visible_error.model_dump(mode="json")
                if user_visible_error is not None
                else None
            ),
        }
    )
    return assistant_message, result_to_chat_response(
        session_id=session_id,
        message_id=assistant_message.id,
        mode=mode,
        result=result,
        skills_used=skills_used,
        user_visible_error=user_visible_error,
    )


def _update_assistant_response(
    *,
    message_id: str,
    session_id: str,
    mode: ChatMode,
    result: StructuredResult,
    skills_used,
    rewritten_query: str = "",
    user_visible_error: Optional[UserVisibleError] = None,
) -> Optional[ChatResponse]:
    assistant_message = repository.update_message(
        message_id,
        {
            "content": result.summary,
            "mode": mode.value,
            "rewritten_query": rewritten_query,
            "skills_used": [skill.model_dump(mode="json") for skill in skills_used],
            "result_snapshot": result.model_dump(mode="json"),
            "status": ChatResponseStatus.COMPLETED.value,
            "user_visible_error": (
                user_visible_error.model_dump(mode="json")
                if user_visible_error is not None
                else None
            ),
        },
    )
    if assistant_message is None:
        return None
    return result_to_chat_response(
        session_id=session_id,
        message_id=assistant_message.id,
        mode=mode,
        result=result,
        skills_used=skills_used,
        user_visible_error=user_visible_error,
    )


def _result_changed(before: StructuredResult, after: StructuredResult) -> bool:
    return before.model_dump(mode="json") != after.model_dump(mode="json")


def _maybe_build_enhanced_response(
    *,
    session_id: str,
    message_id: str,
    mode: ChatMode,
    route,
    profile,
    user_message: str,
    result: StructuredResult,
    skills_used,
    rewritten_query: str,
    user_visible_error: Optional[UserVisibleError],
    should_enhance: bool,
) -> Optional[ChatResponse]:
    try:
        enhanced_result = enhance_plan_result(
            route,
            result,
            profile,
            user_message=user_message,
            should_enhance=should_enhance,
            user_visible_error=user_visible_error,
        )
    except Exception:
        logger.exception("Post-completion result enhancement failed")
        return None

    if not _result_changed(result, enhanced_result):
        return None

    return _update_assistant_response(
        message_id=message_id,
        session_id=session_id,
        mode=mode,
        result=enhanced_result,
        skills_used=skills_used,
        rewritten_query=rewritten_query,
        user_visible_error=user_visible_error,
    )


def _complete_chat(request: ChatRequest):
    detection = None
    route = None
    session = None
    user_message = None

    try:
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
        result, skills_used, rewritten_query, user_visible_error = execute_plan(
            route,
            profile,
            user_message=request.message,
        )
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
                "user_visible_error": (
                    user_visible_error.model_dump(mode="json")
                    if user_visible_error is not None
                    else None
                ),
            }
        )
        return detection, route, result_to_chat_response(
            session_id=session.id,
            message_id=assistant_message.id,
            mode=detection.mode,
            result=result,
            skills_used=skills_used,
            user_visible_error=user_visible_error,
        )
    except Exception as exc:
        logger.exception("Chat request failed")
        error = _default_chat_error(exc)
        failed_mode = _resolved_mode_or_default(detection.mode if detection is not None else request.mode_hint)
        try:
            if session is None:
                session = repository.ensure_session(request.session_id, request.message, failed_mode)
                repository.touch_session(session.id, title=short_title(request.message), mode=failed_mode)
            if user_message is None:
                user_message = repository.add_message(
                    {
                        "session_id": session.id,
                        "role": "user",
                        "content": request.message,
                        "mode": failed_mode.value,
                        "status": ChatResponseStatus.COMPLETED.value,
                    }
                )
            response = _persist_failed_response(
                session_id=session.id,
                parent_message_id=user_message.id,
                mode=failed_mode,
                error=error,
            )
        except Exception:
            logger.exception("Failed to persist chat failure")
            fallback_session_id = session.id if session is not None else (request.session_id or "")
            response = _ephemeral_failed_response(
                session_id=fallback_session_id,
                mode=failed_mode,
                error=error,
            )
        return detection, route, response


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
        detection = None
        route = None
        session = None
        user_message = None

        try:
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

            result, skills_used, rewritten_query, user_visible_error, should_enhance = execute_plan_base(
                route,
                profile,
                user_message=request.message,
            )
            for skill in skills_used:
                yield sse_payload("skill_finished", skill.model_dump(mode="json"))

            yield sse_payload("partial_result", result.model_dump(mode="json"))
            assistant_message, response = _persist_assistant_response(
                session_id=session.id,
                parent_message_id=user_message.id,
                mode=detection.mode,
                result=result,
                skills_used=skills_used,
                rewritten_query=rewritten_query,
                user_visible_error=user_visible_error,
            )
            yield sse_payload("completed", response.model_dump(mode="json"))

            enhanced_response = _maybe_build_enhanced_response(
                session_id=session.id,
                message_id=assistant_message.id,
                mode=detection.mode,
                route=route,
                profile=profile,
                user_message=request.message,
                result=result,
                skills_used=skills_used,
                rewritten_query=rewritten_query,
                user_visible_error=user_visible_error,
                should_enhance=should_enhance,
            )
            if enhanced_response is not None:
                yield sse_payload("result_enhanced", enhanced_response.model_dump(mode="json"))
        except Exception as exc:
            logger.exception("Streaming chat request failed")
            error = _default_chat_error(exc)
            failed_mode = _resolved_mode_or_default(detection.mode if detection is not None else request.mode_hint)
            try:
                if session is None:
                    session = repository.ensure_session(request.session_id, request.message, failed_mode)
                    repository.touch_session(session.id, title=short_title(request.message), mode=failed_mode)
                if user_message is None:
                    user_message = repository.add_message(
                        {
                            "session_id": session.id,
                            "role": "user",
                            "content": request.message,
                            "mode": failed_mode.value,
                            "status": ChatResponseStatus.COMPLETED.value,
                        }
                    )
                response = _persist_failed_response(
                    session_id=session.id,
                    parent_message_id=user_message.id,
                    mode=failed_mode,
                    error=error,
                )
            except Exception:
                logger.exception("Failed to persist streaming chat failure")
                fallback_session_id = session.id if session is not None else (request.session_id or "")
                response = _ephemeral_failed_response(
                    session_id=fallback_session_id,
                    mode=failed_mode,
                    error=error,
                )
            payload = response.model_dump(mode="json")
            payload["error"] = error.message
            yield sse_payload("failed", payload)

    return StreamingResponse(generate(), media_type="text/event-stream")


def _resolve_follow_up_parent(session_id: str, parent_message_id: str):
    parent = repository.find_message(parent_message_id)
    if parent is not None and parent.role == "assistant":
        return parent
    latest_assistant = repository.latest_assistant_message(session_id)
    return latest_assistant or parent


def _complete_follow_up(request: ChatFollowUpRequest):
    parent = None
    user_message = None
    response_mode = ChatMode.FOLLOW_UP
    detection = None
    route = None

    try:
        session_summary = repository.get_session_summary(request.session_id)
        parent = _resolve_follow_up_parent(request.session_id, request.parent_message_id)
        local_refined_result = refine_follow_up_from_snapshot(
            parent.result_snapshot if parent else None,
            request.message,
            parent_mode=parent.mode if parent else session_summary.mode if session_summary else None,
        )
        response_mode = (
            ChatMode.FOLLOW_UP
            if local_refined_result is not None
            else ChatMode.COMPARE if is_compare_follow_up(request.message) else ChatMode.FOLLOW_UP
        )
        user_message = repository.add_message(
            {
                "session_id": request.session_id,
                "parent_message_id": parent.id if parent else request.parent_message_id,
                "role": "user",
                "content": request.message,
                "mode": response_mode.value,
                "status": ChatResponseStatus.COMPLETED.value,
            }
        )

        if response_mode == ChatMode.COMPARE:
            result = compare_from_snapshot(parent.result_snapshot if parent else None, request.message)
            assistant_message = repository.add_message(
                {
                    "session_id": request.session_id,
                    "parent_message_id": user_message.id,
                    "role": "assistant",
                    "content": result.summary,
                    "mode": response_mode.value,
                    "skills_used": [],
                    "result_snapshot": result.model_dump(mode="json"),
                    "status": ChatResponseStatus.COMPLETED.value,
                }
            )
            return None, None, result_to_chat_response(
                session_id=request.session_id,
                message_id=assistant_message.id,
                mode=response_mode,
                result=result,
                skills_used=[],
            )

        if local_refined_result is not None:
            assistant_message = repository.add_message(
                {
                    "session_id": request.session_id,
                    "parent_message_id": user_message.id,
                    "role": "assistant",
                    "content": local_refined_result.summary,
                    "mode": response_mode.value,
                    "skills_used": [],
                    "result_snapshot": local_refined_result.model_dump(mode="json"),
                    "status": ChatResponseStatus.COMPLETED.value,
                }
            )
            return None, None, result_to_chat_response(
                session_id=request.session_id,
                message_id=assistant_message.id,
                mode=response_mode,
                result=local_refined_result,
                skills_used=[],
            )

        profile = repository.get_profile()
        detection, route, contextual_message = plan_follow_up_route(
            request.message,
            parent,
            session_mode=session_summary.mode if session_summary else None,
            profile=profile,
        )
        result, skills_used, rewritten_query, user_visible_error = execute_plan(
            route,
            profile,
            user_message=contextual_message,
        )
        assistant_message = repository.add_message(
            {
                "session_id": request.session_id,
                "parent_message_id": user_message.id,
                "role": "assistant",
                "content": result.summary,
                "mode": response_mode.value,
                "rewritten_query": rewritten_query,
                "skills_used": [skill.model_dump(mode="json") for skill in skills_used],
                "result_snapshot": result.model_dump(mode="json"),
                "status": ChatResponseStatus.COMPLETED.value,
                "user_visible_error": (
                    user_visible_error.model_dump(mode="json")
                    if user_visible_error is not None
                    else None
                ),
            }
        )
        return detection, route, result_to_chat_response(
            session_id=request.session_id,
            message_id=assistant_message.id,
            mode=response_mode,
            result=result,
            skills_used=skills_used,
            user_visible_error=user_visible_error,
        )
    except Exception as exc:
        logger.exception("Follow-up request failed")
        error = _default_chat_error(exc)
        try:
            if user_message is None:
                user_message = repository.add_message(
                    {
                        "session_id": request.session_id,
                        "parent_message_id": parent.id if parent else request.parent_message_id,
                        "role": "user",
                        "content": request.message,
                        "mode": response_mode.value,
                        "status": ChatResponseStatus.COMPLETED.value,
                    }
                )
            response = _persist_failed_response(
                session_id=request.session_id,
                parent_message_id=user_message.id,
                mode=response_mode,
                error=error,
            )
        except Exception:
            logger.exception("Failed to persist follow-up failure")
            response = _ephemeral_failed_response(
                session_id=request.session_id,
                mode=response_mode,
                error=error,
            )
        return detection, route, response


def _stream_follow_up(request: ChatFollowUpRequest):
    def generate():
        parent = None
        user_message = None
        response_mode = ChatMode.FOLLOW_UP
        detection = None
        route = None

        try:
            yield sse_payload("analysis_started", {"status": "analyzing"})

            session_summary = repository.get_session_summary(request.session_id)
            parent = _resolve_follow_up_parent(request.session_id, request.parent_message_id)
            local_refined_result = refine_follow_up_from_snapshot(
                parent.result_snapshot if parent else None,
                request.message,
                parent_mode=parent.mode if parent else session_summary.mode if session_summary else None,
            )
            response_mode = (
                ChatMode.FOLLOW_UP
                if local_refined_result is not None
                else ChatMode.COMPARE if is_compare_follow_up(request.message) else ChatMode.FOLLOW_UP
            )

            user_message = repository.add_message(
                {
                    "session_id": request.session_id,
                    "parent_message_id": parent.id if parent else request.parent_message_id,
                    "role": "user",
                    "content": request.message,
                    "mode": response_mode.value,
                    "status": ChatResponseStatus.COMPLETED.value,
                }
            )

            if response_mode == ChatMode.COMPARE:
                yield sse_payload(
                    "mode_detected",
                    {"mode": ChatMode.COMPARE.value, "confidence": 1.0, "source": "follow_up_compare"},
                )
                result = compare_from_snapshot(parent.result_snapshot if parent else None, request.message)
                assistant_message = repository.add_message(
                    {
                        "session_id": request.session_id,
                        "parent_message_id": user_message.id,
                        "role": "assistant",
                        "content": result.summary,
                        "mode": response_mode.value,
                        "skills_used": [],
                        "result_snapshot": result.model_dump(mode="json"),
                        "status": ChatResponseStatus.COMPLETED.value,
                    }
                )
                response = result_to_chat_response(
                    session_id=request.session_id,
                    message_id=assistant_message.id,
                    mode=response_mode,
                    result=result,
                    skills_used=[],
                )
                yield sse_payload("completed", response.model_dump(mode="json"))
                return

            if local_refined_result is not None:
                yield sse_payload(
                    "mode_detected",
                    {"mode": ChatMode.FOLLOW_UP.value, "confidence": 1.0, "source": "follow_up_snapshot_refine"},
                )
                yield sse_payload(
                    "skill_routing_ready",
                    {"strategy": "compare_existing", "skills": []},
                )
                yield sse_payload("partial_result", local_refined_result.model_dump(mode="json"))
                assistant_message = repository.add_message(
                    {
                        "session_id": request.session_id,
                        "parent_message_id": user_message.id,
                        "role": "assistant",
                        "content": local_refined_result.summary,
                        "mode": response_mode.value,
                        "skills_used": [],
                        "result_snapshot": local_refined_result.model_dump(mode="json"),
                        "status": ChatResponseStatus.COMPLETED.value,
                    }
                )
                response = result_to_chat_response(
                    session_id=request.session_id,
                    message_id=assistant_message.id,
                    mode=response_mode,
                    result=local_refined_result,
                    skills_used=[],
                )
                yield sse_payload("completed", response.model_dump(mode="json"))
                return

            profile = repository.get_profile()
            detection, route, contextual_message = plan_follow_up_route(
                request.message,
                parent,
                session_mode=session_summary.mode if session_summary else None,
                profile=profile,
            )
            yield sse_payload(
                "mode_detected",
                {"mode": detection.mode.value, "confidence": detection.confidence, "source": detection.source},
            )
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

            result, skills_used, rewritten_query, user_visible_error, should_enhance = execute_plan_base(
                route,
                profile,
                user_message=contextual_message,
            )
            for skill in skills_used:
                yield sse_payload("skill_finished", skill.model_dump(mode="json"))

            yield sse_payload("partial_result", result.model_dump(mode="json"))
            assistant_message, response = _persist_assistant_response(
                session_id=request.session_id,
                parent_message_id=user_message.id,
                mode=response_mode,
                result=result,
                skills_used=skills_used,
                rewritten_query=rewritten_query,
                user_visible_error=user_visible_error,
            )
            yield sse_payload("completed", response.model_dump(mode="json"))

            enhanced_response = _maybe_build_enhanced_response(
                session_id=request.session_id,
                message_id=assistant_message.id,
                mode=response_mode,
                route=route,
                profile=profile,
                user_message=contextual_message,
                result=result,
                skills_used=skills_used,
                rewritten_query=rewritten_query,
                user_visible_error=user_visible_error,
                should_enhance=should_enhance,
            )
            if enhanced_response is not None:
                yield sse_payload("result_enhanced", enhanced_response.model_dump(mode="json"))
        except Exception as exc:
            logger.exception("Streaming follow-up request failed")
            error = _default_chat_error(exc)
            try:
                if user_message is None:
                    user_message = repository.add_message(
                        {
                            "session_id": request.session_id,
                            "parent_message_id": parent.id if parent else request.parent_message_id,
                            "role": "user",
                            "content": request.message,
                            "mode": response_mode.value,
                            "status": ChatResponseStatus.COMPLETED.value,
                        }
                    )
                response = _persist_failed_response(
                    session_id=request.session_id,
                    parent_message_id=user_message.id,
                    mode=response_mode,
                    error=error,
                )
            except Exception:
                logger.exception("Failed to persist streaming follow-up failure")
                response = _ephemeral_failed_response(
                    session_id=request.session_id,
                    mode=response_mode,
                    error=error,
                )
            payload = response.model_dump(mode="json")
            payload["error"] = error.message
            yield sse_payload("failed", payload)

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
    runtime_skills = [
        {
            "skill_id": spec.skill_id,
            "display_name": spec.display_name,
            "adapter_kind": spec.adapter_kind.value,
            "default_channel": spec.default_channel,
            "asset_path": spec.asset_path,
            "asset_meta": (
                {
                    "slug": spec.asset_meta.slug,
                    "version": spec.asset_meta.version,
                    "owner_id": spec.asset_meta.owner_id,
                    "published_at": spec.asset_meta.published_at,
                    "meta_path": spec.asset_meta.meta_path,
                }
                if spec.asset_meta is not None
                else None
            ),
            "enabled": spec.enabled,
        }
        for spec in skill_registry.all()
    ]
    return {
        "api_base_url": settings.iwencai_base_url,
        "api_key_configured": bool(settings.iwencai_api_key),
        "skill_count": skill_count,
        "runtime_skills": runtime_skills,
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
    if request.stream:
        return _stream_follow_up(request)
    _, _, response = _complete_follow_up(request)
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


@app.get("/api/portfolio/summary", response_model=PortfolioSummary)
def get_portfolio_summary():
    return portfolio_store.summary()


@app.get("/api/portfolio/accounts", response_model=list[PortfolioAccountRecord])
def list_portfolio_accounts():
    return portfolio_store.list_accounts()


@app.post("/api/portfolio/accounts", response_model=PortfolioAccountRecord)
def create_portfolio_account(data: PortfolioAccountCreate):
    if not data.name.strip():
        raise HTTPException(status_code=400, detail="账户名称不能为空")
    return portfolio_store.create_account(data)


@app.patch("/api/portfolio/accounts/{account_id}", response_model=PortfolioAccountRecord)
def update_portfolio_account(account_id: str, update: PortfolioAccountUpdate):
    if update.name is not None and not update.name.strip():
        raise HTTPException(status_code=400, detail="账户名称不能为空")
    account = portfolio_store.update_account(account_id, update)
    if account is None:
        raise HTTPException(status_code=404, detail="Portfolio account not found")
    return account


@app.delete("/api/portfolio/accounts/{account_id}")
def delete_portfolio_account(account_id: str):
    return {"ok": portfolio_store.delete_account(account_id)}


@app.get("/api/portfolio/positions", response_model=list[PortfolioPositionRecord])
def list_portfolio_positions(account_id: Optional[str] = None):
    return portfolio_store.list_positions(account_id=account_id)


@app.post("/api/portfolio/positions", response_model=PortfolioPositionRecord)
def create_portfolio_position(data: PortfolioPositionCreate):
    try:
        return portfolio_store.create_position(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/api/portfolio/positions/{position_id}", response_model=PortfolioPositionRecord)
def update_portfolio_position(position_id: str, update: PortfolioPositionUpdate):
    try:
        position = portfolio_store.update_position(position_id, update)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if position is None:
        raise HTTPException(status_code=404, detail="Portfolio position not found")
    return position


@app.delete("/api/portfolio/positions/{position_id}")
def delete_portfolio_position(position_id: str):
    return {"ok": portfolio_store.delete_position(position_id)}


@app.post("/api/portfolio/import-screenshot", response_model=PortfolioScreenshotImportResponse)
def import_portfolio_screenshot(data: PortfolioScreenshotImportRequest):
    try:
        return portfolio_screenshot_importer.import_screenshot(data)
    except PortfolioScreenshotImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
    item = repository.create_watch_item(prepared)
    watch_rule_store.ensure_default_rule_for_item(item)
    return item


@app.post("/api/watchlist/backfill", response_model=WatchlistBackfillResponse)
def backfill_watchlist_items():
    return backfill_watchlist(repository)


@app.get("/api/monitor/status", response_model=WatchMonitorStatus)
def get_watch_monitor_status():
    return watch_monitor_service.get_status()


@app.get("/api/monitor/rules", response_model=list[MonitorRuleRecord])
def get_watch_monitor_rules(item_id: Optional[str] = None):
    watch_rule_store.ensure_default_rules(repository.list_watchlist())
    return watch_rule_store.list_rules(item_id=item_id)


@app.post("/api/monitor/rules", response_model=MonitorRuleRecord)
def create_watch_monitor_rule(data: MonitorRuleCreate):
    try:
        return watch_rule_store.create_rule(data)
    except WatchRuleStoreError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.patch("/api/monitor/rules/{rule_id}", response_model=MonitorRuleRecord)
def update_watch_monitor_rule(rule_id: str, update: MonitorRuleUpdate):
    rule = watch_rule_store.update_rule(rule_id, update)
    if rule is None:
        raise HTTPException(status_code=404, detail="Monitor rule not found")
    return rule


@app.delete("/api/monitor/rules/{rule_id}")
def delete_watch_monitor_rule(rule_id: str):
    return {"ok": watch_rule_store.delete_rule(rule_id)}


@app.get("/api/monitor/events", response_model=list[WatchMonitorEvent])
def get_watch_monitor_events(limit: int = 20):
    return watch_monitor_service.list_events(limit=limit)


@app.post("/api/monitor/scan", response_model=WatchMonitorScanResponse)
async def trigger_watch_monitor_scan():
    return await watch_monitor_service.scan_once(manual=True)


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
    watch_rule_store.sync_item_metadata(item)
    return item


@app.delete("/api/watchlist/{item_id}")
def delete_watch_item(item_id: str):
    deleted = repository.delete_watch_item(item_id)
    if deleted:
        watch_rule_store.delete_rules_for_item(item_id)
    return {"ok": deleted}
