"""A monthly total with no charges accounted for must never read as settled."""

from ..fakes.builders import build_listing


def test_a_rent_without_charges_is_marked_unknown() -> None:
    # Arrange — 800 € advertised, no provision published: ~900 € will be paid.
    listing = build_listing(price=800.0)

    # Act & Assert
    assert listing.charges_unknown


def test_a_published_provision_settles_the_total() -> None:
    # Act & Assert
    assert not build_listing(price=800.0, charges=90.0).charges_unknown


def test_a_charges_included_rent_settles_the_total_without_a_provision() -> None:
    # Arrange — "CC" says the figure already covers the charges; no amount needed.
    listing = build_listing(price=890.0, charges_included=True)

    # Act & Assert
    assert not listing.charges_unknown


def test_an_explicitly_excluded_charge_stays_unknown() -> None:
    # Arrange — "HC" says the total is a rent, and says nothing about how much more.
    listing = build_listing(price=800.0, charges_included=False)

    # Act & Assert
    assert listing.charges_unknown


def test_the_summary_line_carries_the_mark() -> None:
    # Arrange — the alert is one of the three readers that must not drop it.
    listing = build_listing(price=800.0)

    # Act
    summary = listing.build_summary_line()

    # Assert
    assert "charges non communiquées" in summary


def test_the_summary_line_stays_quiet_when_the_total_is_settled() -> None:
    # Arrange
    listing = build_listing(price=800.0, charges=90.0)

    # Act
    summary = listing.build_summary_line()

    # Assert
    assert "charges non communiquées" not in summary
