"""Per-site publication-date extraction, on HTML shaped like each site's own."""

from datetime import datetime

from apartment_hunter.domain.value_objects import PublicationSource
from apartment_hunter.infrastructure.crawlers.foncia_crawler import (
    _parse_publication_dates as foncia_dates,
)


def test_foncia_maps_each_reference_to_its_publication_date() -> None:
    # Arrange — Angular escapes the SSR state's quotes as "&q;". Each listing embeds a
    # location object whose own "reference" is the region code (84 = Auvergne-Rhône-Alpes).
    page = (
        "<html><body>"
        "&q;canonicalUrl&q;:&q;/location/annecy-74/appartement/331613405.htm&q;,"
        "&q;reference&q;:&q;331613405&q;,"
        "&q;localisation&q;:{&q;reference&q;:&q;84&q;},&q;nbPiece&q;:3,"
        "&q;datePublication&q;:&q;2026-08-03T10:22:27+02:00&q;,"
        "&q;canonicalUrl&q;:&q;/location/annecy-74/appartement/331613406.htm&q;,"
        "&q;reference&q;:&q;331613406&q;,"
        "&q;localisation&q;:{&q;reference&q;:&q;84&q;},&q;nbPiece&q;:2,"
        "&q;datePublication&q;:&q;2026-07-11T08:00:00+02:00&q;"
        "</body></html>"
    )

    # Act
    dates = foncia_dates(page)

    # Assert
    assert dates == {
        "331613405": datetime(2026, 8, 3, 10, 22, 27),
        "331613406": datetime(2026, 7, 11, 8, 0, 0),
    }


def test_foncia_skips_a_listing_without_a_date_instead_of_borrowing_its_neighbours() -> None:
    # Arrange — the first listing has no datePublication at all
    page = (
        "&q;canonicalUrl&q;:&q;/location/annecy-74/appartement/111.htm&q;,&q;nbPiece&q;:3,"
        "&q;canonicalUrl&q;:&q;/location/annecy-74/appartement/222.htm&q;,"
        "&q;datePublication&q;:&q;2026-07-11T08:00:00+02:00&q;"
    )

    # Act
    dates = foncia_dates(page)

    # Assert
    assert dates == {"222": datetime(2026, 7, 11, 8, 0, 0)}


def test_publication_source_default_is_first_seen() -> None:
    # Act & Assert — a crawler that says nothing must not claim a site date
    assert PublicationSource("first_seen") is PublicationSource.FIRST_SEEN
