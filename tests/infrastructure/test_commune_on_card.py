"""A listing carries the commune its own card names, never the one that was searched.

ParuVendu answered an empty commune's URL with the whole department page, and Foncia pads
a small commune's page with its neighbours: stamping the searched commune on every card put a
Gaillard flat under « Veyrier-du-Lac », at the wrong place on the map and in the radius.
"""

from bs4 import BeautifulSoup, Tag
from faker import Faker

from apartment_hunter.infrastructure.crawlers.base_crawler import parse_commune_label
from apartment_hunter.infrastructure.crawlers.foncia_crawler import FonciaCrawler
from apartment_hunter.infrastructure.crawlers.paruvendu_crawler import ParuVenduCrawler

_fake = Faker("fr_FR")


def _select_card(html: str, selector: str) -> Tag:
    card = BeautifulSoup(html, "lxml").select_one(selector)
    assert card is not None
    return card


def _build_paruvendu_card(place: str) -> str:
    listing_id = _fake.random_int(1_000_000_000, 1_999_999_999)
    return f"""
    <div class="blocAnnonce" data-id="{listing_id}">
      <h3><a href="/immobilier/location/appartement/{listing_id}A1KILHAP000">
        <span>Appartement
55 m<sup>2</sup>
          {place}
        </span>
      </a></h3>
      <div>1 060 € CC*</div>
    </div>
    """


def _build_foncia_card(place: str) -> str:
    reference = _fake.random_int(300_000_000, 399_999_999)
    return f"""
    <app-annonce-card>
      <a class="foncia-card-title-small" href="/location/sevrier-74320/appartement/{reference}.htm">
        <h3>Location Appartement 3 pièces 62.67 m²</h3>
      </a>
      <h2 class="foncia-card-price">1 164 € / mois CC</h2>
      <p class="foncia-card-place">{place}</p>
    </app-annonce-card>
    """


def test_paruvendu_keeps_the_commune_its_card_names() -> None:
    # Arrange — searched for one commune, the department page shows another
    card = _select_card(_build_paruvendu_card("Gaillard (74)"), "div.blocAnnonce")

    # Act
    listing = ParuVenduCrawler()._parse(card)

    # Assert
    assert listing is not None
    assert listing.location.city == "Gaillard"
    assert listing.location.department == "74"


def test_paruvendu_drops_a_card_that_names_no_commune() -> None:
    # Arrange
    card = _select_card(_build_paruvendu_card(""), "div.blocAnnonce")

    # Act
    listing = ParuVenduCrawler()._parse(card)

    # Assert — the searched commune is never a stand-in
    assert listing is None


def test_foncia_keeps_the_commune_its_card_names() -> None:
    # Arrange — a small commune's page padded with its neighbours
    card = _select_card(_build_foncia_card("Sevrier (74320)"), "app-annonce-card")

    # Act
    listing = FonciaCrawler()._parse(card, {})

    # Assert
    assert listing is not None
    assert listing.location.city == "Sevrier"
    assert listing.location.postal_code == "74320"


def test_foncia_drops_a_card_that_names_no_commune() -> None:
    # Arrange
    card = _select_card(_build_foncia_card(""), "app-annonce-card")

    # Act
    listing = FonciaCrawler()._parse(card, {})

    # Assert
    assert listing is None


def test_a_commune_label_splits_into_name_and_code() -> None:
    # Act & Assert — a department (ParuVendu), a postal code (Foncia, Citya)
    assert parse_commune_label("Saint-Julien-en-Genevois (74)") == (
        "Saint-Julien-en-Genevois",
        "74",
    )
    assert parse_commune_label("La Compôte (73630)") == ("La Compôte", "73630")
    assert parse_commune_label("Corse (2A)") == ("Corse", "2A")
    assert parse_commune_label("Appartement 55 m2") is None
