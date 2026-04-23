from __future__ import annotations

from dataclasses import dataclass, field
from html import unescape
import json
import re
from typing import Any, Dict, List, Optional
import urllib.error
import urllib.parse
import urllib.request


USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)

SINA_SUGGEST_URL = "https://suggest3.sinajs.cn/suggest/type=11,12,13,14,15&key={query}"
REALHEAD_URL = "https://d.10jqka.com.cn/v2/realhead/hs_{code}/last.js"
ORDERBOOK_URL = "https://d.10jqka.com.cn/v2/fiverange/hs_{code}/last.js"
TRADE_DETAIL_URL = "https://d.10jqka.com.cn/v2/exchangedetail/hs_{code}/last12.js"
STOCKPAGE_URL = "https://stockpage.10jqka.com.cn/{code}/"


class LocalMarketSkillError(RuntimeError):
    pass


@dataclass
class ResolvedSecurity:
    code: str
    symbol: str
    name: Optional[str] = None
    exchange: str = ""
    source: str = ""


@dataclass
class LocalRealheadSnapshot:
    code: str
    name: Optional[str] = None
    latest_price: Optional[float] = None
    change_pct: Optional[float] = None
    change_amount: Optional[float] = None
    open_price: Optional[float] = None
    prev_close: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    amount: Optional[float] = None
    volume: Optional[float] = None
    turnover_pct: Optional[float] = None
    amplitude_pct: Optional[float] = None
    pb: Optional[float] = None
    pe_dynamic: Optional[float] = None
    volume_ratio: Optional[float] = None
    total_market_value: Optional[float] = None
    float_market_value: Optional[float] = None
    waipan: Optional[float] = None
    neipan: Optional[float] = None
    weibi: Optional[float] = None
    weicha: Optional[float] = None
    update_time: Optional[str] = None
    stock_status: Optional[str] = None
    market_type: Optional[str] = None

    def to_raw_fields(self) -> Dict[str, Any]:
        return {
            "股票代码": self.code,
            "代码": self.code,
            "股票简称": self.name,
            "名称": self.name,
            "最新价": self.latest_price,
            "最新涨跌幅": self.change_pct,
            "涨跌幅": self.change_pct,
            "涨跌额": self.change_amount,
            "开盘价": self.open_price,
            "前收盘价": self.prev_close,
            "最高价": self.high_price,
            "最低价": self.low_price,
            "成交额": self.amount,
            "成交量": self.volume,
            "换手率": self.turnover_pct,
            "振幅": self.amplitude_pct,
            "量比": self.volume_ratio,
            "动态市盈率": self.pe_dynamic,
            "市净率": self.pb,
            "总市值": self.total_market_value,
            "流通市值": self.float_market_value,
            "外盘": self.waipan,
            "内盘": self.neipan,
            "委差": self.weicha,
            "委比": self.weibi,
            "交易状态": self.stock_status,
            "更新时间": self.update_time,
        }


@dataclass
class LocalOrderBookSnapshot:
    code: str
    bid_prices: List[Optional[float]] = field(default_factory=list)
    bid_volumes: List[Optional[float]] = field(default_factory=list)
    ask_prices: List[Optional[float]] = field(default_factory=list)
    ask_volumes: List[Optional[float]] = field(default_factory=list)
    waipan: Optional[float] = None
    neipan: Optional[float] = None
    weibi: Optional[float] = None
    weicha: Optional[float] = None

    def support_zone(self, depth: int = 3) -> tuple[Optional[float], Optional[float]]:
        valid = [price for price in self.bid_prices[:depth] if price is not None]
        if not valid:
            return None, None
        return min(valid), max(valid)


@dataclass
class LocalTradeDetail:
    time: str
    price: Optional[float] = None
    volume: Optional[float] = None
    direction: str = "flat"


@dataclass
class LocalThemeSnapshot:
    code: str
    name: Optional[str] = None
    region: Optional[str] = None
    themes: List[str] = field(default_factory=list)
    business: Optional[str] = None

    def to_raw_fields(self) -> Dict[str, Any]:
        return {
            "所属地域": self.region,
            "所属概念": "、".join(self.themes) if self.themes else None,
            "主营业务": self.business,
        }


@dataclass
class LocalMarketContext:
    resolved: Optional[ResolvedSecurity] = None
    realhead: Optional[LocalRealheadSnapshot] = None
    order_book: Optional[LocalOrderBookSnapshot] = None
    trades: List[LocalTradeDetail] = field(default_factory=list)
    theme: Optional[LocalThemeSnapshot] = None

    @property
    def has_any(self) -> bool:
        return any((self.realhead, self.order_book, self.trades, self.theme))


def _safe_float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace("%", "").replace(",", "").strip()
        if not cleaned or cleaned in {"--", "-"}:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _normalize_exchange(code: str) -> str:
    if code.startswith(("60", "68", "90")):
        return "SH"
    if code.startswith(("00", "20", "30")):
        return "SZ"
    if code.startswith(("43", "83", "87", "88", "92")) or code.startswith("8"):
        return "BJ"
    return ""


def _normalize_symbol(code: str) -> str:
    exchange = _normalize_exchange(code)
    return f"{code}.{exchange}" if exchange else code


def _clean_text(value: str) -> Optional[str]:
    text = re.sub(r"<[^>]+>", "", unescape(value or ""))
    text = text.replace("\u3000", " ")
    text = re.sub(r"\s+", " ", text).strip(" ：:\n\t")
    if not text or text in {"--", "-"}:
        return None
    return text


def _truncate_text(value: Optional[str], limit: int = 120) -> Optional[str]:
    if not value:
        return None
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


class LocalMarketSkillClient:
    def _get_text(self, url: str, *, referer: str, encoding: str = "utf-8") -> str:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Referer": referer,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return response.read().decode(encoding, errors="replace")
        except urllib.error.HTTPError as exc:
            raise LocalMarketSkillError(f"HTTP {exc.code}: {url}") from exc
        except urllib.error.URLError as exc:
            raise LocalMarketSkillError(f"网络错误: {exc.reason}") from exc

    def _load_jsonp_object(self, url: str, *, referer: str) -> Dict[str, Any]:
        body = self._get_text(url, referer=referer)
        matched = re.search(r"\((.*)\)\s*;?\s*$", body, re.S)
        if not matched:
            raise LocalMarketSkillError("同花顺返回格式异常，未匹配到 JSONP 数据")
        try:
            return json.loads(matched.group(1))
        except json.JSONDecodeError as exc:
            raise LocalMarketSkillError("同花顺返回的 JSONP 解析失败") from exc

    def resolve_security(self, keyword: str) -> ResolvedSecurity:
        text = str(keyword or "").strip()
        if not text:
            raise LocalMarketSkillError("请输入股票名称或代码")

        direct = re.search(r"([0368]\d{5})", text)
        if direct:
            code = direct.group(1)
            return ResolvedSecurity(
                code=code,
                symbol=_normalize_symbol(code),
                exchange=_normalize_exchange(code),
                source="direct_code",
            )

        query = urllib.parse.quote(text)
        body = self._get_text(
            SINA_SUGGEST_URL.format(query=query),
            referer="https://finance.sina.com.cn/",
            encoding="gbk",
        )
        matched = re.search(r'"(.*)"', body)
        if not matched:
            raise LocalMarketSkillError(f"未能解析股票代码：{text}")

        best_match: Optional[ResolvedSecurity] = None
        for item in matched.group(1).split(";"):
            parts = [part.strip() for part in item.split(",")]
            if len(parts) < 4:
                continue
            name = parts[0]
            code = parts[2]
            symbol = parts[3].lower()
            if not re.fullmatch(r"(sh|sz|bj)\d{6}", symbol):
                continue
            exchange = symbol[:2].upper()
            resolved = ResolvedSecurity(
                code=code,
                symbol=f"{code}.{exchange}",
                name=name or None,
                exchange=exchange,
                source="sina_suggest",
            )
            if name == text:
                return resolved
            if best_match is None:
                best_match = resolved

        if best_match is None:
            raise LocalMarketSkillError(f"未找到匹配的 A 股证券：{text}")
        return best_match

    def fetch_realhead(self, code: str) -> LocalRealheadSnapshot:
        normalized_code = self.resolve_security(code).code if not re.fullmatch(r"\d{6}", code) else code
        url = REALHEAD_URL.format(code=normalized_code)
        payload = self._load_jsonp_object(
            url,
            referer=STOCKPAGE_URL.format(code=normalized_code),
        )
        items = payload.get("items") or payload
        if not isinstance(items, dict) or not items:
            raise LocalMarketSkillError("同花顺行情快照返回为空")

        return LocalRealheadSnapshot(
            code=normalized_code,
            name=_clean_text(str(items.get("name") or "")),
            latest_price=_safe_float(items.get("10")),
            change_pct=_safe_float(items.get("199112")),
            change_amount=_safe_float(items.get("264648")),
            open_price=_safe_float(items.get("7")),
            prev_close=_safe_float(items.get("6")),
            high_price=_safe_float(items.get("8")),
            low_price=_safe_float(items.get("9")),
            amount=_safe_float(items.get("19")),
            volume=_safe_float(items.get("13")),
            turnover_pct=_safe_float(items.get("1968584")),
            amplitude_pct=_safe_float(items.get("526792")),
            pb=_safe_float(items.get("592920")),
            pe_dynamic=_safe_float(items.get("2034120")),
            volume_ratio=_safe_float(items.get("1771976")),
            total_market_value=_safe_float(items.get("3541450")),
            float_market_value=_safe_float(items.get("3475914")),
            waipan=_safe_float(items.get("14")),
            neipan=_safe_float(items.get("15")),
            weibi=_safe_float(items.get("461256")),
            weicha=_safe_float(items.get("395720")),
            update_time=_clean_text(str(items.get("updateTime") or items.get("time") or "")),
            stock_status=_clean_text(str(items.get("stockStatus") or "")),
            market_type=_clean_text(str(items.get("marketType") or "")),
        )

    def fetch_order_book(
        self,
        code: str,
        *,
        realhead: Optional[LocalRealheadSnapshot] = None,
    ) -> LocalOrderBookSnapshot:
        normalized_code = self.resolve_security(code).code if not re.fullmatch(r"\d{6}", code) else code
        url = ORDERBOOK_URL.format(code=normalized_code)
        payload = self._load_jsonp_object(
            url,
            referer=STOCKPAGE_URL.format(code=normalized_code),
        )
        items = payload.get("items") or payload
        if not isinstance(items, dict) or not items:
            raise LocalMarketSkillError("同花顺五档盘口返回为空")

        return LocalOrderBookSnapshot(
            code=normalized_code,
            bid_prices=[_safe_float(items.get(key)) for key in ("24", "26", "28", "150", "154")],
            bid_volumes=[_safe_float(items.get(key)) for key in ("25", "27", "29", "151", "155")],
            ask_prices=[_safe_float(items.get(key)) for key in ("30", "32", "34", "152", "156")],
            ask_volumes=[_safe_float(items.get(key)) for key in ("31", "33", "35", "153", "157")],
            waipan=realhead.waipan if realhead else None,
            neipan=realhead.neipan if realhead else None,
            weibi=realhead.weibi if realhead else None,
            weicha=realhead.weicha if realhead else None,
        )

    def fetch_trade_details(self, code: str, *, limit: int = 12) -> List[LocalTradeDetail]:
        normalized_code = self.resolve_security(code).code if not re.fullmatch(r"\d{6}", code) else code
        url = TRADE_DETAIL_URL.format(code=normalized_code)
        payload = self._load_jsonp_object(
            url,
            referer=STOCKPAGE_URL.format(code=normalized_code),
        )
        items = payload.get("items") or []
        if not isinstance(items, list):
            raise LocalMarketSkillError("同花顺逐笔成交返回格式异常")

        details: List[LocalTradeDetail] = []
        for item in items[:limit]:
            if not isinstance(item, dict):
                continue
            direction_flag = _safe_float(item.get("12"))
            if direction_flag is None:
                direction = "flat"
            elif direction_flag > 4:
                direction = "buy"
            elif direction_flag < 4:
                direction = "sell"
            else:
                direction = "flat"
            details.append(
                LocalTradeDetail(
                    time=str(item.get("His") or "").strip(),
                    price=_safe_float(item.get("10")),
                    volume=_safe_float(item.get("49")),
                    direction=direction,
                )
            )
        return details

    def fetch_theme_snapshot(self, code: str) -> LocalThemeSnapshot:
        normalized_code = self.resolve_security(code).code if not re.fullmatch(r"\d{6}", code) else code
        body = self._get_text(
            STOCKPAGE_URL.format(code=normalized_code),
            referer="https://stockpage.10jqka.com.cn/",
        )

        title_match = re.search(r"<title>\s*([^<(]+)\((\d{6})\)", body)
        name = _clean_text(title_match.group(1)) if title_match else None

        region_match = re.search(r"所属地域：</dt>\s*<dd[^>]*>(.*?)</dd>", body, re.S)
        region = _clean_text(region_match.group(1)) if region_match else None

        concept_match = re.search(r"涉及概念：</dt>\s*<dd(?P<attrs>[^>]*)>(?P<body>.*?)</dd>", body, re.S)
        theme_text = None
        if concept_match:
            title_attr = re.search(r'title="([^"]*)"', concept_match.group("attrs"))
            theme_text = title_attr.group(1) if title_attr else concept_match.group("body")
        themes = []
        cleaned_theme_text = _clean_text(theme_text or "")
        if cleaned_theme_text:
            themes = [part.strip() for part in re.split(r"[、,，/]", cleaned_theme_text) if part.strip()][:12]

        business_match = re.search(
            r"主营业务：</dt>\s*(?:<dd[^>]*>.*?</dd>\s*)?<dd(?P<attrs>[^>]*)>(?P<body>.*?)</dd>",
            body,
            re.S,
        )
        business_text = None
        if business_match:
            title_attr = re.search(r'title="([^"]*)"', business_match.group("attrs"))
            business_text = title_attr.group(1) if title_attr else business_match.group("body")

        return LocalThemeSnapshot(
            code=normalized_code,
            name=name,
            region=region,
            themes=themes,
            business=_truncate_text(_clean_text(business_text or ""), limit=180),
        )


local_market_skill_client = LocalMarketSkillClient()
