import copy
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Final

from ..value_objects import DpeRating

# Defaults shared by every entry point (CLI wizard, web form, stored-filter loader),
# so a filter created one way behaves like one created another way.
DEFAULT_RADIUS_KM: Final = 20.0
DEFAULT_MAX_RESULTS: Final = 25
DEFAULT_NOTIFICATION_INTERVAL_MINUTES: Final = 15
DEFAULT_REFRESH_INTERVAL_MINUTES: Final = 30
DEFAULT_FILTER_NAME: Final = "Sans nom"

# Bounds the filter refuses to be built outside of. They are not cosmetic: a
# non-positive interval puts the watch loop's next deadline in the past, so it
# re-crawls every source on every tick (~1s), and a huge radius expands the crawl to
# thousands of communes. Both hammer the sources and get the IP banned.
MIN_INTERVAL_MINUTES: Final = 5
MIN_RADIUS_KM: Final = 1.0
MAX_RADIUS_KM: Final = 150.0
MIN_MAX_RESULTS: Final = 1
MAX_MAX_RESULTS: Final = 500
# Each city is one Nominatim call, and Nominatim allows one a second.
MAX_CITIES: Final = 10
# Ten years: wide enough for any search, narrow enough for `now - max_age_days` to stay
# a date (10**30 days was accepted, and every page of that filter answered 500).
MAX_AGE_DAYS: Final = 3650


class FilterBoundError(ValueError):
    """A criterion outside its bounds, naming the field so a form can point at it."""

    def __init__(self, field_name: str, message: str):
        super().__init__(message)
        self.field_name = field_name


def clamp_int(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def clamp_float(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass
class SearchFilter:
    id: str
    name: str
    cities: list[str]
    radius_km: float = DEFAULT_RADIUS_KM
    excluded_cities: list[str] = field(default_factory=list)

    # Price
    min_price: int | None = None
    max_price: int | None = None

    # Surface
    min_surface_m2: float | None = None
    max_surface_m2: float | None = None

    # Rooms
    min_rooms: int | None = None
    max_rooms: int | None = None

    # Listing features
    furnished: bool | None = None  # None = indifferent
    exclude_ground_floor: bool = False
    exclude_first_floor: bool = False
    top_floor_only: bool = False
    accepted_dpe_ratings: set[DpeRating] = field(default_factory=set)  # empty = no DPE filter
    charges_included: bool | None = None
    collective_heating: bool | None = None

    # Quality filters
    min_photos: int = 0  # skip listings with no photos
    excluded_advertisers: list[str] = field(default_factory=list)

    # Freshness
    max_age_days: int | None = None  # None = no limit; 14 = last 2 weeks

    # Result cap — how many matched listings to surface. Above PAGE_SIZE the UI paginates.
    max_results: int = DEFAULT_MAX_RESULTS

    # Scheduler
    notification_interval_minutes: int = DEFAULT_NOTIFICATION_INTERVAL_MINUTES
    refresh_interval_minutes: int = DEFAULT_REFRESH_INTERVAL_MINUTES
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Refuse a filter that would make the crawler misbehave or the query absurd."""
        if not MIN_RADIUS_KM <= self.radius_km <= MAX_RADIUS_KM:
            raise FilterBoundError(
                "radius_km",
                f"radius_km must be between {MIN_RADIUS_KM} and {MAX_RADIUS_KM}, "
                f"got {self.radius_km}",
            )
        for label, minutes in (
            ("notification_interval_minutes", self.notification_interval_minutes),
            ("refresh_interval_minutes", self.refresh_interval_minutes),
        ):
            if minutes < MIN_INTERVAL_MINUTES:
                raise FilterBoundError(
                    label, f"{label} must be at least {MIN_INTERVAL_MINUTES}, got {minutes}"
                )
        if not MIN_MAX_RESULTS <= self.max_results <= MAX_MAX_RESULTS:
            raise FilterBoundError(
                "max_results",
                f"max_results must be between {MIN_MAX_RESULTS} and {MAX_MAX_RESULTS}, "
                f"got {self.max_results}",
            )
        if len(self.cities) > MAX_CITIES:
            raise FilterBoundError(
                "cities", f"cities holds at most {MAX_CITIES} names, got {len(self.cities)}"
            )
        if self.max_age_days is not None and self.max_age_days > MAX_AGE_DAYS:
            raise FilterBoundError(
                "max_age_days", f"max_age_days is at most {MAX_AGE_DAYS}, got {self.max_age_days}"
            )
        self._reject_negatives_and_non_numbers()

    def with_crawl_cities(self, cities: list[str]) -> "SearchFilter":
        """This filter, crawling `cities`: the communes in radius, which outnumber
        MAX_CITIES. That bound caps the names the hunter types, each one a Nominatim
        call; `dataclasses.replace` would re-run it and refuse the crawl list."""
        expanded = copy.copy(self)
        expanded.cities = list(cities)
        return expanded

    def _reject_negatives_and_non_numbers(self) -> None:
        negatives = {
            "min_price": self.min_price,
            "max_price": self.max_price,
            "min_surface_m2": self.min_surface_m2,
            "max_surface_m2": self.max_surface_m2,
            "min_rooms": self.min_rooms,
            "max_rooms": self.max_rooms,
            "max_age_days": self.max_age_days,
            "min_photos": self.min_photos,
        }
        for label, value in negatives.items():
            if value is None:
                continue
            # « nan » passes `< 0` and every later comparison: refuse it by name.
            if not math.isfinite(value):
                raise FilterBoundError(label, f"{label} must be a number, got {value}")
            if value < 0:
                raise FilterBoundError(label, f"{label} cannot be negative, got {value}")
