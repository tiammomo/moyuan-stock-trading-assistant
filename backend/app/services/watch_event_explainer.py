from __future__ import annotations

import json
from typing import Any, Dict, Optional

from app.schemas import MonitorRuleRecord, WatchMonitorEvent

from .llm_manager import LLMProviderError, LLMRequest, llm_provider_manager


class WatchEventExplainer:
    def explain(self, event: WatchMonitorEvent, rule: MonitorRuleRecord) -> Dict[str, Optional[str]]:
        fallback = self._fallback(event, rule)
        if not llm_provider_manager.enabled:
            return fallback

        request = LLMRequest(
            system_prompt=(
                "你是 A 股盯盘事件解释助手。只能基于输入事件、规则和指标解释，不能编造新闻、价格或结论。"
                "输出 JSON：ai_explanation 不超过80字；action_hint 不超过60字。"
            ),
            user_prompt=json.dumps(
                {
                    "event": event.model_dump(mode="json"),
                    "rule": {
                        "rule_name": rule.rule_name,
                        "severity": rule.severity,
                        "condition_group": rule.condition_group.model_dump(mode="json"),
                    },
                },
                ensure_ascii=False,
            ),
            reasoning_effort="medium",
            max_output_tokens=300,
        )
        try:
            result = llm_provider_manager.generate_text(request)
        except LLMProviderError:
            return fallback
        if result is None:
            return fallback
        try:
            payload = json.loads(self._extract_json(result.text))
        except (json.JSONDecodeError, ValueError):
            return fallback
        return {
            "ai_explanation": self._clean(payload.get("ai_explanation")) or fallback["ai_explanation"],
            "action_hint": self._clean(payload.get("action_hint")) or fallback["action_hint"],
        }

    def _fallback(self, event: WatchMonitorEvent, rule: MonitorRuleRecord) -> Dict[str, Optional[str]]:
        change_pct = event.metrics.get("change_pct")
        volume_ratio = event.metrics.get("volume_ratio")
        intraday_position = event.metrics.get("intraday_position_pct")
        anchors = []
        if isinstance(change_pct, (int, float)):
            anchors.append(f"涨跌幅 {change_pct:+.2f}%")
        if isinstance(volume_ratio, (int, float)):
            anchors.append(f"量比 {volume_ratio:.2f}")
        if isinstance(intraday_position, (int, float)):
            anchors.append(f"日内位置 {intraday_position:.0f}%")
        anchor_text = "，".join(anchors) or "核心指标已触发"
        return {
            "ai_explanation": f"{anchor_text}，说明「{rule.rule_name}」关注的条件已经出现，需要结合分时承接确认。",
            "action_hint": "先确认量价是否延续；若快速回落或放量滞涨，降低追高动作。",
        }

    def _extract_json(self, text: str) -> str:
        stripped = text.strip()
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("no json")
        return stripped[start : end + 1]

    def _clean(self, value: Any) -> Optional[str]:
        if not isinstance(value, str):
            return None
        text = " ".join(value.split()).strip()
        return text[:160] or None


watch_event_explainer = WatchEventExplainer()
