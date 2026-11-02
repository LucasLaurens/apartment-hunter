"""The card price is read on the node that holds "€" — never a price per square metre."""

from bs4 import BeautifulSoup
from faker import Faker

from apartment_hunter.infrastructure.crawlers.base_crawler import parse_price_from_euro_node

_fake = Faker("fr_FR")


def _parse(html: str) -> int:
    return int(parse_price_from_euro_node(BeautifulSoup(html, "lxml")))


def test_a_monthly_price_is_read() -> None:
    # Arrange — "/mois" once fell to the per-square-metre test and the price became 0
    rent = _fake.random_int(500, 2500)

    # Act & Assert
    assert _parse(f"<div><span>{rent} €<span> /mois</span></span></div>") == rent


def test_a_price_per_square_metre_is_skipped() -> None:
    # Arrange
    rent = _fake.random_int(500, 2500)
    html = f"<div><p>{_fake.random_int(10, 40)} €/m²</p><p>{rent} €</p></div>"

    # Act & Assert
    assert _parse(html) == rent


def test_thousands_with_a_no_break_space_are_read() -> None:
    # Act & Assert
    assert _parse("<div><b>1\xa0250 €</b></div>") == 1250
