"""A saved filter must come back exactly as it went in.

The encoder enumerates its keys by hand, so a criterion added to `SearchFilter` and
forgotten in the codec used to vanish on every save with nothing failing anywhere.
"""

import json
from dataclasses import fields
from datetime import datetime

from faker import Faker

from apartment_hunter.domain.entities import SearchFilter
from apartment_hunter.domain.value_objects import DpeRating
from apartment_hunter.infrastructure.storage.filter_codec import filter_from_json, filter_to_json

_fake = Faker("fr_FR")

# Set by the row, not by the JSON blob — the filters table holds its own columns.
_ROW_FIELDS = {"id", "name", "enabled", "created_at"}


def _build_fully_populated() -> SearchFilter:
    """A filter with every criterion set away from its default."""
    return SearchFilter(
        id=_fake.uuid4()[:8],
        name=_fake.word(),
        cities=["Annecy", "Cran-Gevrier"],
        radius_km=12.5,
        excluded_cities=["Rumilly"],
        min_price=600,
        max_price=1250,
        min_surface_m2=42.0,
        max_surface_m2=95.0,
        min_rooms=2,
        max_rooms=4,
        furnished=False,
        exclude_ground_floor=True,
        exclude_first_floor=True,
        top_floor_only=True,
        accepted_dpe_ratings={DpeRating.A, DpeRating.C},
        charges_included=True,
        collective_heating=False,
        min_photos=3,
        excluded_advertisers=["Foncia"],
        max_age_days=14,
        max_results=42,
        notification_interval_minutes=20,
        refresh_interval_minutes=45,
        enabled=False,
        created_at=datetime(2026, 8, 1, 9, 30),
    )


def _run_round_trip(search_filter: SearchFilter) -> SearchFilter:
    return filter_from_json(
        {
            "id": search_filter.id,
            "name": search_filter.name,
            "enabled": int(search_filter.enabled),
            "created_at": search_filter.created_at.isoformat(),
            "config": filter_to_json(search_filter),
        }
    )


def test_every_field_survives_a_round_trip() -> None:
    """Field by field, so adding a criterion without encoding it fails right here."""
    # Arrange
    original = _build_fully_populated()

    # Act
    restored = _run_round_trip(original)

    # Assert
    for field in fields(SearchFilter):
        assert getattr(restored, field.name) == getattr(original, field.name), field.name


def test_the_codec_covers_every_criterion_of_the_entity() -> None:
    # Arrange — the encoded keys and the entity's own fields are two spellings of one fact
    encoded_keys = set(json.loads(filter_to_json(_build_fully_populated())))

    # Act
    missing = {f.name for f in fields(SearchFilter)} - _ROW_FIELDS - encoded_keys

    # Assert
    assert not missing, f"critères absents du codec : {sorted(missing)}"


def test_a_legacy_dpe_threshold_still_reads() -> None:
    # Arrange — filters saved before the DPE set replaced a single ceiling
    row = {
        "id": "old1",
        "name": "Ancien",
        "enabled": 1,
        "created_at": "2026-01-01T09:00:00",
        "config": '{"cities": ["Annecy"], "max_dpe_rating": "D"}',
    }

    # Act
    restored = filter_from_json(row)

    # Assert
    assert restored.accepted_dpe_ratings == DpeRating.up_to(DpeRating.D)


def test_a_legacy_advertiser_exclusion_still_reads() -> None:
    # Arrange — the key was renamed when the glossary settled on *annonceur*
    row = {
        "id": "old2",
        "name": "Ancien",
        "enabled": 1,
        "created_at": "2026-01-01T09:00:00",
        "config": '{"cities": ["Annecy"], "exclude_agencies": ["Foncia"]}',
    }

    # Act
    restored = filter_from_json(row)

    # Assert — losing this would put back listings the user had told us to drop
    assert restored.excluded_advertisers == ["Foncia"]


def test_an_out_of_range_radius_is_clamped_not_refused() -> None:
    # Arrange — a row written before the bounds existed must not break startup
    row = {
        "id": "old3",
        "name": "Ancien",
        "enabled": 1,
        "created_at": "2026-01-01T09:00:00",
        "config": '{"cities": ["Annecy"], "radius_km": 900}',
    }

    # Act
    restored = filter_from_json(row)

    # Assert
    assert restored.radius_km == 150.0


def test_an_interval_below_the_floor_is_raised() -> None:
    # Arrange — a zero interval puts the next deadline in the past
    row = {
        "id": "old4",
        "name": "Ancien",
        "enabled": 1,
        "created_at": "2026-01-01T09:00:00",
        "config": '{"cities": ["Annecy"], "refresh_interval_minutes": 0}',
    }

    # Act
    restored = filter_from_json(row)

    # Assert
    assert restored.refresh_interval_minutes == 5


def test_a_negative_bound_is_read_as_absent() -> None:
    # Arrange
    row = {
        "id": "old5",
        "name": "Ancien",
        "enabled": 1,
        "created_at": "2026-01-01T09:00:00",
        "config": '{"cities": ["Annecy"], "max_price": -50}',
    }

    # Act
    restored = filter_from_json(row)

    # Assert
    assert restored.max_price is None
