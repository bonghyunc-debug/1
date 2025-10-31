"""Minimal Flask application for the gift tax filing prototype."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

from flask import Flask, render_template, request
from pydantic import ValidationError

from gift_tax.calculator import GiftInput, LawContext, compute_tax, load_law_table

APP_ROOT = Path(__file__).resolve().parent
LAW_TABLE_PATH = APP_ROOT / "gift_tax" / "law_tables" / "kor_2025.yaml"

app = Flask(__name__)
LAW_CONTEXT: LawContext = load_law_table(LAW_TABLE_PATH)

RELATIONSHIP_OPTIONS: List[Tuple[str, str]] = [
    ("spouse", "배우자"),
    ("lineal_ascendant", "직계존속"),
    ("lineal_descendant_adult", "직계비속-성년"),
    ("lineal_descendant_minor", "직계비속-미성년"),
    ("others", "기타"),
]

RESIDENCY_OPTIONS: List[Tuple[str, str]] = [
    ("resident", "거주자"),
    ("non_resident", "비거주자"),
]

PROPERTY_TYPE_OPTIONS: List[Tuple[str, str]] = [
    ("cash", "현금"),
    ("real_estate", "부동산"),
    ("stock", "주식"),
    ("other", "기타"),
]


def _empty_form_values() -> Dict[str, str]:
    return {
        "recipient_name": "",
        "gift_date": "",
        "relationship": "",
        "residency_status": "",
        "property_type": "",
        "property_value": "",
        "debt_assumed": "",
        "prior_gifts": "",
    }


@app.route("/", methods=["GET"])
def form() -> str:
    return render_template(
        "form.html",
        relationship_options=RELATIONSHIP_OPTIONS,
        residency_options=RESIDENCY_OPTIONS,
        property_type_options=PROPERTY_TYPE_OPTIONS,
        errors=[],
        form_values=_empty_form_values(),
    )


@app.route("/calc", methods=["POST"])
def calculate() -> str:
    form_data = request.form.to_dict()
    payload = {
        "recipient_name": form_data.get("recipient_name", ""),
        "gift_date": form_data.get("gift_date", ""),
        "relationship": form_data.get("relationship", ""),
        "residency_status": form_data.get("residency_status", ""),
        "property_type": form_data.get("property_type", ""),
        "property_value": form_data.get("property_value", ""),
        "debt_assumed": form_data.get("debt_assumed", ""),
        "prior_gifts": form_data.get("prior_gifts", ""),
    }

    try:
        gift_input = GiftInput(**payload)
    except ValidationError as exc:
        error_messages = [
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}" for error in exc.errors()
        ]
        return (
            render_template(
                "form.html",
                relationship_options=RELATIONSHIP_OPTIONS,
                residency_options=RESIDENCY_OPTIONS,
                property_type_options=PROPERTY_TYPE_OPTIONS,
                errors=error_messages,
                form_values=payload,
            ),
            400,
        )

    breakdown = compute_tax(gift_input, LAW_CONTEXT)

    return render_template("result.html", breakdown=breakdown)


if __name__ == "__main__":
    app.run(debug=True)
