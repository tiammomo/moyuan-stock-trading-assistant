from __future__ import annotations

import csv
from datetime import datetime, timezone
from io import StringIO
import re
from typing import Dict, List, Optional

from app.schemas.portfolio import (
    PortfolioCsvImportRequest,
    PortfolioCsvImportResponse,
    PortfolioCsvImportRow,
    PortfolioPositionCreate,
    PortfolioPositionLot,
)

from .portfolio_store import portfolio_store


HEADER_ALIASES: Dict[str, str] = {
    "代码": "symbol",
    "股票代码": "symbol",
    "symbol": "symbol",
    "ticker": "symbol",
    "名称": "name",
    "股票名称": "name",
    "name": "name",
    "成本价": "cost_price",
    "成本": "cost_price",
    "cost_price": "cost_price",
    "quantity": "quantity",
    "持仓数量": "quantity",
    "持仓": "quantity",
    "总数量": "quantity",
    "available_quantity": "available_quantity",
    "可用数量": "available_quantity",
    "可用": "available_quantity",
    "frozen_quantity": "frozen_quantity",
    "冻结数量": "frozen_quantity",
    "冻结": "frozen_quantity",
    "industry": "industry",
    "行业": "industry",
    "trading_style": "trading_style",
    "风格": "trading_style",
    "style": "trading_style",
    "note": "note",
    "备注": "note",
    "lots": "lots",
    "分批买入": "lots",
}


class PortfolioCsvImportError(RuntimeError):
    pass


def _clean_text(value: Optional[str]) -> str:
    return " ".join(str(value or "").strip().split())


def _as_int(value: Optional[str]) -> Optional[int]:
    text = _clean_text(value)
    if not text:
        return None
    try:
        return int(float(text.replace(",", "")))
    except ValueError:
        return None


def _as_float(value: Optional[str]) -> Optional[float]:
    text = _clean_text(value)
    if not text:
        return None
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


class PortfolioCsvImporter:
    def import_csv(self, request: PortfolioCsvImportRequest) -> PortfolioCsvImportResponse:
        account = portfolio_store.get_account(request.account_id)
        if account is None:
            raise PortfolioCsvImportError("账户不存在")

        normalized_rows = self._parse_csv_rows(request.csv_text)
        rows: List[PortfolioCsvImportRow] = []
        imported_count = 0
        updated_count = 0
        skipped_count = 0

        for raw_row in normalized_rows:
            symbol = _clean_text(raw_row.get("symbol"))
            quantity = _as_int(raw_row.get("quantity"))
            cost_price = _as_float(raw_row.get("cost_price"))
            if not symbol or quantity is None or quantity <= 0 or cost_price is None or cost_price <= 0:
                rows.append(
                    PortfolioCsvImportRow(
                        symbol=symbol or "--",
                        name=_clean_text(raw_row.get("name")) or None,
                        quantity=max(quantity or 0, 0),
                        cost_price=max(cost_price or 0, 0),
                        action="skipped",
                        reason="missing_required_fields",
                    )
                )
                skipped_count += 1
                continue

            lots = self._parse_lots(raw_row.get("lots"))
            available_quantity = _as_int(raw_row.get("available_quantity"))
            frozen_quantity = _as_int(raw_row.get("frozen_quantity"))
            industry = _clean_text(raw_row.get("industry")) or None
            style = _clean_text(raw_row.get("trading_style")) or request.default_trading_style
            note = _clean_text(raw_row.get("note")) or None
            name = _clean_text(raw_row.get("name")) or None

            if request.dry_run:
                rows.append(
                    PortfolioCsvImportRow(
                        symbol=symbol,
                        name=name,
                        quantity=quantity,
                        available_quantity=available_quantity,
                        frozen_quantity=frozen_quantity,
                        cost_price=cost_price,
                        industry=industry,
                        trading_style=style,  # type: ignore[arg-type]
                        lots=lots,
                        action="preview",
                    )
                )
                continue

            position, was_updated = portfolio_store.upsert_position(
                PortfolioPositionCreate(
                    account_id=request.account_id,
                    symbol=symbol,
                    name=name,
                    cost_price=cost_price,
                    quantity=quantity,
                    available_quantity=available_quantity,
                    frozen_quantity=frozen_quantity,
                    trading_style=style,  # type: ignore[arg-type]
                    industry=industry,
                    note=note,
                    lots=lots,
                ),
                preserve_existing_note=request.preserve_existing_note,
            )
            rows.append(
                PortfolioCsvImportRow(
                    symbol=position.symbol,
                    name=position.name,
                    quantity=position.quantity,
                    available_quantity=position.available_quantity,
                    frozen_quantity=position.frozen_quantity,
                    cost_price=position.cost_price,
                    industry=position.industry,
                    trading_style=position.trading_style,
                    lots=position.lots,
                    action="updated" if was_updated else "created",
                    position_id=position.id,
                )
            )
            if was_updated:
                updated_count += 1
            else:
                imported_count += 1

        return PortfolioCsvImportResponse(
            account_id=account.id,
            account_name=account.name,
            detected_at=datetime.now(timezone.utc),
            parsed_count=len(normalized_rows),
            imported_count=imported_count,
            updated_count=updated_count,
            skipped_count=skipped_count,
            rows=rows,
        )

    def _parse_csv_rows(self, csv_text: str) -> List[Dict[str, str]]:
        text = str(csv_text or "").strip()
        if not text:
            raise PortfolioCsvImportError("CSV 内容不能为空")

        reader = csv.DictReader(StringIO(text))
        if not reader.fieldnames:
            raise PortfolioCsvImportError("CSV 缺少表头")

        normalized_rows: List[Dict[str, str]] = []
        for raw_row in reader:
            normalized: Dict[str, str] = {}
            for key, value in raw_row.items():
                canonical = HEADER_ALIASES.get(_clean_text(key), _clean_text(key))
                if canonical:
                    normalized[canonical] = value or ""
            if any(_clean_text(value) for value in normalized.values()):
                normalized_rows.append(normalized)

        if not normalized_rows:
            raise PortfolioCsvImportError("CSV 未解析到有效行")
        return normalized_rows

    def _parse_lots(self, raw_value: Optional[str]) -> List[PortfolioPositionLot]:
        text = _clean_text(raw_value)
        if not text:
            return []
        parts = [part.strip() for part in re.split(r"[;；|]", text) if part.strip()]
        lots: List[PortfolioPositionLot] = []
        for part in parts:
            acquired_at = None
            descriptor = part
            if "#" in part:
                date_text, descriptor = part.split("#", 1)
                try:
                    acquired_at = datetime.fromisoformat(date_text.strip())
                except ValueError:
                    acquired_at = None
            match = re.fullmatch(r"(\d+)\s*@\s*([0-9.]+)", descriptor.strip())
            if not match:
                continue
            lots.append(
                PortfolioPositionLot(
                    acquired_at=acquired_at,
                    quantity=int(match.group(1)),
                    cost_price=float(match.group(2)),
                )
            )
        return lots


portfolio_csv_importer = PortfolioCsvImporter()
