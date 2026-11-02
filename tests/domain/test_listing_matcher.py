from dataclasses import replace

import pytest

from apartment_hunter.domain.services import ListingMatcher
from apartment_hunter.domain.value_objects import DpeRating, Location
from tests.fakes.builders import build_listing, build_search_filter

ANNECY_COORDS = (45.8992, 6.1294)
GEOCODED = {"annecy": ANNECY_COORDS}


@pytest.fixture
def matcher() -> ListingMatcher:
    return ListingMatcher(geocoded_cities=GEOCODED)


def test_matches_price_within_range(matcher: ListingMatcher) -> None:
    # Arrange
    listing = build_listing(price=900.0)
    f = build_search_filter(max_price=1000)

    # Act & Assert
    assert matcher.matches(listing, f) is True


def test_rejects_price_over_max(matcher: ListingMatcher) -> None:
    # Arrange
    listing = build_listing(price=1200.0)
    f = build_search_filter(max_price=1000)

    # Act & Assert
    assert matcher.matches(listing, f) is False


def test_rejects_dpe_worse_than_max(matcher: ListingMatcher) -> None:
    # Arrange
    listing = build_listing(dpe="E")
    f = build_search_filter(max_dpe_rating="D")

    # Act & Assert
    assert matcher.matches(listing, f) is False


def test_accepts_dpe_equal_to_max(matcher: ListingMatcher) -> None:
    # Arrange
    listing = build_listing(dpe="D")
    f = build_search_filter(max_dpe_rating="D")

    # Act & Assert
    assert matcher.matches(listing, f) is True


def test_accepts_apartment_with_no_dpe_when_filter_set(matcher: ListingMatcher) -> None:
    # Arrange — unknown DPE passes (can't filter what's not there)
    listing = build_listing(dpe=None)
    f = build_search_filter(max_dpe_rating="B")

    # Act & Assert
    assert matcher.matches(listing, f) is True


def test_rejects_dpe_not_in_accepted_set(matcher: ListingMatcher) -> None:
    # Arrange — user checked A, B, C, E but NOT D or F (non-contiguous selection)
    listing = build_listing(dpe="F")
    f = build_search_filter()
    f.accepted_dpe_ratings = {DpeRating.A, DpeRating.B, DpeRating.C, DpeRating.E}

    # Act & Assert — F was never checked, must be rejected (regression: gap-leak)
    assert matcher.matches(listing, f) is False


def test_rejects_unchecked_middle_dpe(matcher: ListingMatcher) -> None:
    # Arrange — D sits in a gap between checked C and E
    listing = build_listing(dpe="D")
    f = build_search_filter()
    f.accepted_dpe_ratings = {DpeRating.A, DpeRating.B, DpeRating.C, DpeRating.E}

    # Act & Assert
    assert matcher.matches(listing, f) is False


def test_rejects_ground_floor_when_excluded(matcher: ListingMatcher) -> None:
    # Arrange
    listing = build_listing(floor_level=0)
    f = build_search_filter()
    f.exclude_ground_floor = True

    # Act & Assert
    assert matcher.matches(listing, f) is False


def test_accepts_upper_floor_when_ground_excluded(matcher: ListingMatcher) -> None:
    # Arrange
    listing = build_listing(floor_level=3)
    f = build_search_filter()
    f.exclude_ground_floor = True

    # Act & Assert
    assert matcher.matches(listing, f) is True


def test_rejects_excluded_city(matcher: ListingMatcher) -> None:
    # Arrange
    listing = build_listing(city="Rumilly")
    f = build_search_filter(cities=["Annecy"], excluded_cities=["Rumilly"])

    # Act & Assert
    assert matcher.matches(listing, f) is False


def test_top_floor_only_rejects_non_top(matcher: ListingMatcher) -> None:
    # Arrange
    listing = build_listing(floor_level=3, is_top=False)
    f = build_search_filter()
    f.top_floor_only = True

    # Act & Assert
    assert matcher.matches(listing, f) is False


def test_top_floor_only_accepts_top(matcher: ListingMatcher) -> None:
    # Arrange
    listing = build_listing(floor_level=6, is_top=True)
    f = build_search_filter()
    f.top_floor_only = True

    # Act & Assert
    assert matcher.matches(listing, f) is True


def test_rejects_a_banned_agency(matcher: ListingMatcher) -> None:
    # Arrange
    listing = build_listing(advertiser="Foncia")
    f = build_search_filter()
    f.excluded_advertisers = ["Foncia"]

    # Act & Assert
    assert matcher.matches(listing, f) is False


def test_rejects_a_banned_agency_branch(matcher: ListingMatcher) -> None:
    # Arrange — the network name is what the user types; the listing adds its branch
    listing = build_listing(advertiser="Century 21 Lac Bleu")
    f = build_search_filter()
    f.excluded_advertisers = ["century 21"]

    # Act & Assert
    assert matcher.matches(listing, f) is False


def test_keeps_an_agency_that_was_not_banned(matcher: ListingMatcher) -> None:
    # Arrange
    listing = build_listing(advertiser="Laforêt Annecy")
    f = build_search_filter()
    f.excluded_advertisers = ["Foncia"]

    # Act & Assert
    assert matcher.matches(listing, f) is True


def test_keeps_a_listing_with_no_agency_when_some_are_banned(matcher: ListingMatcher) -> None:
    # Arrange — most sources publish no advertiser name; it can't prove a match
    listing = build_listing(advertiser=None)
    f = build_search_filter()
    f.excluded_advertisers = ["Foncia"]

    # Act & Assert
    assert matcher.matches(listing, f) is True


def test_an_uncollected_photo_set_does_not_reject(matcher: ListingMatcher) -> None:
    """No crawler fills `images` yet, so empty means "not collected", not "no photo".

    Counting it as zero made any `min_photos > 0` reject every single listing.
    """
    # Arrange
    f = build_search_filter(cities=["Annecy"])
    f.min_photos = 3
    listing = build_listing(city="Annecy")

    # Act & Assert
    assert matcher.matches(listing, f)


def test_a_listing_with_too_few_known_photos_is_rejected(matcher: ListingMatcher) -> None:
    # Arrange — once a source does fill them, the criterion bites again
    f = build_search_filter(cities=["Annecy"])
    f.min_photos = 3
    listing = replace(build_listing(city="Annecy"), images=("https://a.test/1.jpg",))

    # Act & Assert
    assert not matcher.matches(listing, f)


# The geo API keys a commune by its INSEE name; each site prints its own spelling.
# No crawler collects coordinates, so the commune name is the only way in.
SPELLING_GEOCODED = {
    "annecy": ANNECY_COORDS,
    "sevrier": (45.8644, 6.1397),
    "saint-félix": (45.8006, 5.9800),
    "alby-sur-chéran": (45.8183, 6.0105),
}


@pytest.mark.parametrize(
    "site_spelling",
    ["Sévrier", "Saint Felix", "Alby Sur Cheran", "SAINT-FÉLIX", "Alby-sur-Chéran"],
)
def test_a_commune_matches_whatever_the_site_spelling(site_spelling: str) -> None:
    # Arrange
    matcher = ListingMatcher(geocoded_cities=SPELLING_GEOCODED)
    listing = replace(build_listing(), location=Location(city=site_spelling))
    f = build_search_filter(cities=["Annecy"], radius_km=20.0)

    # Act & Assert
    assert matcher.matches(listing, f) is True


def test_an_excluded_commune_is_excluded_whatever_the_site_spelling() -> None:
    # Arrange
    matcher = ListingMatcher(geocoded_cities=SPELLING_GEOCODED)
    listing = replace(build_listing(), location=Location(city="Saint Felix"))
    f = build_search_filter(cities=["Annecy"], radius_km=20.0, excluded_cities=["Saint-Félix"])

    # Act & Assert
    assert matcher.matches(listing, f) is False
