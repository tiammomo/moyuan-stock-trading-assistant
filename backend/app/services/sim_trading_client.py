from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from threading import RLock
import time
from typing import Any, Dict, List, Optional
import urllib.error
import urllib.parse
import urllib.request

from app.core.config import get_settings


class SimTradingClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class SimTradingAccount:
    username: str
    capital_account: str
    department_id: str
    shareholder_accounts: Dict[str, str] = field(default_factory=dict)
    market_codes: Dict[str, str] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class SimTradingPosition:
    code: str
    name: str
    quantity: int
    available_quantity: int
    cost_price: Optional[float] = None
    market_value: Optional[float] = None
    float_profit: Optional[float] = None
    profit_rate_pct: Optional[float] = None


@dataclass(frozen=True)
class SimTradingHoldingContext:
    account: SimTradingAccount
    opened_now: bool
    positions: List[SimTradingPosition]
    matched_position: Optional[SimTradingPosition]
    total_positions: int
    latency_ms: int
    portfolio_position_pct: Optional[float] = None
    total_assets: Optional[float] = None
    note: str = ""


class SimTradingClient:
    base_url = "http://trade.10jqka.com.cn:8088"
    default_account_file = "default.json"
    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(self) -> None:
        self.settings = get_settings()
        self._lock = RLock()

    @property
    def enabled(self) -> bool:
        return self.settings.sim_trading_enabled

    @property
    def accounts_dir(self) -> Path:
        return self.settings.effective_sim_trading_accounts_dir

    @property
    def account_file(self) -> Path:
        return self.accounts_dir / self.default_account_file

    def query_holding_context(self, subject: str) -> SimTradingHoldingContext:
        if not self.enabled:
            raise SimTradingClientError("模拟炒股 skill 未安装或脚本不完整")

        started = time.perf_counter()
        account, opened_now = self._ensure_account()
        positions_payload = self._query_positions(account)
        positions = self._normalize_positions(positions_payload)
        matched_position = self._match_position(subject, positions)
        profit_info = self._query_profit_info_best_effort(account)

        return SimTradingHoldingContext(
            account=account,
            opened_now=opened_now,
            positions=positions,
            matched_position=matched_position,
            total_positions=len(positions),
            latency_ms=int((time.perf_counter() - started) * 1000),
            portfolio_position_pct=_safe_float(profit_info.get("cw") if profit_info else None),
            total_assets=_safe_float(profit_info.get("zzc") if profit_info else None),
            note="同花顺问财提供模拟炒股服务",
        )

    def _ensure_account(self) -> tuple[SimTradingAccount, bool]:
        with self._lock:
            existing = self._read_account()
            if existing is not None:
                return self._normalize_account(existing), False

            if not self.settings.sim_trading_auto_open:
                raise SimTradingClientError("模拟炒股账户未建立，且 SIM_TRADING_AUTO_OPEN=false")

            account = self._open_account()
            self._write_account(account)
            return self._normalize_account(account), True

    def _read_account(self) -> Optional[Dict[str, Any]]:
        if not self.account_file.exists():
            return None
        try:
            return json.loads(self.account_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise SimTradingClientError(f"读取模拟炒股账户失败: {exc}") from exc

    def _write_account(self, payload: Dict[str, Any]) -> None:
        self.account_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.account_file.with_suffix(f"{self.account_file.suffix}.tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(self.account_file)

    def _open_account(self) -> Dict[str, Any]:
        username = f"skill_{int(time.time() * 1000)}"
        department_id = self.settings.sim_trading_department_id
        create_payload = self._get_json(
            "/pt_add_user",
            {
                "usrname": username,
                "yybid": department_id,
                "datatype": "json",
            },
            error_label="模拟炒股开户",
        )
        capital_account = str(create_payload.get("errormsg") or "").strip()
        if not capital_account:
            raise SimTradingClientError("模拟炒股开户成功但未返回资金账号")

        shareholder_payload = self._get_json(
            "/pt_qry_stkaccount_dklc",
            {
                "usrid": capital_account,
                "yybid": department_id,
                "datatype": "json",
            },
            error_label="模拟炒股股东账号查询",
        )
        shareholder_accounts: Dict[str, str] = {}
        market_codes: Dict[str, str] = {}
        for item in shareholder_payload.get("result", []) or []:
            if not isinstance(item, dict):
                continue
            market_code = str(item.get("scdm") or "").strip()
            shareholder_code = str(item.get("gddm") or "").strip()
            if not market_code or not shareholder_code:
                continue
            if market_code == "1":
                shareholder_accounts["sz"] = shareholder_code
                market_codes["sz"] = market_code
            elif market_code == "2":
                shareholder_accounts["sh"] = shareholder_code
                market_codes["sh"] = market_code

        now = datetime.now(timezone.utc).isoformat()
        return {
            "username": username,
            "capital_account": capital_account,
            "department_id": department_id,
            "shareholder_accounts": shareholder_accounts,
            "market_codes": market_codes,
            "created_at": now,
            "updated_at": now,
        }

    def _query_positions(self, account: SimTradingAccount) -> Dict[str, Any]:
        return self._get_json_any(
            ["/pt_web_qry_stock", "/pt_web_qy_stock"],
            {
                "name": account.capital_account,
                "yybid": account.department_id,
                "type": "1",
                "datatype": "json",
            },
            error_label="模拟炒股持仓查询",
        )

    def _query_profit_info_best_effort(self, account: SimTradingAccount) -> Dict[str, Any]:
        try:
            payload = self._get_json(
                "/pt_qry_userinfo_v1",
                {
                    "usrname": account.username,
                    "yybid": account.department_id,
                    "type": "",
                    "datatype": "json",
                },
                error_label="模拟炒股收益查询",
            )
        except SimTradingClientError:
            return {}

        profit_list = payload.get("list") or []
        return profit_list[0] if profit_list and isinstance(profit_list[0], dict) else {}

    def _get_json_any(
        self,
        paths: List[str],
        params: Dict[str, Any],
        *,
        error_label: str,
    ) -> Dict[str, Any]:
        last_error: Optional[Exception] = None
        for path in paths:
            try:
                return self._get_json(path, params, error_label=error_label)
            except SimTradingClientError as exc:
                last_error = exc
                continue
        raise SimTradingClientError(str(last_error) if last_error else f"{error_label}失败")

    def _get_json(self, path: str, params: Dict[str, Any], *, error_label: str) -> Dict[str, Any]:
        query = urllib.parse.urlencode(params)
        request = urllib.request.Request(
            f"{self.base_url}{path}?{query}",
            headers={"User-Agent": self.user_agent},
            method="GET",
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.settings.sim_trading_timeout_seconds,
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            raise SimTradingClientError(f"{error_label} HTTP {exc.code}: {body[:200]}") from exc
        except urllib.error.URLError as exc:
            raise SimTradingClientError(f"{error_label} 网络错误: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise SimTradingClientError(f"{error_label} 返回非 JSON 数据") from exc

        if not isinstance(payload, dict):
            raise SimTradingClientError(f"{error_label} 返回格式异常")

        error_code = payload.get("errorcode", payload.get("error_no", 0))
        if str(error_code) not in {"0", ""}:
            error_message = payload.get("errormsg") or payload.get("error_info") or "未知错误"
            raise SimTradingClientError(f"{error_label}失败: {error_message}")
        return payload

    def _normalize_account(self, payload: Dict[str, Any]) -> SimTradingAccount:
        username = str(payload.get("username") or "").strip()
        capital_account = str(payload.get("capital_account") or "").strip()
        department_id = str(payload.get("department_id") or self.settings.sim_trading_department_id).strip()
        if not username or not capital_account:
            raise SimTradingClientError("模拟炒股账户信息缺少 username 或 capital_account")
        shareholder_accounts = payload.get("shareholder_accounts")
        market_codes = payload.get("market_codes")
        return SimTradingAccount(
            username=username,
            capital_account=capital_account,
            department_id=department_id,
            shareholder_accounts=shareholder_accounts if isinstance(shareholder_accounts, dict) else {},
            market_codes=market_codes if isinstance(market_codes, dict) else {},
            created_at=str(payload.get("created_at") or ""),
            updated_at=str(payload.get("updated_at") or ""),
        )

    def _normalize_positions(self, payload: Dict[str, Any]) -> List[SimTradingPosition]:
        raw_positions = payload.get("result") or payload.get("list") or payload.get("data") or []
        if not isinstance(raw_positions, list):
            return []

        positions: List[SimTradingPosition] = []
        for item in raw_positions:
            if not isinstance(item, dict):
                continue
            code = str(item.get("zqdm") or item.get("证券代码") or item.get("code") or "").strip()
            name = str(item.get("zqmc") or item.get("证券名称") or item.get("name") or "").strip()
            if not code and not name:
                continue
            positions.append(
                SimTradingPosition(
                    code=code,
                    name=name,
                    quantity=_safe_int(item.get("gpsl") or item.get("股票数量") or item.get("quantity")),
                    available_quantity=_safe_int(item.get("kysl") or item.get("可用数量") or item.get("available_quantity")),
                    cost_price=_safe_float(item.get("gpcb") or item.get("股票成本") or item.get("cost_price")),
                    market_value=_safe_float(item.get("gpz") or item.get("股票市值") or item.get("market_value")),
                    float_profit=_safe_float(item.get("fdyk") or item.get("浮动盈亏") or item.get("float_profit")),
                    profit_rate_pct=_safe_float(item.get("ydl") or item.get("盈亏率") or item.get("profit_rate")),
                )
            )
        return positions

    def _match_position(
        self,
        subject: str,
        positions: List[SimTradingPosition],
    ) -> Optional[SimTradingPosition]:
        normalized_subject = _normalize_security_key(subject)
        for position in positions:
            if _normalize_security_key(position.code) == normalized_subject:
                return position
            if position.code and _normalize_security_key(position.code.split(".")[0]) == normalized_subject:
                return position
            if _normalize_security_key(position.name) == normalized_subject:
                return position
        return None


def _safe_float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        return None
    text = str(value).strip().replace("%", "").replace(",", "")
    if not text or text in {"-", "--"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _safe_int(value: Any) -> int:
    number = _safe_float(value)
    return int(number) if number is not None else 0


def _normalize_security_key(value: str) -> str:
    return "".join(str(value).upper().split()).removesuffix(".SH").removesuffix(".SZ").removesuffix(".BJ")


sim_trading_client = SimTradingClient()
