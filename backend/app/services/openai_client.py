from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from typing import Any, Dict, List, Optional

from app.schemas import CardType, ChatMode, ResultCard, StructuredResult

from app.core.config import get_settings
from .llm_manager import LLMProviderError, LLMRequest, llm_provider_manager


OpenAIClientError = LLMProviderError


@dataclass
class AnalysisEnhancement:
    summary: Optional[str] = None
    judgements: List[str] = field(default_factory=list)
    follow_ups: List[str] = field(default_factory=list)
    operation_guidance_content: Optional[str] = None


class OpenAIAnalysisClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def enabled(self) -> bool:
        return llm_provider_manager.enabled

    def enhance_result(
        self,
        *,
        user_message: str,
        mode: ChatMode,
        result: StructuredResult,
        subject: Optional[str] = None,
        entry_price_focus: bool = False,
        reasoning_effort: Optional[str] = None,
    ) -> Optional[AnalysisEnhancement]:
        if not self.enabled or not result.sources:
            return None

        system_prompt = self._build_system_prompt(mode=mode, entry_price_focus=entry_price_focus)

        prompt_payload = {
            "user_message": user_message,
            "mode": mode.value,
            "subject": subject,
            "entry_price_focus": entry_price_focus,
            "structured_result": {
                "summary": result.summary,
                "facts": result.facts,
                "judgements": result.judgements,
                "follow_ups": result.follow_ups,
                "cards": [
                    {
                        "type": self._card_type_value(card),
                        "title": card.title,
                        "content": card.content,
                        "metadata": card.metadata,
                    }
                    for card in result.cards
                ],
                "table": result.table.model_dump(mode="json") if result.table else None,
                "sources": [source.model_dump(mode="json") for source in result.sources],
            },
            "output_contract": {
                "summary": "string, 1-2句话，直接回答用户问题，不超过90字",
                "judgements": ["string", "2-4条，每条一句"],
                "follow_ups": ["string", "恰好3条，都是用户下一步可直接点击的追问"],
                "operation_guidance_content": "string|null，只有存在操作建议卡时才返回字符串",
            },
            "style_contract": {
                "summary_must_reference_data_anchor": True,
                "mention_one_catalyst_if_available": True,
                "avoid_generic_phrases_without_reason": True,
            },
        }

        request = LLMRequest(
            system_prompt=system_prompt,
            user_prompt=json.dumps(prompt_payload, ensure_ascii=False),
            reasoning_effort=reasoning_effort,
            max_output_tokens=1200,
        )
        chain = llm_provider_manager.resolve_chain()
        if not chain:
            return None

        last_error: Optional[Exception] = None
        for provider in chain:
            try:
                text = provider.generate_text(request)
                payload = self._parse_json_payload(text)
                return self._normalize_enhancement(payload, result.cards)
            except (LLMProviderError, ValueError) as exc:
                last_error = exc
                continue

        if last_error is None:
            return None
        raise OpenAIClientError(str(last_error)) from last_error

    def _build_system_prompt(self, *, mode: ChatMode, entry_price_focus: bool) -> str:
        mode_prompt = self._mode_subprompt(mode)
        fallback_mode_hint = {
            ChatMode.GENERIC_DATA_QUERY: "当前问法偏数据查询，优先把结论落到查询结果本身，不要硬凹交易建议。",
            ChatMode.FOLLOW_UP: "当前问法是上一轮结果的追问，回答要紧贴已有结果，不要另起炉灶。",
            ChatMode.COMPARE: "当前问法偏比较，优先说明谁更强、差在哪、适合什么节奏。",
        }.get(mode, "")
        extra_focus = (
            "当前用户明确在问买点或价位，优先回答能不能追、更好的买点、失效条件和止损/观察位。"
            if entry_price_focus
            else ""
        )
        contract_prompt = (
            "你当前处于问财结构化结果后的分析增强层。"
            "你的职责是把现有规则化结果改写得更自然、更像真实交易复盘，但不能编造任何事实、价格、新闻、指标或来源。"
            "不要输出模板腔，不要重复“模式已完成”“已完成分析”这类句式。"
            "先回答用户最关心的结论，再补风险边界。"
            "如果数据不足，就明确说观察，不要假装确定。"
            "如果 facts 或 cards 里已经有价格、涨跌幅、资金、行业、概念、新闻、公告，你必须至少引用一个数据锚点；"
            "如果 facts 或 cards 里已经有 K 线、均线、MACD、RSI、KDJ、布林带、量比这些技术指标，你也必须至少引用一个技术锚点；"
            "如果有新闻或公告标题，优先点出一个最值得盯的催化或风险点，不要只说泛化判断。"
            "禁止输出‘先观察更稳’这类空话，除非后面紧跟具体原因。"
            "单股问题如果结果里已经有“三周期分析”卡，你在 summary 或 judgements 里必须点到短线、中线、长线里的至少两个周期，不能只复述单一周期。"
            "judgements 里的每一条都必须比 summary 多提供一个新信息点，不允许换个说法重复同一句。"
            "follow_ups 之间不能语义重复，也不要把 summary 原句改成问句。"
            "你只能改写以下字段：summary、judgements、follow_ups、operation_guidance_content。"
            "不要改写表格、sources、facts、card metadata。"
            "若存在操作建议卡，operation_guidance_content 必须严格保留四行，且每行分别以"
            "“现在能不能追：”“更好的买点：”“失效条件：”“止损/观察位：”开头。"
            "如果原卡里已经有价格，请在改写时保留这些价格数字，不得新编价格。"
            "输出必须是 JSON 对象，不要 Markdown，不要代码块。"
        )
        parts = [
            self.settings.effective_llm_system_prompt,
            mode_prompt or fallback_mode_hint,
            extra_focus,
            contract_prompt,
        ]
        return "\n".join(part for part in parts if part)

    def _mode_subprompt(self, mode: ChatMode) -> str:
        if mode == ChatMode.SHORT_TERM:
            return self.settings.effective_llm_mode_prompt("short_term")
        if mode == ChatMode.SWING:
            return self.settings.effective_llm_mode_prompt("swing")
        if mode == ChatMode.MID_TERM_VALUE:
            return self.settings.effective_llm_mode_prompt("mid_term_value")
        return ""

    def _parse_json_payload(self, raw_text: str) -> Dict[str, Any]:
        text = raw_text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("LLM 返回内容中未找到 JSON 对象")

        try:
            payload = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ValueError("LLM 返回的 JSON 无法解析") from exc
        if not isinstance(payload, dict):
            raise ValueError("LLM 返回的根节点不是对象")
        return payload

    def _normalize_enhancement(
        self,
        payload: Dict[str, Any],
        cards: List[ResultCard],
    ) -> AnalysisEnhancement:
        summary = payload.get("summary")
        if not isinstance(summary, str):
            summary = None
        elif not summary.strip():
            summary = None
        else:
            summary = self._normalize_summary_text(summary)[:220]

        judgements = self._normalize_string_list(payload.get("judgements"), limit=4)
        follow_ups = self._normalize_string_list(payload.get("follow_ups"), limit=3)
        operation_guidance_content = self._normalize_operation_guidance_content(
            payload.get("operation_guidance_content"),
            cards,
        )

        return AnalysisEnhancement(
            summary=summary,
            judgements=judgements,
            follow_ups=follow_ups,
            operation_guidance_content=operation_guidance_content,
        )

    def _normalize_summary_text(self, text: str) -> str:
        blocks: List[str] = []
        for raw_block in re.split(r"\n\s*\n", text or ""):
            block = " ".join(raw_block.split()).strip()
            if block:
                blocks.append(block)
        return "\n\n".join(blocks)

    def _card_type_value(self, card: ResultCard) -> str:
        return card.type.value if isinstance(card.type, CardType) else str(card.type)

    def _normalize_string_list(self, value: Any, *, limit: int) -> List[str]:
        if not isinstance(value, list):
            return []
        items: List[str] = []
        for item in value:
            if not isinstance(item, str):
                continue
            text = " ".join(item.split())
            if not text:
                continue
            items.append(text[:120])
            if len(items) >= limit:
                break
        return items

    def _normalize_operation_guidance_content(
        self,
        value: Any,
        cards: List[ResultCard],
    ) -> Optional[str]:
        if not isinstance(value, str) or not value.strip():
            return None

        current_card = next(
            (
                card
                for card in cards
                if self._card_type_value(card) == CardType.OPERATION_GUIDANCE.value
            ),
            None,
        )
        if current_card is None:
            return None

        required_prefixes = [
            "现在能不能追：",
            "更好的买点：",
            "失效条件：",
            "止损/观察位：",
        ]
        seen: Dict[str, str] = {}
        for raw_line in value.splitlines():
            line = raw_line.strip()
            for prefix in required_prefixes:
                if line.startswith(prefix):
                    seen[prefix] = line
                    break

        if any(prefix not in seen for prefix in required_prefixes):
            return None

        metadata_numbers = []
        for key in ("observe_low", "observe_high", "stop_price"):
            raw_number = current_card.metadata.get(key)
            if isinstance(raw_number, (int, float)):
                metadata_numbers.append(f"{float(raw_number):.2f}")
        normalized = "\n".join(seen[prefix] for prefix in required_prefixes)
        if metadata_numbers and not all(number in normalized for number in metadata_numbers):
            return None
        return normalized


openai_analysis_client = OpenAIAnalysisClient()
