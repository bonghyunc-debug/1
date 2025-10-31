import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gift_tax.calculator import GiftInput, compute_tax, load_law_table


@pytest.fixture(scope="module")
def law_context():
    law_path = Path(__file__).resolve().parents[1] / "gift_tax" / "law_tables" / "kor_2025.yaml"
    return load_law_table(law_path)


def make_input(**overrides) -> GiftInput:
    base = {
        "recipient_name": "홍길동",
        "gift_date": "2025-02-10",
        "relationship": "lineal_descendant_adult",
        "residency_status": "resident",
        "property_type": "cash",
        "property_value": Decimal("0"),
        "debt_assumed": Decimal("0"),
        "prior_gifts": Decimal("0"),
    }
    base.update(overrides)
    return GiftInput(**base)


def test_basic_deduction_zero_tax_adult_descendant(law_context):
    gift_input = make_input(property_value=Decimal("50000000"))
    breakdown = compute_tax(gift_input, law_context)

    assert breakdown.taxable_base == Decimal("0")
    assert breakdown.tax_due == Decimal("0")
    assert breakdown.basic_deduction == Decimal("50000000")
    assert breakdown.law_configured is True


def test_tax_at_first_bracket_ceiling(law_context):
    gift_input = make_input(property_value=Decimal("150000000"))
    breakdown = compute_tax(gift_input, law_context)

    assert breakdown.taxable_base == Decimal("100000000")
    assert breakdown.tax_due == Decimal("10000000")
    assert breakdown.applied_rate == Decimal("0.1")


def test_second_bracket_progressive_deduction(law_context):
    gift_input = make_input(property_value=Decimal("160000000"))
    breakdown = compute_tax(gift_input, law_context)

    assert breakdown.taxable_base == Decimal("110000000")
    assert breakdown.applied_rate == Decimal("0.2")
    assert breakdown.progressive_deduction == Decimal("10000000")
    assert breakdown.tax_due == Decimal("12000000")


def test_spouse_high_value_falls_into_fourth_bracket(law_context):
    gift_input = make_input(
        relationship="spouse",
        property_value=Decimal("3500000000"),
    )
    breakdown = compute_tax(gift_input, law_context)

    assert breakdown.basic_deduction == Decimal("600000000")
    assert breakdown.taxable_base == Decimal("2900000000")
    assert breakdown.applied_rate == Decimal("0.4")
    assert breakdown.tax_due == Decimal("1000000000")


def test_minor_with_prior_gifts_reduces_deduction(law_context):
    gift_input = make_input(
        relationship="lineal_descendant_minor",
        property_value=Decimal("30000000"),
        prior_gifts=Decimal("5000000"),
    )
    breakdown = compute_tax(gift_input, law_context)

    assert breakdown.basic_deduction_limit == Decimal("20000000")
    assert breakdown.prior_gifts_adjustment == Decimal("5000000")
    assert breakdown.basic_deduction == Decimal("15000000")
    assert breakdown.tax_due == Decimal("1500000")


def test_prior_gifts_exceed_basic_deduction(law_context):
    gift_input = make_input(
        property_value=Decimal("40000000"),
        prior_gifts=Decimal("80000000"),
    )
    breakdown = compute_tax(gift_input, law_context)

    assert breakdown.basic_deduction == Decimal("0")
    assert breakdown.prior_gifts_adjustment == Decimal("50000000")
    assert breakdown.tax_due == Decimal("4000000")


def test_debt_reduces_net_to_zero(law_context):
    gift_input = make_input(
        property_value=Decimal("10000000"),
        debt_assumed=Decimal("12000000"),
    )
    breakdown = compute_tax(gift_input, law_context)

    assert breakdown.net_gift == Decimal("0")
    assert breakdown.taxable_base == Decimal("0")
    assert breakdown.tax_due == Decimal("0")


def test_non_resident_others_deduction(law_context):
    gift_input = make_input(
        residency_status="non_resident",
        relationship="others",
        property_value=Decimal("60000000"),
    )
    breakdown = compute_tax(gift_input, law_context)

    assert breakdown.basic_deduction_limit == Decimal("10000000")
    assert breakdown.taxable_base == Decimal("50000000")
    assert breakdown.tax_due == Decimal("5000000")
    assert breakdown.law_version == "2025-01-01"
