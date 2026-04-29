from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Dict, Optional

from app.core.config import get_settings
from app.schemas import ScheduledReportType

from .llm_manager import LLMProviderError, LLMRequest, llm_provider_manager


@dataclass(frozen=True)
class ScheduledReportEnhancement:
    title: str
    summary: str
    body: str
    provider: str


class ScheduledReportLLMEnhancer:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def enabled(self) -> bool:
        return llm_provider_manager.enabled

    def enhance_report(
        self,
        *,
        report_type: ScheduledReportType,
        title: str,
        summary: str,
        body: str,
        payload: Dict[str, Any],
    ) -> Optional[ScheduledReportEnhancement]:
        if not self.enabled:
            return None

        request = LLMRequest(
            system_prompt=self._build_system_prompt(report_type),
            user_prompt=json.dumps(
                {
                    "report_type": report_type,
                    "title": title,
                    "summary": summary,
                    "body": body,
                    "payload": payload,
                    "output_contract": {
                        "title": "string，沿用原日报类型，不要杜撰全新主题，最多18字",
                        "summary": "string，1-2句，先给结论，再给动作或风险，不超过120字",
                        "body": self._body_contract(report_type),
                    },
                },
                ensure_ascii=False,
            ),
            reasoning_effort="medium",
            max_output_tokens=1400,
        )

        result = llm_provider_manager.generate_text(request)
        if result is None:
            return None
        payload = self._parse_json_payload(result.text)
        normalized = self._normalize_payload(report_type, payload)
        if normalized is None:
            return None
        return ScheduledReportEnhancement(
            title=normalized["title"],
            summary=normalized["summary"],
            body=normalized["body"],
            provider=result.provider,
        )

    def _build_system_prompt(self, report_type: ScheduledReportType) -> str:
        type_prompt = {
            "pre_market_watchlist": (
                "这是盘前简报。必须严格输出四段，且每段分别以“今天怎么看：”“先盯谁：”“哪些风险：”“开盘怎么做：”开头。"
            ),
            "post_market_review": (
                "这是盘后复盘。必须严格输出四段，且每段分别以“今天发生了什么：”“哪些最关键：”“明天看什么：”“哪些先回避：”开头。"
            ),
            "portfolio_daily": (
                "这是持仓日报。先给账户总体结论，再指出重点仓位、风险暴露和下一步处理。"
            ),
            "news_digest": (
                "这是新闻摘要。先给催化主线，再说明哪些消息值得继续核实。"
            ),
        }[report_type]
        return "\n".join(
            [
                self.settings.effective_llm_system_prompt,
                type_prompt,
                (
                    "你正在为 A 股本地交易助手重写日报。"
                    "你的职责是把现有规则化日报改写成更像交易员复盘/晨会简报的文字。"
                    "绝对不能编造事实、价格、涨跌幅、新闻标题、账户数据、规则事件。"
                    "只能基于输入里的 title、summary、body、payload 重写。"
                    "如果信息不足，就明确说信息不足，不要补脑。"
                    "summary 必须有明确结论，不能只是复述。"
                    "body 必须保留原始数据锚点，但允许重组顺序、压缩重复、补上过渡句。"
                    "body 不要用 Markdown 标题、编号、项目符号，只输出纯文本分段。"
                    "若 report_type 是盘前或盘后，你必须严格遵守对应四段标题，不允许改标题名字。"
                    "每一段都要对真实交易动作有帮助，避免空话和模板腔。"
                    "输出必须是 JSON 对象，不要代码块。"
                ),
            ]
        )

    def _body_contract(self, report_type: ScheduledReportType) -> str:
        if report_type == "pre_market_watchlist":
            return (
                "string，恰好4段，分别以“今天怎么看：”“先盯谁：”“哪些风险：”“开盘怎么做：”开头，"
                "每段单独换行，写成交易晨会简报，不要 markdown 列表符号"
            )
        if report_type == "post_market_review":
            return (
                "string，恰好4段，分别以“今天发生了什么：”“哪些最关键：”“明天看什么：”“哪些先回避：”开头，"
                "每段单独换行，写成交易复盘简报，不要 markdown 列表符号"
            )
        return "string，4-8段，每段单独换行，写成真正的交易简报，不要 markdown 列表符号"

    def _parse_json_payload(self, raw_text: str) -> Dict[str, Any]:
        text = raw_text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("日报 AI 返回内容中未找到 JSON 对象")
        payload = json.loads(text[start : end + 1])
        if not isinstance(payload, dict):
            raise ValueError("日报 AI 返回的根节点不是对象")
        return payload

    def _normalize_payload(
        self,
        report_type: ScheduledReportType,
        payload: Dict[str, Any],
    ) -> Optional[Dict[str, str]]:
        title = " ".join(str(payload.get("title") or "").split()).strip()
        summary = self._normalize_text_block(payload.get("summary"))
        body = self._normalize_body(report_type, payload.get("body"))
        if not title or not summary or not body:
            return None
        return {
            "title": title[:18],
            "summary": summary[:220],
            "body": body[:1600],
        }

    def _normalize_text_block(self, value: Any) -> str:
        if not isinstance(value, str):
            return ""
        return " ".join(value.split()).strip()

    def _normalize_body(self, report_type: ScheduledReportType, value: Any) -> str:
        if not isinstance(value, str):
            return ""
        blocks = []
        for raw_block in re.split(r"\n\s*\n", value):
            block = " ".join(raw_block.split()).strip()
            if block:
                blocks.append(block)
        required_sections = self._required_sections(report_type)
        if not required_sections:
            return "\n\n".join(blocks)

        normalized_blocks: list[str] = []
        for section in required_sections:
            matched = next((block for block in blocks if block.startswith(section)), None)
            if matched is None:
                return ""
            normalized_blocks.append(matched)
        return "\n\n".join(normalized_blocks)

    def _required_sections(self, report_type: ScheduledReportType) -> list[str]:
        if report_type == "pre_market_watchlist":
            return [
                "今天怎么看：",
                "先盯谁：",
                "哪些风险：",
                "开盘怎么做：",
            ]
        if report_type == "post_market_review":
            return [
                "今天发生了什么：",
                "哪些最关键：",
                "明天看什么：",
                "哪些先回避：",
            ]
        return []


scheduled_report_llm_enhancer = ScheduledReportLLMEnhancer()
