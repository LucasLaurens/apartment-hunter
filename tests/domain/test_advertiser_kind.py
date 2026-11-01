from faker import Faker

from apartment_hunter.domain.services import (
    AGENCY_ONLY_SOURCES,
    FEDERATION_SOURCES,
    NETWORK_NAMES,
    PRIVATE_ONLY_SOURCES,
    AdvertiserKind,
    detect_advertiser_kind,
    find_network,
)

_fake = Faker("fr_FR")


def test_pap_is_private_whatever_the_advertiser_field_says() -> None:
    # Arrange — PAP publishes private ads only; a stray name cannot change that.
    source = next(iter(PRIVATE_ONLY_SOURCES))

    # Act & Assert
    assert detect_advertiser_kind(source, None) is AdvertiserKind.PRIVATE
    assert detect_advertiser_kind(source, _fake.company()) is AdvertiserKind.PRIVATE


def test_an_agency_network_is_an_agency_even_with_no_branch_name() -> None:
    # Arrange
    source = next(iter(AGENCY_ONLY_SOURCES))

    # Act & Assert
    assert detect_advertiser_kind(source, None) is AdvertiserKind.AGENCY


def test_a_portal_naming_an_advertiser_is_an_agency() -> None:
    # Arrange — a private landlord has no trade name to print.
    branch = _fake.company()

    # Act
    kind = detect_advertiser_kind("seloger", branch)

    # Assert
    assert kind is AdvertiserKind.AGENCY


def test_a_portal_naming_nobody_stays_unknown() -> None:
    # Act & Assert — silence is never guessed as "particulier".
    assert detect_advertiser_kind("seloger", None) is AdvertiserKind.UNKNOWN
    assert detect_advertiser_kind("seloger", "   ") is AdvertiserKind.UNKNOWN


def test_source_case_and_padding_do_not_change_the_answer() -> None:
    # Act & Assert
    assert detect_advertiser_kind("  PAP ", None) is AdvertiserKind.PRIVATE


def test_a_branch_name_reveals_its_network() -> None:
    # Act & Assert — a branch prints the brand with its town appended
    assert find_network("Laforêt Annecy") == "Laforêt"
    assert find_network("Century 21 Lac Bleu") == "Century 21"


def test_network_matching_ignores_case_accents_and_spacing() -> None:
    # Act & Assert — "century21", "CENTURY 21" and "Century21" are one brand
    assert find_network("CENTURY21 Annecy") == "Century 21"
    assert find_network("laforet immobilier") == "Laforêt"


def test_an_unknown_branch_has_no_network() -> None:
    # Act & Assert — empty, so callers print it unguarded
    assert find_network("Agence du Lac") == ""
    assert find_network(None) == ""


def test_every_agency_source_names_its_network() -> None:
    # Act & Assert — the two lists share one home; neither can gain a member alone.
    # A federation (FNAIM) is agency-only with no brand: it is the one declared exception.
    assert set(NETWORK_NAMES) == AGENCY_ONLY_SOURCES - FEDERATION_SOURCES
    assert not set(NETWORK_NAMES) & FEDERATION_SOURCES
