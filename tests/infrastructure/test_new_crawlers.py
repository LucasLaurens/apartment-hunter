"""Laforêt and Citya card parsing, on HTML shaped like each site's own."""

from bs4 import BeautifulSoup

from apartment_hunter.infrastructure.crawlers.base_crawler import is_in_department
from apartment_hunter.infrastructure.crawlers.citya_crawler import CityaCrawler
from apartment_hunter.infrastructure.crawlers.laforet_crawler import LaforetCrawler

_LAFORET_CARD = """
<div>
  <a href="https://www.laforet.com/agence-immobiliere/pringy/louer/annecy/appartement-4-pieces-52846209#section-video">Voir</a>
  <button data-gtm-item-id-param="52846209"
          data-gtm-item-type-param="Appartement"
          data-gtm-item-city-param="ANNECY LE VIEUX"
          data-gtm-item-zipcode-param="74940"
          data-gtm-item-price-param="1450"
          data-gtm-item-size-param="83.81"
          data-gtm-item-rooms-nb-param="4"
          data-gtm-item-criteria-param="84 m², 4 pièces, 2 chambres"
          data-gtm-item-name-param="Appartement 4 ANNECY">♥</button>
  <a href="https://www.laforet.com/agence-immobiliere/rumilly/louer/rumilly/maison-3-pieces-52788591">Voir</a>
  <button data-gtm-item-id-param="52788591"
          data-gtm-item-type-param="Maison"
          data-gtm-item-city-param="RUMILLY"
          data-gtm-item-zipcode-param="74150"
          data-gtm-item-price-param="710"
          data-gtm-item-size-param="31.78"
          data-gtm-item-rooms-nb-param="1"
          data-gtm-item-name-param="Maison 1 RUMILLY">♥</button>
</div>
"""

_CITYA_CARDS = """
<div>
  <div class="property-card" data-itemid="GES1-1" data-category="Appartement"
       data-itemname="Appartement 2 pièces 39.03m²" data-price="851">
    <a href="/annonces/location/appartement/annecy-74000/GES1-1">
      <p>Annecy (74000)</p>
      <p>Appartement <strong>2 pièces 39.03m²</strong></p>
    </a>
  </div>
  <div class="property-card" data-itemid="GES2-2" data-category="Appartement"
       data-itemname="Appartement 5 pièces 175.95m²" data-price="2076">
    <a href="/annonces/location/appartement/lyon-2e-arrondissement-69002/GES2-2">
      <p>Lyon 2e Arrondissement (69002)</p>
      <p>Appartement <strong>5 pièces 175.95m²</strong></p>
    </a>
  </div>
</div>
"""


# Shaped like a Laforêt detail page: furnishing is a bare chip under "Intérieur",
# the storey only appears in the prose, and "location meublée" links sit in the footer.
_LAFORET_DETAIL = """
<main>
  <div class="text-primary">
    <h3 class="mb-4 text-2xl font-bold">Intérieur</h3>
    <div class="grid grid-cols-2 gap-4">
      <div class="flex items-center gap-2"><span><svg></svg></span><span>Ascenseur</span></div>
      <div class="flex items-center gap-2"><span><svg></svg></span><span>Terrasse</span></div>
      <div class="flex items-center gap-2"><span><svg></svg></span><span>Meublé</span></div>
    </div>
  </div>
  <h2>Description</h2>
  <p>Ce T2 de 43,12 m² se trouve au 4e étage sur 5 d'une copropriété récente.</p>
  <footer>
    <a href="/location-meublee-annecy">Location meublée Annecy</a>
    <div class="text truncate">Terrasse &bull; Ascenseur &bull; Meublé</div>
  </footer>
</main>
"""


def test_laforet_reads_the_furnishing_chip_the_criteria_table_prints() -> None:
    # Arrange — Laforêt never writes "Meublé : oui", so the labelled reading is blind
    soup = BeautifulSoup(_LAFORET_DETAIL, "lxml")

    # Act
    details = LaforetCrawler.parse_details(soup)

    # Assert
    assert details.furnished is True
    assert details.floor is not None
    assert details.floor.level == 4


def test_laforet_ignores_a_furnishing_word_outside_the_criteria_table() -> None:
    # Arrange — same page without its chip: only the footer link and a neighbour's card
    without_chip = _LAFORET_DETAIL.replace("<span>Meublé</span>", "<span>Cave</span>")
    soup = BeautifulSoup(without_chip, "lxml")

    # Act
    details = LaforetCrawler.parse_details(soup)

    # Assert
    assert details.furnished is None


def test_laforet_joins_analytics_attributes_to_the_listing_url() -> None:
    # Arrange
    crawler = LaforetCrawler()

    # Act
    apts = crawler._parse_page(_LAFORET_CARD)

    # Assert — the "Maison" card is dropped, the flat's figures come from the button
    assert len(apts) == 1
    listing = apts[0]
    assert listing.url.endswith("appartement-4-pieces-52846209")  # the "#anchor" is stripped
    assert listing.location.city == "Annecy Le Vieux"
    assert listing.location.postal_code == "74940"
    assert float(listing.price.amount) == 1450.0
    assert listing.surface_m2 == 83.81
    assert listing.rooms == 4
    assert not listing.has_site_publication_date  # Laforêt prints no date


def test_citya_reads_price_city_and_surface_from_the_card() -> None:
    # Arrange
    crawler = CityaCrawler()
    card = BeautifulSoup(_CITYA_CARDS, "lxml").select("div.property-card")[0]

    # Act
    listing = crawler._parse(card)

    # Assert
    assert listing is not None
    assert listing.url == "https://www.citya.com/annonces/location/appartement/annecy-74000/GES1-1"
    assert listing.location.city == "Annecy"
    assert listing.location.postal_code == "74000"
    assert float(listing.price.amount) == 851.0
    assert listing.surface_m2 == 39.03
    assert listing.rooms == 2


def test_citya_drops_the_cross_city_carousel_listings() -> None:
    # Arrange — a town page pads its results with listings from other departments
    crawler = CityaCrawler()
    cards = BeautifulSoup(_CITYA_CARDS, "lxml").select("div.property-card")
    parsed = [listing for c in cards if (listing := crawler._parse(c))]

    # Act
    kept = [listing for listing in parsed if is_in_department(listing, "74")]

    # Assert
    assert [listing.location.postal_code for listing in kept] == ["74000"]
