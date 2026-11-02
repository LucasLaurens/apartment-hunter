"""Money as the hunter reads it, in every reader: « 1 210 € CC » (ticket 08, R2/R4/R11)."""

from decimal import Decimal

from faker import Faker

from apartment_hunter.domain.value_objects import Price

_fake = Faker("fr_FR")
NARROW_NBSP = " "


def test_a_total_with_charges_reads_charges_included() -> None:
    # Arrange
    price = Price(amount=Decimal("1150"), charges=Decimal("60"))

    # Act & Assert — thousands separated by a narrow no-break space
    assert price.format_total() == f"1{NARROW_NBSP}210{NARROW_NBSP}€ CC"


def test_a_rent_alone_carries_no_cc() -> None:
    # Arrange
    amount = _fake.random_int(500, 999)

    # Act & Assert — "CC" would be a claim the listing never made
    assert Price(amount=Decimal(amount)).format_total() == f"{amount}{NARROW_NBSP}€"


def test_the_composition_names_rent_and_charges() -> None:
    # Arrange
    price = Price(amount=Decimal("1150"), charges=Decimal("60"))

    # Act
    composition = price.format_display()

    # Assert
    assert composition == f"loyer 1{NARROW_NBSP}150{NARROW_NBSP}€ + 60{NARROW_NBSP}€ de charges"


def test_cents_round_half_up() -> None:
    # Act & Assert
    assert Price(amount=Decimal("899.5")).format_total() == f"900{NARROW_NBSP}€"
