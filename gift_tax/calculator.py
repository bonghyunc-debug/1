"""Core domain models and computation helpers for the gift tax prototype."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

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
    law_version: Optional[str] = None
    law_reference: Optional[str] = None
    law_reference_url: Optional[str] = None
    recipient_name: str
    gift_date: date
    relationship: str
    residency_status: str
    property_type: str
    property_value: Decimal
    debt_assumed: Decimal
    net_gift: Decimal
    basic_deduction_limit: Decimal
    prior_gifts_adjustment: Decimal
    basic_deduction: Decimal
    taxable_base: Decimal
    applied_rate: Optional[Decimal] = None
    progressive_deduction: Optional[Decimal] = None
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


def _find_progressive_bracket(
    brackets: Iterable[Dict[str, Any]], taxable_base: Decimal
) -> Optional[Dict[str, Decimal]]:
    """Locate the progressive tax bracket applicable to the taxable base."""

    normalized: list[Dict[str, Decimal]] = []
    for bracket in brackets:
        try:
            min_value = Decimal(str(bracket.get("min", "0")))
            max_value = bracket.get("max")
            max_decimal = Decimal(str(max_value)) if max_value is not None else None
            rate = Decimal(str(bracket["rate"]))
            deduction = Decimal(str(bracket.get("deduction", "0")))
        except (KeyError, ValueError, TypeError):  # pragma: no cover - invalid config
            continue
        normalized.append(
            {
                "min": min_value,
                "max": max_decimal,
                "rate": rate,
                "deduction": deduction,
            }
        )

    normalized.sort(key=lambda item: item["min"])

    for bracket in normalized:
        lower_ok = taxable_base >= bracket["min"]
        upper_ok = bracket["max"] is None or taxable_base <= bracket["max"]
        if lower_ok and upper_ok:
            return bracket

    return None


def compute_tax(gift_input: GiftInput, law: LawContext) -> GiftBreakdown:
    """Compute the taxable base and optionally the tax, depending on law availability."""

    property_value = gift_input.property_value
    debt_assumed = gift_input.debt_assumed or Decimal("0")
    net_gift = property_value - debt_assumed
    if net_gift < 0:
        net_gift = Decimal("0")

    law_version: Optional[str] = None
    law_reference: Optional[str] = None
    law_reference_url: Optional[str] = None

    notes: list[str] = []
    tax_due: Optional[Decimal] = None
    applied_rate: Optional[Decimal] = None
    progressive_deduction: Optional[Decimal] = None

    basic_deduction_limit = Decimal("0")
    prior_gifts_adjustment = gift_input.prior_gifts or Decimal("0")
    basic_deduction_applied = Decimal("0")
    taxable_base = Decimal("0")

    if not law.configured or not law.data:
        notes.append("법규 테이블이 설정되어 있지 않아 기본공제와 세액을 계산할 수 없습니다.")
    else:
        metadata = law.data.get("metadata", {})
        law_version = metadata.get("version")
        law_reference = metadata.get("reference")
        law_reference_url = metadata.get("reference_url")

        residency_key = gift_input.residency_status
        relationship_key = gift_input.relationship

        basic_table = law.data.get("basic_deduction", {})
        try:
            basic_deduction_limit = Decimal(
                str(basic_table[residency_key][relationship_key])
            )
        except KeyError:
            notes.append(
                "법규 테이블에 해당 거주자 구분/관계의 기본공제가 정의되어 있지 않습니다."
            )
            return GiftBreakdown(
                law_configured=False,
                law_version=law_version,
                law_reference=law_reference,
                law_reference_url=law_reference_url,
                recipient_name=gift_input.recipient_name,
                gift_date=gift_input.gift_date,
                relationship=gift_input.relationship,
                residency_status=gift_input.residency_status,
                property_type=gift_input.property_type,
                property_value=property_value,
                debt_assumed=debt_assumed,
                net_gift=net_gift,
                basic_deduction_limit=basic_deduction_limit,
                prior_gifts_adjustment=prior_gifts_adjustment,
                basic_deduction=basic_deduction_applied,
                taxable_base=taxable_base,
                applied_rate=applied_rate,
                progressive_deduction=progressive_deduction,
                tax_due=tax_due,
                notes=notes,
            )

        prior_gifts_adjustment = min(prior_gifts_adjustment, basic_deduction_limit)
        basic_deduction_applied = basic_deduction_limit - prior_gifts_adjustment
        if basic_deduction_applied < 0:
            basic_deduction_applied = Decimal("0")

        taxable_base = net_gift - basic_deduction_applied
        if taxable_base < 0:
            taxable_base = Decimal("0")

        if taxable_base == 0:
            tax_due = Decimal("0")
        else:
            bracket = _find_progressive_bracket(law.data.get("progressive_rates", []), taxable_base)
            if bracket is None:
                notes.append("법규 테이블의 누진세율 구간을 찾을 수 없습니다.")
                tax_due = None
            else:
                applied_rate = bracket["rate"]
                progressive_deduction = bracket.get("deduction", Decimal("0"))
                raw_tax = taxable_base * applied_rate
                tax_due = raw_tax - progressive_deduction
                if tax_due < 0:
                    tax_due = Decimal("0")
                tax_due = tax_due.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
                notes.append(
                    "과세표준 {base:,}원에 세율 {rate}% 및 누진공제 {deduction:,}원을 적용했습니다.".format(
                        base=int(taxable_base),
                        rate=(applied_rate * Decimal("100")),
                        deduction=int(progressive_deduction),
                    )
                )

        if gift_input.prior_gifts:
            notes.append(
                "최근 10년 내 증여가액 {amount:,}원이 기본공제 한도를 차감했습니다.".format(
                    amount=int(gift_input.prior_gifts or Decimal("0"))
                )
            )

    return GiftBreakdown(
        law_configured=law.configured and bool(law.data),
        law_version=law_version,
        law_reference=law_reference,
        law_reference_url=law_reference_url,
        recipient_name=gift_input.recipient_name,
        gift_date=gift_input.gift_date,
        relationship=gift_input.relationship,
        residency_status=gift_input.residency_status,
        property_type=gift_input.property_type,
        property_value=property_value,
        debt_assumed=debt_assumed,
        net_gift=net_gift,
        basic_deduction_limit=basic_deduction_limit,
        prior_gifts_adjustment=prior_gifts_adjustment,
        basic_deduction=basic_deduction_applied,
        taxable_base=taxable_base,
        applied_rate=applied_rate,
        progressive_deduction=progressive_deduction,
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
