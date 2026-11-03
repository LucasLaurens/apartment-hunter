"""
Agence BFM — one local agency in Annecy, on the Netty platform.

curl_cffi, like every SSR crawler. Its legal notice forbids reproducing the site in
whole or in part without Netty's express consent, so the source runs only when the
hunter chose to ignore the sites' rules (`forbids_reproduction`, ADR-0012). robots.txt
allows everything but PDFs and asks `Crawl-delay: 5`.

The markup's class names are generated (`_se5lkg`) and change with every build; the
data is not in them. Each page carries its state as base64 JSON,
`window._TEMPLATE_DATA = JSON.parse(b64_to_utf8("…"))`, whose `prodId` maps a reference
(`LA4396`) to the whole record. Decoding that is base64 then JSON: nothing is evaluated.

`/location` holds the whole rental stock (9 records on 2026-11-03, parkings and a house
included), read once (`covers_radius`); apartments are kept by `prod_type`. A record
gives the rent and the charges provision apart, surface, rooms, storey, commune, postal
code, coordinates, photos, the description and the day it went online. The detail page
adds one thing the list lacks: the legal mention, « Classe énergie D, Classe climat D ».
"""

import base64
import json
import re
from datetime import datetime
from decimal import Decimal
from typing import Any, Final

from bs4 import BeautifulSoup
from loguru import logger

from ...domain.entities import Listing, SearchFilter
from ...domain.services import detect_furnished
from ...domain.value_objects import DpeRating, Floor, Location, Price, PublicationSource
from .base_crawler import BaseCrawler, ListingDetails, MissingCommuneError, build_listing_id

_BASE_URL: Final = "https://www.agencebfm-immo.com"
_LIST_URL: Final = f"{_BASE_URL}/location"
_STATE_RE: Final = re.compile(
    r'window\._TEMPLATE_DATA\s*=\s*JSON\.parse\(b64_to_utf8\("([A-Za-z0-9+/=]+)"\)\)'
)
_FLAT_TYPE: Final = "appt"
_RENTAL_OFFER: Final = 2  # `type_offer`: 1 sale, 2 rental
_ADVERTISER: Final = "Agence BFM"
_DPE_RE: Final = re.compile(r"Classe énergie\s*([A-G])\b")
_GES_RE: Final = re.compile(r"Classe climat\s*([A-G])\b")


def read_state(html: str) -> dict[str, Any]:
    """The page's decoded `_TEMPLATE_DATA`; {} when the page carries none."""
    found = _STATE_RE.search(html)
    if found is None:
        return {}
    state: Any = json.loads(base64.b64decode(found.group(1)).decode("utf-8"))
    return state if isinstance(state, dict) else {}


def read_records(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """The state's records by reference (`LA4396` → record)."""
    records = state.get("prodId")
    return records if isinstance(records, dict) else {}


def read_reference(url: str) -> str:
    """`…/appartement-t2-2-pieces-annecy-74000,LA4396` → `LA4396`."""
    return url.rsplit(",", 1)[-1]


def _read_text(field: Any) -> str:
    """A translated field (`{"fr": "…"}`) as plain text, tags stripped."""
    raw = field.get("fr", "") if isinstance(field, dict) else ""
    return BeautifulSoup(raw, "lxml").get_text(" ", strip=True) if raw else ""


def _parse_price(record: dict[str, Any]) -> Price:
    """Rent and provision apart when the site gives one, else the advertised figure.

    Without a provision the record prints « HC » and `rent_total` is the bare rent:
    left without charges, the listing reads « charges ? », as it should.
    """
    charges = record.get("charges")
    if charges:
        return Price(amount=Decimal(str(record["rent"])), charges=Decimal(str(charges)))
    return Price(amount=Decimal(str(record["rent_total"])))


def _parse_floor(record: dict[str, Any]) -> Floor | None:
    """The storey, with « dernier étage » when it is the building's last one.

    Netty writes 0 for every field nobody filled in, so 0 reads as unknown rather than
    rez-de-chaussée: a wrong RDC would hide the home behind `exclude_ground_floor`.
    """
    level = record.get("floor") or 0
    if level <= 0:
        return None
    return Floor.from_int(level, is_top=level == (record.get("floors") or 0))


class AgenceBfmCrawler(BaseCrawler):
    source_name = "agence-bfm"
    BASE_URL = _BASE_URL
    RATE_LIMIT_SECONDS = 5.0  # robots.txt Crawl-delay
    # One list, then one page per apartment: no commune to run in parallel.
    CITY_CONCURRENCY = 1
    covers_radius = True  # the agency's whole stock; ListingMatcher narrows it
    forbids_reproduction = True

    async def fetch(self, search_filter: SearchFilter) -> list[Listing]:
        html = await self._fetch_html(_LIST_URL)
        listings = self.parse_page(html) if html else []
        if listings:
            listings = await self._enrich_details(listings, self._fetch_details)
        logger.info(f"[{self.source_name}] {len(listings)} listings")
        return listings

    async def _fetch_details(self, url: str) -> ListingDetails | None:
        html = await self._fetch_html(url)
        return self.parse_details(html, read_reference(url)) if html else None

    def parse_page(self, html: str) -> list[Listing]:
        """The rental apartments among the page's records; parkings and houses dropped.

        shortcut: assumes `/location` lists the whole stock on one page (9 records on
        2026-11-03); the warning below says when the site starts paginating.
        """
        state = read_state(html)
        records = read_records(state)
        if len(records) < int(state.get("prodCount") or 0):
            logger.warning(
                f"[{self.source_name}] {len(records)} of {state['prodCount']} records "
                "on the list: the site paginates now"
            )
        return [
            listing
            for record in records.values()
            if record.get("prod_type") == _FLAT_TYPE
            and record.get("type_offer") == _RENTAL_OFFER
            and (listing := self._parse_record(record))
        ]

    def _parse_record(self, record: dict[str, Any]) -> Listing | None:
        slug = (record.get("url") or {}).get("fr", "")
        url = self.resolve_url(f"/location/{slug},{record.get('prod_ref', '')}")
        try:
            return self._build_listing(record, url)
        except Exception as exc:
            self._log_parse_error(url, json.dumps(record, ensure_ascii=False), exc)
            return None

    def _build_listing(self, record: dict[str, Any], url: str) -> Listing:
        city = str(record.get("city") or "").strip()
        if not city:
            raise MissingCommuneError
        geoloc = record.get("geoloc") or {}
        accurate = isinstance(geoloc, dict) and geoloc.get("accurate")
        description = _read_text(record.get("details"))
        online = record.get("time_online")
        price = _parse_price(record)
        return Listing(
            id=build_listing_id(url),
            url=url,
            title=str(record.get("title_auto") or ""),
            source=self.source_name,
            location=Location(
                city=city,
                postal_code=str(record.get("cp") or "") or None,
                latitude=float(geoloc["latitude"]) if accurate else None,
                longitude=float(geoloc["longitude"]) if accurate else None,
            ),
            price=price,
            charges_included=True if price.has_charges else None,
            surface_m2=float(record["surface"]) if record.get("surface") else None,
            rooms=int(record["rooms"]) if record.get("rooms") else None,
            floor=_parse_floor(record),
            # `mbl` is 1 on every record, furnished or not: only the wording is read.
            furnished=detect_furnished(description),
            description=description or None,
            advertiser=_ADVERTISER,
            images=tuple(str(photo) for photo in record.get("photos") or ()),
            published_at=datetime.fromtimestamp(online) if online else datetime.now(),
            published_at_source=(
                PublicationSource.SITE if online else PublicationSource.FIRST_SEEN
            ),
        )

    @staticmethod
    def parse_details(html: str, reference: str) -> ListingDetails:
        """DPE and GES from the record's legal mention; nothing else the list lacks."""
        legal = _read_text(read_records(read_state(html)).get(reference, {}).get("legal"))
        dpe = _DPE_RE.search(legal)
        ges = _GES_RE.search(legal)
        return ListingDetails(
            dpe_rating=DpeRating.from_string(dpe.group(1)) if dpe else None,
            ges_rating=DpeRating.from_string(ges.group(1)) if ges else None,
        )
