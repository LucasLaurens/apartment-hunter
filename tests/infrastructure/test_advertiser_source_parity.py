"""The advertiser classification and the crawler list are two spellings of one fact.

`domain/services/advertiser.py` names every source and says which kind of advertiser
it carries. Adding a crawler without classifying it would silently answer "inconnu"
for that whole source, and the fee-bearing advertiser ads would stop being marked. This
test fails the moment the two lists disagree.
"""

from apartment_hunter.domain.services import (
    AGENCY_ONLY_SOURCES,
    MIXED_SOURCES,
    PRIVATE_ONLY_SOURCES,
)
from apartment_hunter.infrastructure.config import Settings
from apartment_hunter.infrastructure.container import build_crawlers


def test_every_crawler_source_is_classified() -> None:
    # Arrange
    classified = PRIVATE_ONLY_SOURCES | AGENCY_ONLY_SOURCES | MIXED_SOURCES

    # Act
    crawled = {crawler.source_name for crawler in build_crawlers(Settings())}

    # Assert
    assert crawled == classified


def test_the_three_families_do_not_overlap() -> None:
    # Act & Assert — a source is private-only, advertiser-only or mixed, never two of them.
    assert not PRIVATE_ONLY_SOURCES & AGENCY_ONLY_SOURCES
    assert not PRIVATE_ONLY_SOURCES & MIXED_SOURCES
    assert not AGENCY_ONLY_SOURCES & MIXED_SOURCES
