"""ParuVendu energy scales — read the listing's own note, never the scale legend."""

from bs4 import BeautifulSoup
from faker import Faker

from apartment_hunter.domain.entities import Listing
from apartment_hunter.domain.value_objects import DpeRating
from apartment_hunter.infrastructure.crawlers.base_crawler import ListingDetails
from apartment_hunter.infrastructure.crawlers.paruvendu_crawler import ParuVenduCrawler

_fake = Faker("fr_FR")

# Shaped like the real detail page: a legend printing every letter from A to G, then
# the two blocks that actually carry this listing's own rating.
_DETAIL_PAGE = """
<div class="DPE_greyPadd">
  <div class="DPE_noteglobale">
    <div class="DPE_ng_flex">
      <span class="NoteEnerg_A ">A</span>
      <span class="NoteEnerg_B ">B</span>
      <span class="NoteEnerg_C ">C</span>
      <span class="NoteEnerg_D ">D</span>
      <span class="NoteEnerg_E ">E</span>
      <span class="NoteEnerg_F NoteActive">F</span>
      <span class="NoteEnerg_G ">G</span>
    </div>
  </div>
  <div class="DPE_flex">
    <div class="DPE_consEnerGlob newDPE_glob">
      <div class="DPE_consEnerNote NoteEnerg_F">F</div>
      <div class="DPE_consEnerTxt newDPE">Classe Énergie<span>336 kWh/m² an</span></div>
    </div>
    <div class="DPE_effSerreGlob newDPE_glob">
      <div class="DPE_effSerreNote NoteGES2022_E">E</div>
      <div class="DPE_effSerreTxt">Indice d'émissions<span>60 kgCO2/m².an</span></div>
    </div>
  </div>
</div>
"""

_PAGE_WITHOUT_ENERGY = '<div class="DPE_greyPadd"><p>Aucun diagnostic fourni</p></div>'


def test_reads_the_listings_own_letters_not_the_first_of_the_scale() -> None:
    # Arrange
    soup = BeautifulSoup(_DETAIL_PAGE, "lxml")

    # Act
    details = ParuVenduCrawler.parse_details(soup)

    # Assert — a page-wide `NoteEnerg_([A-G])` search would answer "A" here
    assert details.dpe_rating is DpeRating.F
    assert details.ges_rating is DpeRating.E


def test_leaves_both_ratings_unknown_when_the_page_has_no_diagnosis() -> None:
    # Arrange
    soup = BeautifulSoup(_PAGE_WITHOUT_ENERGY, "lxml")

    # Act
    details = ParuVenduCrawler.parse_details(soup)

    # Assert
    assert details == ListingDetails()


def _build_card(listing_id: int, energy: str) -> str:
    return f"""
    <div class="blocAnnonce" data-id="{listing_id}">
      <h3><a href="/immobilier/location/appartement/{listing_id}A1KILHAP000">
        <span>Appartement 48 m<sup>2</sup> {_fake.city()} (74)</span>
      </a></h3>
      {energy}
    </div>
    """


def _build_energy(listing_id: int, letter: str, kwh: int, kg: int) -> str:
    return f"""
    <button aria-describedby="conso-emission-{listing_id}" class="trigger">
      DPE : <span class="rounded-md NoteEnerg_{letter}">{letter}</span>
    </button>
    <div id="conso-emission-{listing_id}" class="tooltip_dpe hidden">
      <span>{kwh}</span> kWh/m².an <span>{kg}</span> kg CO<sub>2</sub>/m².an
    </div>
    """


def _parse_card(html: str) -> Listing | None:
    card = BeautifulSoup(html, "lxml").select_one("div.blocAnnonce")
    assert card is not None
    return ParuVenduCrawler()._parse(card)


def test_the_card_carries_the_rating_the_captcha_hides_on_the_detail_page() -> None:
    # Arrange — detail pages answer with an anti-scraping captcha since 2026-10-28
    listing_id = _fake.random_int(1_000_000_000, 1_999_999_999)
    html = _build_card(listing_id, _build_energy(listing_id, "D", kwh=250, kg=55))

    # Act
    listing = _parse_card(html)

    # Assert — 55 kg CO2/m².an is class E on the 2021 scale
    assert listing is not None
    assert listing.dpe_rating is DpeRating.D
    assert listing.ges_rating is DpeRating.E


def test_a_card_without_a_diagnosis_leaves_both_ratings_unknown() -> None:
    # Arrange
    listing_id = _fake.random_int(1_000_000_000, 1_999_999_999)

    # Act
    listing = _parse_card(_build_card(listing_id, energy=""))

    # Assert
    assert listing is not None
    assert listing.dpe_rating is None
    assert listing.ges_rating is None
