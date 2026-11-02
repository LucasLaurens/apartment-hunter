"""Square Habitat parsing, on pages shaped like the site's own ng-state JSON."""

import json
from decimal import Decimal

from faker import Faker

from apartment_hunter.domain.value_objects import DpeRating, PublicationSource
from apartment_hunter.infrastructure.crawlers.squarehabitat_crawler import (
    SquareHabitatCrawler,
    find_department_page,
)

_fake = Faker("fr_FR")
_DETAIL_PATH = (
    "/square-habitat-des-savoie/annonces/biens/location/appartement/annecy-le-vieux/{ref}"
)


def _build_bien(**overrides: object) -> dict[str, object]:
    bien: dict[str, object] = {
        "codeRef": _fake.uuid4(),
        "codeCategorie": "LOCATION",
        "typeBien": "appartement",
        "ville": "ANNECY  LE VIEUX",
        "codePostal": "74940",
        "nbPieces": _fake.random_int(1, 5),
        "surfaceHabitable": float(_fake.random_int(20, 120)),
        "prix": _fake.random_int(600, 2500),
        "latitude": 45.914,
        "longitude": 6.142,
        "dateCreation": "2026-10-28T12:06:35.587786Z",
        "medias": [{"type": "Photo", "externalId": _fake.uuid4(), "extension": "webp"}],
    }
    bien.update(overrides)
    return bien


def _build_page(biens: list[dict[str, object]], linked: list[dict[str, object]]) -> str:
    state = {"apiBienUrl/bien": {"pagination": {"totalItems": len(biens)}, "biens": biens}}
    links = "".join(f'<a href="{_DETAIL_PATH.format(ref=b["codeRef"])}">Voir</a>' for b in linked)
    return (
        f"<html><body>{links}"
        f'<script id="ng-state" type="application/json">{json.dumps(state)}</script>'
        "</body></html>"
    )


def test_a_rental_flat_is_read_with_its_coordinates_and_settled_total() -> None:
    # Arrange
    bien = _build_bien()
    html = _build_page([bien], [bien])

    # Act
    [listing] = SquareHabitatCrawler().parse_page(html)

    # Assert
    assert listing.location.city == "Annecy Le Vieux"
    assert listing.location.coordinates == (45.914, 6.142)
    assert listing.price.amount == Decimal(str(bien["prix"]))
    assert not listing.charges_unknown
    assert listing.published_at_source is PublicationSource.SITE
    assert listing.url.endswith(str(bien["codeRef"]))
    assert len(listing.images) == 1


def test_a_house_a_sale_or_an_unlinked_card_is_left_out() -> None:
    # Arrange
    house = _build_bien(typeBien="maison")
    sale = _build_bien(codeCategorie="VENTE")
    unlinked = _build_bien()
    html = _build_page([house, sale, unlinked], [house, sale])

    # Act & Assert
    assert SquareHabitatCrawler().parse_page(html) == []


def test_the_detail_page_adds_energy_storey_and_furnishing() -> None:
    # Arrange
    state = {
        "apiUrl/page/details-page?PageType=FICHE_BIEN_LOCATION&slug=x": {
            "bienDetails": {
                "dpeInfos": {"dpeLettre": "B", "gesLettre": "A"},
                "logementInfos": {"etage": "5", "nbEtagesBatiment": 5, "meuble": False},
            }
        }
    }
    html = f'<script id="ng-state" type="application/json">{json.dumps(state)}</script>'

    # Act
    details = SquareHabitatCrawler.parse_details(html)

    # Assert
    assert (details.dpe_rating, details.ges_rating) == (DpeRating.B, DpeRating.A)
    assert details.floor is not None and details.floor.level == 5 and details.floor.is_top
    assert details.furnished is False


def test_the_department_page_is_read_from_the_sitemap() -> None:
    # Arrange
    base = "https://www.squarehabitat.fr/annonces/location/bien/appartement/immobilier"
    sitemap = (
        f"<urlset><url><loc>{base}/auvergne-rhone-alpes/haute-savoie/annecy-74000</loc></url>"
        f"<url><loc>{base}/auvergne-rhone-alpes/haute-savoie-74</loc></url></urlset>"
    )

    # Act & Assert
    assert find_department_page(sitemap, "74") == f"{base}/auvergne-rhone-alpes/haute-savoie-74"
    assert find_department_page(sitemap, "73") is None
