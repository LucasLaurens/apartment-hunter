"""Editing a filter on the web keeps what the form never shows (W4)."""

import re
from dataclasses import fields, replace
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from faker import Faker

from apartment_hunter.domain.entities import FilterBoundError, SearchFilter
from apartment_hunter.presentation.web.filter_payload import (
    _read_form,
    apply_payload,
    filter_from_payload,
    format_filter_error,
)
from tests.fakes.builders import build_search_filter

_fake = Faker("fr_FR")


def _build_stored_filter_with_hidden_criteria() -> SearchFilter:
    return replace(
        build_search_filter(),
        max_surface_m2=float(_fake.random_int(80, 150)),
        charges_included=True,
        collective_heating=False,
        min_photos=_fake.random_int(1, 5),
        excluded_advertisers=[_fake.company()],
        max_age_days=_fake.random_int(7, 30),
        enabled=False,
        created_at=datetime.now() - timedelta(days=_fake.random_int(10, 300)),
    )


def test_an_edit_keeps_every_criterion_the_form_does_not_show() -> None:
    # Arrange
    stored = _build_stored_filter_with_hidden_criteria()
    body = {"name": _fake.word(), "cities": "Annecy, Poisy", "radius_km": "15", "max_price": "1400"}
    form_fields = set(_read_form(body))

    # Act
    edited = apply_payload(stored, body)

    # Assert
    hidden = [f.name for f in fields(stored) if f.name not in form_fields]
    assert hidden, "every criterion is on the form — this test no longer guards anything"
    assert {name: getattr(edited, name) for name in hidden} == {
        name: getattr(stored, name) for name in hidden
    }


def test_an_edit_applies_what_the_form_holds() -> None:
    # Arrange
    stored = _build_stored_filter_with_hidden_criteria()
    name = _fake.word()

    # Act
    edited = apply_payload(stored, {"name": name, "cities": "Poisy", "max_price": "1200"})

    # Assert
    assert (edited.name, edited.cities, edited.max_price) == (name, ["Poisy"], 1200)
    assert edited.id == stored.id


_APP_JS = (
    Path(__file__).parent.parent.parent / "src/apartment_hunter/presentation/web/assets/app.js"
).read_text(encoding="utf-8")


def test_the_page_sends_every_criterion_the_server_reads() -> None:
    """A criterion read but never sent is blanked by every edit: max_rooms was (W4)."""
    # Arrange
    block = re.search(r"function filterPayload\(\) \{\s*return \{(.*?)\n  \};", _APP_JS, re.S)
    assert block is not None, "filterPayload introuvable dans app.js"
    sent = set(re.findall(r"^\s*(\w+):", block.group(1), re.M))

    # Act
    unsent = set(_read_form({})) - sent

    # Assert
    assert not unsent, f"lus par le serveur, jamais envoyés par la page : {sorted(unsent)}"


def test_a_refused_radius_names_its_field_in_french() -> None:
    # Arrange
    body = {"name": _fake.word(), "cities": "Annecy", "radius_km": str(_fake.random_int(151, 900))}

    # Act
    with pytest.raises(FilterBoundError) as refused:
        filter_from_payload(_fake.uuid4(), body)
    error = format_filter_error(refused.value)

    # Assert
    assert error["field"] == "radius_km"
    assert "km" in error["message"] and "radius_km" not in error["message"]


def test_a_negative_bound_names_its_field() -> None:
    # Arrange
    body = {"name": _fake.word(), "cities": "Annecy", "min_price": "-1"}

    # Act
    with pytest.raises(FilterBoundError) as refused:
        filter_from_payload(_fake.uuid4(), body)

    # Assert
    assert format_filter_error(refused.value)["field"] == "min_price"
