"""`BaseCrawler._enrich_details` — one detail fetch fills energy *and* date."""

from datetime import datetime, timedelta

from faker import Faker

from apartment_hunter.domain.entities import Listing, SearchFilter
from apartment_hunter.domain.value_objects import DpeRating, PublicationSource
from apartment_hunter.infrastructure.cache.ttl_cache import DETAIL_CACHE
from apartment_hunter.infrastructure.crawlers.base_crawler import BaseCrawler, ListingDetails
from tests.fakes.builders import build_listing

_fake = Faker("fr_FR")


class RecordingCrawler(BaseCrawler):
    """Concrete crawler whose detail pages are an in-memory dict, not the network."""

    source_name = "recording"

    def __init__(self, details_by_url: dict[str, ListingDetails]):
        super().__init__()
        self._details_by_url = details_by_url
        self.fetched_urls: list[str] = []

    async def fetch(self, search_filter: SearchFilter) -> list[Listing]:
        return []

    async def fetch_details(self, url: str) -> ListingDetails | None:
        self.fetched_urls.append(url)
        return self._details_by_url.get(url)


async def test_stamps_the_site_date_and_energy_from_the_detail_page() -> None:
    # Arrange
    listing = build_listing(dpe=None)
    published_at = datetime.now().replace(microsecond=0) - timedelta(days=9)
    crawler = RecordingCrawler(
        {
            listing.url: ListingDetails(
                dpe_rating=DpeRating.from_string("C"),
                ges_rating=DpeRating.from_string("B"),
                published_at=published_at,
            )
        }
    )

    # Act
    enriched = await crawler._enrich_details([listing], crawler.fetch_details)

    # Assert
    assert enriched[0].published_at == published_at
    assert enriched[0].published_at_source is PublicationSource.SITE
    assert enriched[0].has_site_publication_date
    assert enriched[0].dpe_rating == DpeRating.from_string("C")
    assert enriched[0].ges_rating == DpeRating.from_string("B")


async def test_keeps_the_first_seen_fallback_when_the_page_has_no_date() -> None:
    # Arrange
    listing = build_listing(dpe=None)
    crawler = RecordingCrawler({listing.url: ListingDetails(dpe_rating=DpeRating.from_string("D"))})

    # Act
    enriched = await crawler._enrich_details([listing], crawler.fetch_details)

    # Assert
    assert enriched[0].published_at == listing.published_at
    assert enriched[0].published_at_source is PublicationSource.FIRST_SEEN
    assert enriched[0].dpe_rating == DpeRating.from_string("D")


async def test_takes_the_furnishing_answer_from_the_detail_page() -> None:
    # Arrange — the card said nothing; the page's criteria table says "Meublé : oui"
    listing = build_listing(furnished=None)
    crawler = RecordingCrawler({listing.url: ListingDetails(furnished=True)})

    # Act
    enriched = await crawler._enrich_details([listing], crawler.fetch_details)

    # Assert — without this an "unfurnished" filter keeps every listing
    assert enriched[0].furnished is True


async def test_the_detail_page_corrects_what_the_card_advertised() -> None:
    # Arrange — the headline reads "meublé", the criteria table answers "Meublé : non"
    listing = build_listing(furnished=True)
    crawler = RecordingCrawler({listing.url: ListingDetails(furnished=False)})

    # Act
    enriched = await crawler._enrich_details([listing], crawler.fetch_details)

    # Assert
    assert enriched[0].furnished is False


async def test_keeps_the_card_furnishing_when_the_page_states_none() -> None:
    # Arrange
    listing = build_listing(furnished=True)
    crawler = RecordingCrawler({listing.url: ListingDetails(dpe_rating=DpeRating.from_string("D"))})

    # Act
    enriched = await crawler._enrich_details([listing], crawler.fetch_details)

    # Assert — an unreadable page must not blank what the card already proved
    assert enriched[0].furnished is True


async def test_caches_unreadable_pages_so_they_are_fetched_once() -> None:
    # Arrange — no entry for this URL: the fetch returns nothing
    listing = build_listing(dpe=None)
    DETAIL_CACHE.invalidate(listing.url)
    crawler = RecordingCrawler({})

    # Act
    await crawler._enrich_details([listing], crawler.fetch_details)
    again = await crawler._enrich_details([listing], crawler.fetch_details)

    # Assert
    assert crawler.fetched_urls == [listing.url]
    assert again[0].published_at_source is PublicationSource.FIRST_SEEN
