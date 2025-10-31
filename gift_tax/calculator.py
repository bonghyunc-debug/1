"""Core domain models and computation helpers for the gift tax prototype."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dateutil.parser import parse as parse_datetime
from pydantic import BaseModel, Field, validator


class GiftInput(BaseModel):
    """Structured representation of the gift tax form submission."""

    recipient_name: str = Field(..., description="수증자 이름")
    gift_date: date = Field(..., description="증여일")
    relationship: str = Field(..., description="증여자와의 관계")
    residency_status: str = Field(..., description="거주자 여부")
    property_type: str = Field(..., description="증여 재산 종류")
    property_value: Decimal = Field(..., ge=0, description="평가가액")
    debt_assumed: Optional[Decimal] = Field(default=Decimal("0"), ge=0, description="채무 인수액")
    prior_gifts: Optional[Decimal] = Field(
        default=Decimal("0"), ge=0, description="최근 10년 내 동일 증여자의 누적 증여가액"
    )

    @validator("recipient_name", "relationship", "residency_status", "property_type")
    def strip_strings(cls, value: str) -> str:
        if isinstance(value, str):
            value = value.strip()
        if not value:
            raise ValueError("값을 입력해 주세요.")
        return value

    @validator("gift_date", pre=True)
    def parse_date(cls, value: Any) -> date:
        if isinstance(value, date):
            return value
        try:
            parsed = parse_datetime(str(value)).date()
        except (ValueError, TypeError) as exc:  # pragma: no cover - defensive
            raise ValueError("YYYY-MM-DD 형식으로 입력해 주세요.") from exc
        return parsed

    @validator("property_value", "debt_assumed", "prior_gifts", pre=True)
    def parse_decimal(cls, value: Any) -> Decimal:
        if value in (None, ""):
            return Decimal("0")
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except (ValueError, TypeError) as exc:  # pragma: no cover - defensive
            raise ValueError("숫자를 입력해 주세요.") from exc


class GiftBreakdown(BaseModel):
    """Outcome of the gift tax computation."""

    law_configured: bool
    recipient_name: str
    gift_date: date
    relationship: str
    residency_status: str
    property_type: str
    property_value: Decimal
    debt_assumed: Decimal
    net_gift: Decimal
    basic_deduction: Decimal
    prior_gifts_adjustment: Decimal
    taxable_base: Decimal
    tax_due: Optional[Decimal] = None
    notes: list[str] = Field(default_factory=list)


@dataclass
class LawContext:
    """Wrapper describing the loaded law table and whether it is usable."""

    data: Optional[Dict[str, Any]]
    configured: bool


def load_law_table(path: str | Path) -> LawContext:
    """Load the law table YAML file, detecting placeholder content."""

    law_path = Path(path)
    if not law_path.exists():
        return LawContext(data=None, configured=False)

    with law_path.open("r", encoding="utf-8") as handle:
        raw_data = yaml.safe_load(handle) or {}

    serialized = yaml.safe_dump(raw_data)
    contains_placeholder = "PLACEHOLDER" in serialized

    return LawContext(data=raw_data, configured=not contains_placeholder)


def compute_tax(gift_input: GiftInput, law: LawContext) -> GiftBreakdown:
    """Compute the taxable base and optionally the tax, depending on law availability."""

    property_value = gift_input.property_value
    debt_assumed = gift_input.debt_assumed or Decimal("0")
    net_gift = property_value - debt_assumed

    basic_deduction = Decimal("0")
    prior_gifts_adjustment = gift_input.prior_gifts or Decimal("0")

    taxable_base = net_gift - basic_deduction - prior_gifts_adjustment
    if taxable_base < 0:
        taxable_base = Decimal("0")

    notes: list[str] = []
    tax_due: Optional[Decimal] = None

    if not law.configured:
        notes.append("법규 테이블이 PLACEHOLDER 상태이므로 세액을 계산하지 않습니다.")
    else:
        # Placeholder for future tax calculation logic once the law table is populated.
        notes.append("법규 테이블이 설정되어 있으나, 세액 계산 로직은 구현 예정입니다.")

    return GiftBreakdown(
        law_configured=law.configured,
        recipient_name=gift_input.recipient_name,
        gift_date=gift_input.gift_date,
        relationship=gift_input.relationship,
        residency_status=gift_input.residency_status,
        property_type=gift_input.property_type,
        property_value=property_value,
        debt_assumed=debt_assumed,
        net_gift=net_gift,
        basic_deduction=basic_deduction,
        prior_gifts_adjustment=prior_gifts_adjustment,
        taxable_base=taxable_base,
        tax_due=tax_due,
        notes=notes,
    )


__all__ = [
    "GiftInput",
    "GiftBreakdown",
    "LawContext",
    "load_law_table",
    "compute_tax",
]
