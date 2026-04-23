from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import json
from pathlib import Path
from typing import Dict, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[3]


class SkillAdapterKind(str, Enum):
    WENCAI_QUERY = "wencai_query"
    WENCAI_SEARCH = "wencai_search"
    LOCAL_REALHEAD = "local_realhead"
    LOCAL_ORDERBOOK = "local_orderbook"
    LOCAL_THEME = "local_theme"


@dataclass(frozen=True)
class SkillAssetMeta:
    slug: Optional[str] = None
    version: Optional[str] = None
    owner_id: Optional[str] = None
    published_at: Optional[int] = None
    meta_path: Optional[str] = None


@dataclass(frozen=True)
class SkillSpec:
    skill_id: str
    display_name: str
    adapter_kind: SkillAdapterKind
    default_channel: Optional[str] = None
    asset_path: Optional[str] = None
    asset_meta: Optional[SkillAssetMeta] = None
    enabled: bool = True


class UnknownSkillError(KeyError):
    pass


def _optional_str(value: object) -> Optional[str]:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _optional_int(value: object) -> Optional[int]:
    if isinstance(value, int):
        return value
    return None


def _load_asset_meta(asset_path: Optional[str]) -> Optional[SkillAssetMeta]:
    if not asset_path:
        return None

    meta_path = REPO_ROOT / asset_path / "_meta.json"
    if not meta_path.exists():
        return None

    try:
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return None

    return SkillAssetMeta(
        slug=_optional_str(payload.get("slug")),
        version=_optional_str(payload.get("version")),
        owner_id=_optional_str(payload.get("ownerId")),
        published_at=_optional_int(payload.get("publishedAt")),
        meta_path=str(meta_path.relative_to(REPO_ROOT)),
    )


SKILL_WENCAI_SECTOR_SCREEN = "wencai.sector_screen"
SKILL_WENCAI_STOCK_SCREEN = "wencai.stock_screen"
SKILL_WENCAI_MARKET_QUERY = "wencai.market_query"
SKILL_WENCAI_INDUSTRY_QUERY = "wencai.industry_query"
SKILL_WENCAI_FINANCIAL_QUERY = "wencai.financial_query"
SKILL_WENCAI_SHAREHOLDER_QUERY = "wencai.shareholder_query"
SKILL_WENCAI_SINGLE_SECURITY_SNAPSHOT = "wencai.single_security_snapshot"
SKILL_WENCAI_SINGLE_SECURITY_FUNDAMENTAL = "wencai.single_security_fundamental"
SKILL_SEARCH_NEWS = "search.news"
SKILL_SEARCH_ANNOUNCEMENT = "search.announcement"
SKILL_SEARCH_REPORT = "search.report"
SKILL_LOCAL_REALHEAD = "local.realhead"
SKILL_LOCAL_ORDERBOOK = "local.orderbook"
SKILL_LOCAL_THEME = "local.theme"


class SkillRegistry:
    def __init__(self, specs: List[SkillSpec]) -> None:
        self._specs: Dict[str, SkillSpec] = {}
        for spec in specs:
            hydrated = replace(spec, asset_meta=_load_asset_meta(spec.asset_path))
            self._specs[hydrated.skill_id] = hydrated

    def get(self, skill_id: str) -> Optional[SkillSpec]:
        return self._specs.get(skill_id)

    def require(self, skill_id: str) -> SkillSpec:
        spec = self.get(skill_id)
        if spec is None:
            raise UnknownSkillError(f"Unknown runtime skill: {skill_id}")
        return spec

    def all(self) -> List[SkillSpec]:
        return list(self._specs.values())


skill_registry = SkillRegistry(
    [
        SkillSpec(
            skill_id=SKILL_WENCAI_SECTOR_SCREEN,
            display_name="问财选板块",
            adapter_kind=SkillAdapterKind.WENCAI_QUERY,
        ),
        SkillSpec(
            skill_id=SKILL_WENCAI_STOCK_SCREEN,
            display_name="问财选A股",
            adapter_kind=SkillAdapterKind.WENCAI_QUERY,
            asset_path="skills/stock-selecter",
        ),
        SkillSpec(
            skill_id=SKILL_WENCAI_MARKET_QUERY,
            display_name="行情数据查询",
            adapter_kind=SkillAdapterKind.WENCAI_QUERY,
        ),
        SkillSpec(
            skill_id=SKILL_WENCAI_INDUSTRY_QUERY,
            display_name="行业数据查询",
            adapter_kind=SkillAdapterKind.WENCAI_QUERY,
        ),
        SkillSpec(
            skill_id=SKILL_WENCAI_FINANCIAL_QUERY,
            display_name="财务数据查询",
            adapter_kind=SkillAdapterKind.WENCAI_QUERY,
            asset_path="skills/ths-financial-data",
        ),
        SkillSpec(
            skill_id=SKILL_WENCAI_SHAREHOLDER_QUERY,
            display_name="公司股东股本查询",
            adapter_kind=SkillAdapterKind.WENCAI_QUERY,
        ),
        SkillSpec(
            skill_id=SKILL_WENCAI_SINGLE_SECURITY_SNAPSHOT,
            display_name="个股快照",
            adapter_kind=SkillAdapterKind.WENCAI_QUERY,
        ),
        SkillSpec(
            skill_id=SKILL_WENCAI_SINGLE_SECURITY_FUNDAMENTAL,
            display_name="财报快照",
            adapter_kind=SkillAdapterKind.WENCAI_QUERY,
        ),
        SkillSpec(
            skill_id=SKILL_SEARCH_NEWS,
            display_name="新闻搜索",
            adapter_kind=SkillAdapterKind.WENCAI_SEARCH,
            default_channel="news",
            asset_path="skills/新闻搜索",
        ),
        SkillSpec(
            skill_id=SKILL_SEARCH_ANNOUNCEMENT,
            display_name="公告搜索",
            adapter_kind=SkillAdapterKind.WENCAI_SEARCH,
            default_channel="announcement",
            asset_path="skills/公告搜索",
        ),
        SkillSpec(
            skill_id=SKILL_SEARCH_REPORT,
            display_name="研报搜索",
            adapter_kind=SkillAdapterKind.WENCAI_SEARCH,
            default_channel="report",
            asset_path="skills/研报搜索",
        ),
        SkillSpec(
            skill_id=SKILL_LOCAL_REALHEAD,
            display_name="同花顺行情快照",
            adapter_kind=SkillAdapterKind.LOCAL_REALHEAD,
            asset_path="skills/ths-advanced-analysis",
        ),
        SkillSpec(
            skill_id=SKILL_LOCAL_ORDERBOOK,
            display_name="同花顺盘口分析",
            adapter_kind=SkillAdapterKind.LOCAL_ORDERBOOK,
            asset_path="skills/ths-advanced-analysis",
        ),
        SkillSpec(
            skill_id=SKILL_LOCAL_THEME,
            display_name="同花顺题材补充",
            adapter_kind=SkillAdapterKind.LOCAL_THEME,
            asset_path="skills/ths-stock-themes",
        ),
    ]
)


__all__ = [
    "SKILL_LOCAL_ORDERBOOK",
    "SKILL_LOCAL_REALHEAD",
    "SKILL_LOCAL_THEME",
    "SKILL_SEARCH_ANNOUNCEMENT",
    "SKILL_SEARCH_NEWS",
    "SKILL_SEARCH_REPORT",
    "SKILL_WENCAI_FINANCIAL_QUERY",
    "SKILL_WENCAI_INDUSTRY_QUERY",
    "SKILL_WENCAI_MARKET_QUERY",
    "SKILL_WENCAI_SECTOR_SCREEN",
    "SKILL_WENCAI_SHAREHOLDER_QUERY",
    "SKILL_WENCAI_SINGLE_SECURITY_FUNDAMENTAL",
    "SKILL_WENCAI_SINGLE_SECURITY_SNAPSHOT",
    "SKILL_WENCAI_STOCK_SCREEN",
    "SkillAdapterKind",
    "SkillAssetMeta",
    "SkillRegistry",
    "SkillSpec",
    "UnknownSkillError",
    "skill_registry",
]
