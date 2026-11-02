from dataclasses import dataclass, field
from datetime import datetime

from ..value_objects import DpeRating, Floor, Location, Price, PublicationSource
from ..value_objects.market_position import NOT_ASSESSED, MarketAssessment
from .dismissal import Dismissal


@dataclass(frozen=True)
class Listing:
    id: str  # SHA-256 of URL, stable dedup key
    url: str
    title: str
    source: str
    location: Location
    price: Price
    published_at: datetime
    published_at_source: PublicationSource = PublicationSource.FIRST_SEEN
    surface_m2: float | None = None
    rooms: int | None = None
    floor: Floor | None = None
    dpe_rating: DpeRating | None = None
    ges_rating: DpeRating | None = None
    furnished: bool | None = None
    charges_included: bool | None = None
    collective_heating: bool | None = None
    description: str | None = None
    advertiser: str | None = None
    images: tuple[str, ...] = field(default_factory=tuple)
    fetched_at: datetime = field(default_factory=datetime.now)
    # Moved forward by every crawl that returns the listing again; `fetched_at` stays
    # the first sighting. A listing built by a crawler is, by definition, seen now.
    last_seen_at: datetime = field(default_factory=datetime.now)
    # Set by `GetTopListings` from the openings, never stored on the row: the first time
    # the hunter followed a link to this home, through any of its publications (ADR-0009).
    opened_at: datetime | None = None
    # Set by `GetTopListings`, never stored: days its source has stopped answering the
    # filter, 0 while it answers. Non-zero means "maybe expired", see `expiry.py`.
    source_down_days: int = 0
    # Set by `GetTopListings`, never stored: where the rent sits against the Carte des
    # loyers for this commune (ADR-0010), or why it has no position.
    market_position: MarketAssessment = NOT_ASSESSED
    # Set by `DismissedHomes.annotate`, never stored: a dismissal of this home at another
    # rent, which no longer hides it but is worth saying (ADR-0009).
    former_dismissal: Dismissal | None = None
    # Set by `RestoredHomes.annotate`, never stored: the hunter dismissed this home once,
    # then took it back (ADR-0009).
    restored_at: datetime | None = None

    @property
    def opened(self) -> bool:
        """What makes a listing stop being *Nouvelle* (ADR-0002)."""
        return self.opened_at is not None

    @property
    def has_site_publication_date(self) -> bool:
        """True when the site advertised the date, False when it is our first-seen time."""
        return self.published_at_source is PublicationSource.SITE

    @property
    def charges_unknown(self) -> bool:
        """True when the monthly total is a rent with no charges accounted for.

        The budget is reasoned charges included, so a listing that publishes neither a
        provision nor a "charges comprises" flag has a total that understates what it
        will cost — 800 € advertised, ~900 € paid. Readers must mark it rather than
        print the figure as if it were settled.
        """
        return not self.price.has_charges and self.charges_included is not True

    def format_published_label(self) -> str:
        """Day (plus time for today's listings) — 'le' wording is up to the caller."""
        if self.published_at.date() == datetime.now().date():
            return self.published_at.strftime("%d/%m %H:%M")
        return self.published_at.strftime("%d/%m/%Y")

    def build_summary_line(self) -> str:
        parts = [self.title]
        if self.surface_m2:
            parts.append(f"{self.surface_m2:.0f}m²")
        if self.rooms:
            parts.append(f"{self.rooms}p")
        parts.append(self.price.format_total())
        if self.charges_unknown:
            parts.append("charges non communiquées")
        if self.dpe_rating:
            parts.append(f"DPE {self.dpe_rating.value}")
        if self.ges_rating:
            parts.append(f"GES {self.ges_rating.value}")
        prefix = "paru" if self.has_site_publication_date else "vu"
        parts.append(f"{prefix} {self.format_published_label()}")
        return " · ".join(parts)
