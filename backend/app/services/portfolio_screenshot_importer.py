from __future__ import annotations

from base64 import b64decode
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
import socket
from typing import Any, Dict, List, Optional
import urllib.error
import urllib.request

from app.schemas.portfolio import (
    PortfolioPositionCreate,
    PortfolioBrokerTemplate,
    PortfolioScreenshotImportRequest,
    PortfolioScreenshotImportResponse,
    PortfolioScreenshotImportRow,
)

from .llm_account_pool import LLMAccount, llm_account_pool
from .local_market_skill_client import LocalMarketSkillError, local_market_skill_client
from .portfolio_store import portfolio_store


class PortfolioScreenshotImportError(RuntimeError):
    pass


@dataclass(frozen=True)
class ParsedHoldingRow:
    name: str
    quantity: int
    available_quantity: Optional[int]
    cost_price: float
    latest_price: Optional[float]
    market_value: Optional[float]
    pnl_amount: Optional[float]
    pnl_pct: Optional[float]


class PortfolioScreenshotImporter:
    def import_screenshot(
        self,
        request: PortfolioScreenshotImportRequest,
    ) -> PortfolioScreenshotImportResponse:
        account = portfolio_store.get_account(request.account_id)
        if account is None:
            raise PortfolioScreenshotImportError("账户不存在")

        if request.parsed_rows:
            raw_rows = [row.model_dump(mode="json") for row in request.parsed_rows]
            broker_name = request.broker_name
        else:
            if not request.image_data_url:
                raise PortfolioScreenshotImportError("缺少截图数据")
            payload = self._parse_data_url(request.image_data_url)
            raw_rows, broker_name = self._extract_rows_with_vision(
                payload["mime"],
                payload["base64"],
                broker_template=request.broker_template,
            )
        rows: List[PortfolioScreenshotImportRow] = []
        imported_count = 0
        updated_count = 0
        skipped_count = 0

        for raw_row in raw_rows:
            normalized = self._normalize_row(raw_row)
            if normalized is None:
                skipped_count += 1
                continue

            if request.skip_zero_quantity and normalized.quantity <= 0:
                rows.append(
                    PortfolioScreenshotImportRow(
                        name=normalized.name,
                        quantity=normalized.quantity,
                        available_quantity=normalized.available_quantity,
                        cost_price=normalized.cost_price,
                        latest_price=normalized.latest_price,
                        market_value=normalized.market_value,
                        pnl_amount=normalized.pnl_amount,
                        pnl_pct=normalized.pnl_pct,
                        action="skipped",
                        reason="quantity_zero",
                    )
                )
                skipped_count += 1
                continue

            symbol = self._resolve_symbol(normalized.name)
            if symbol is None:
                rows.append(
                    PortfolioScreenshotImportRow(
                        name=normalized.name,
                        quantity=normalized.quantity,
                        available_quantity=normalized.available_quantity,
                        cost_price=normalized.cost_price,
                        latest_price=normalized.latest_price,
                        market_value=normalized.market_value,
                        pnl_amount=normalized.pnl_amount,
                        pnl_pct=normalized.pnl_pct,
                        action="skipped",
                        reason="resolve_symbol_failed",
                    )
                )
                skipped_count += 1
                continue

            if request.dry_run:
                rows.append(
                    PortfolioScreenshotImportRow(
                        name=normalized.name,
                        symbol=symbol,
                        quantity=normalized.quantity,
                        available_quantity=normalized.available_quantity,
                        cost_price=normalized.cost_price,
                        latest_price=normalized.latest_price,
                        market_value=normalized.market_value,
                        pnl_amount=normalized.pnl_amount,
                        pnl_pct=normalized.pnl_pct,
                        action="preview",
                    )
                )
                continue

            position, was_updated = portfolio_store.upsert_position(
                PortfolioPositionCreate(
                    account_id=request.account_id,
                    symbol=symbol,
                    name=normalized.name,
                    cost_price=normalized.cost_price,
                    quantity=normalized.quantity,
                    trading_style="swing",
                    note="截图导入",
                ),
                preserve_existing_note=True,
            )
            rows.append(
                PortfolioScreenshotImportRow(
                    name=normalized.name,
                    symbol=position.symbol,
                    quantity=normalized.quantity,
                    available_quantity=normalized.available_quantity,
                    cost_price=normalized.cost_price,
                    latest_price=normalized.latest_price,
                    market_value=normalized.market_value,
                    pnl_amount=normalized.pnl_amount,
                    pnl_pct=normalized.pnl_pct,
                    action="updated" if was_updated else "created",
                    position_id=position.id,
                )
            )
            if was_updated:
                updated_count += 1
            else:
                imported_count += 1

        return PortfolioScreenshotImportResponse(
            account_id=account.id,
            account_name=account.name,
            broker_name=broker_name,
            detected_at=datetime.now(timezone.utc),
            parsed_count=len(raw_rows),
            imported_count=imported_count,
            updated_count=updated_count,
            skipped_count=skipped_count,
            rows=rows,
        )

    def _parse_data_url(self, image_data_url: str) -> Dict[str, str]:
        matched = re.fullmatch(
            r"data:(image/[a-zA-Z0-9.+-]+);base64,([A-Za-z0-9+/=]+)",
            image_data_url.strip(),
        )
        if not matched:
            raise PortfolioScreenshotImportError("截图数据格式无效")
        mime_type = matched.group(1)
        encoded = matched.group(2)
        try:
            b64decode(encoded, validate=True)
        except ValueError as exc:
            raise PortfolioScreenshotImportError("截图数据无法解码") from exc
        return {"mime": mime_type, "base64": encoded}

    def _extract_rows_with_vision(
        self,
        mime_type: str,
        image_base64: str,
        *,
        broker_template: PortfolioBrokerTemplate,
    ) -> tuple[List[Dict[str, Any]], Optional[str]]:
        accounts = llm_account_pool.ordered_accounts("openai")
        if not accounts:
            raise PortfolioScreenshotImportError("未配置可用的 OpenAI 多模态账号，无法解析截图")

        last_error: Optional[Exception] = None
        for account in accounts:
            try:
                return self._extract_rows_with_account(
                    account,
                    mime_type,
                    image_base64,
                    broker_template=broker_template,
                )
            except PortfolioScreenshotImportError as exc:
                last_error = exc
                continue

        raise PortfolioScreenshotImportError(str(last_error) if last_error else "截图识别失败")

    def _extract_rows_with_account(
        self,
        account: LLMAccount,
        mime_type: str,
        image_base64: str,
        *,
        broker_template: PortfolioBrokerTemplate,
    ) -> tuple[List[Dict[str, Any]], Optional[str]]:
        payload = {
            "model": account.model,
            "reasoning": {"effort": "medium"},
            "max_output_tokens": 1800,
            "input": [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": self._build_vision_system_prompt(broker_template),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "请识别这张中国券商持仓截图，返回结构化 JSON。",
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:{mime_type};base64,{image_base64}",
                        },
                    ],
                },
            ],
        }
        request = urllib.request.Request(
            f"{account.base_url}/responses",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {account.auth_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=account.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (TimeoutError, socket.timeout) as exc:
            raise PortfolioScreenshotImportError("截图识别请求超时") from exc
        except urllib.error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            raise PortfolioScreenshotImportError(f"截图识别接口异常: HTTP {exc.code} {message[:200]}") from exc
        except urllib.error.URLError as exc:
            raise PortfolioScreenshotImportError(f"截图识别网络错误: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise PortfolioScreenshotImportError("截图识别返回非 JSON") from exc

        text = self._extract_output_text(body)
        payload_text = self._extract_json_object_text(text)
        try:
            parsed = json.loads(payload_text)
        except json.JSONDecodeError as exc:
            raise PortfolioScreenshotImportError("截图识别结果无法解析为 JSON") from exc
        if not isinstance(parsed, dict):
            raise PortfolioScreenshotImportError("截图识别结果格式错误")
        rows = parsed.get("rows")
        if not isinstance(rows, list):
            raise PortfolioScreenshotImportError("截图识别结果缺少 rows")
        broker_name = parsed.get("broker_name")
        return rows, broker_name if isinstance(broker_name, str) and broker_name.strip() else None

    def _extract_output_text(self, body: Dict[str, Any]) -> str:
        output_text = body.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        texts: List[str] = []
        for item in body.get("output", []):
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []):
                if not isinstance(content, dict):
                    continue
                text = content.get("text")
                if content.get("type") in {"output_text", "text"} and isinstance(text, str):
                    texts.append(text)
        text = "\n".join(texts).strip()
        if not text:
            raise PortfolioScreenshotImportError("截图识别未返回文本内容")
        return text

    def _extract_json_object_text(self, raw_text: str) -> str:
        text = raw_text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise PortfolioScreenshotImportError("截图识别结果中未找到 JSON 对象")
        return text[start : end + 1]

    def _normalize_row(self, raw_row: Any) -> Optional[ParsedHoldingRow]:
        if not isinstance(raw_row, dict):
            return None
        name = str(raw_row.get("name") or "").strip()
        quantity = self._safe_int(raw_row.get("quantity"))
        cost_price = self._safe_float(raw_row.get("cost_price"))
        if not name or quantity is None or cost_price is None:
            return None
        return ParsedHoldingRow(
            name=name,
            quantity=quantity,
            available_quantity=self._safe_int(raw_row.get("available_quantity")),
            cost_price=cost_price,
            latest_price=self._safe_float(raw_row.get("latest_price")),
            market_value=self._safe_float(raw_row.get("market_value")),
            pnl_amount=self._safe_float(raw_row.get("pnl_amount")),
            pnl_pct=self._safe_float(raw_row.get("pnl_pct")),
        )

    def _build_vision_system_prompt(self, broker_template: PortfolioBrokerTemplate) -> str:
        base_prompt = (
            "你是证券持仓截图结构化抽取器。"
            "只提取当前截图里真正可见的持仓行。"
            "输出必须是 JSON 对象，格式为 "
            "{\"broker_name\": string|null, \"rows\": ["
            "{\"name\": string, \"quantity\": number, \"available_quantity\": number|null, "
            "\"cost_price\": number, \"latest_price\": number|null, \"market_value\": number|null, "
            "\"pnl_amount\": number|null, \"pnl_pct\": number|null}"
            "]}"
            "。"
            "不要补全截图中没有出现的股票。"
            "不要输出 markdown 或解释。"
            "如果某列缺失，给 null。"
            "数量优先取‘持仓/可用’中的持仓数量。"
            "成本价优先取‘成本/现价’中的成本价。"
            "如果一行是已清仓股票，数量通常为 0。"
        )
        template_hints: Dict[PortfolioBrokerTemplate, str] = {
            "auto": (
                "先识别券商名称和页面模板，再按最匹配的模板抽取。"
                "中国券商持仓页常见列是 市值/盈亏/持仓可用/成本现价。"
            ),
            "generic_cn": "按中国 A 股券商通用模板抽取，重点识别 市值、盈亏、持仓/可用、成本/现价 四列。",
            "tonghuashun": (
                "这是同花顺交易持仓模板。常见顶部含 买入/卖出/撤单/持仓/查询 标签。"
                "每一行一般是 股票名+市值、盈亏金额+盈亏比例、持仓/可用、成本/现价。"
            ),
            "guotai_haitong": (
                "这是国泰海通证券交易持仓模板。顶部常见 国泰海通证券 和 买入/卖出/撤单/持仓/查询。"
                "每一行依次重点识别 股票名+市值、盈亏金额+盈亏比例、持仓/可用、成本/现价。"
            ),
            "eastmoney": (
                "这是东方财富交易持仓模板。常见字段顺序也接近 股票名称、市值、盈亏、持仓/可用、成本/现价。"
            ),
            "huatai": "这是华泰证券持仓模板，优先按 股票名、市值、盈亏、持仓/可用、成本/现价 抽取。",
            "pingan": "这是平安证券持仓模板，优先按 股票名、市值、盈亏、持仓/可用、成本/现价 抽取。",
        }
        return base_prompt + template_hints.get(broker_template, template_hints["auto"])

    def _resolve_symbol(self, name: str) -> Optional[str]:
        try:
            resolved = local_market_skill_client.resolve_security(name)
        except LocalMarketSkillError:
            return None
        return resolved.symbol or None

    def _safe_float(self, value: Any) -> Optional[float]:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = value.replace(",", "").replace("%", "").strip()
            if not cleaned:
                return None
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None

    def _safe_int(self, value: Any) -> Optional[int]:
        number = self._safe_float(value)
        if number is None:
            return None
        return int(round(number))


portfolio_screenshot_importer = PortfolioScreenshotImporter()
