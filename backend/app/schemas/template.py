from datetime import datetime
from typing import Dict, Optional

from pydantic import Field

from .common import ChatMode, ContractModel, JsonValue


class TemplateRecord(ContractModel):
    id: str
    name: str
    category: str
    mode: Optional[ChatMode] = None
    content: str
    default_params: Dict[str, JsonValue] = Field(default_factory=dict)
    created_at: datetime


class TemplateCreate(ContractModel):
    name: str
    category: str
    mode: Optional[ChatMode] = None
    content: str
    default_params: Dict[str, JsonValue] = Field(default_factory=dict)


class TemplateUpdate(ContractModel):
    name: Optional[str] = None
    category: Optional[str] = None
    mode: Optional[ChatMode] = None
    content: Optional[str] = None
    default_params: Optional[Dict[str, JsonValue]] = None
