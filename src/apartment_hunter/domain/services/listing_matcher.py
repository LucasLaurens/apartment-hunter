import re
from datetime import datetime, timedelta
from functools import lru_cache

from geopy.distance import geodesic

from ..entities import Listing, SearchFilter
from .commune_names import fold_commune_name
from .furnishing import detect_furnished
from .listing_order import build_published_key
from .tenancy_scope import is_out_of_scope_tenancy

_RDC_RE = re.compile(r"\bRDC\b|[Rr]ez[- ][Dd]e[- ][Cc]haussée", re.I)


@lru_cache(maxsize=256)
def _normalise(cities: tuple[str, ...]) -> frozenset[str]:
    """Folded city names (see `fold_commune_name`) — memoised per city tuple.

    The matcher runs once per (listing, filter) pair, and the purge runs it over
    every stored listing against every saved filter, so rebuilding these sets inline
    would cost O(listings × cities). The cache makes it O(cities) once per filter.
    """
    return frozenset(fold_commune_name(city) for city in cities)


class ListingMatcher:
    """Pure domain logic — no IO, no framework deps."""

    def __init__(self, geocoded_cities: dict[str, tuple[float, float]]):
        # folded city name → (lat, lon); O(n) once, n = communes in radius
        self._geocoded_cities = {
            fold_commune_name(name): coords for name, coords in geocoded_cities.items()
        }

    def matches(self, listing: Listing, search_filter: SearchFilter) -> bool:
        """True when the listing satisfies every criterion of the filter.

        Criteria are evaluated lazily, cheapest-to-reject first is not assumed — the
        generator simply stops at the first failure instead of running every check
        (the geodesic distance in `_matches_location` is by far the costliest).
        """
        checks = (
            self._is_a_home,  # first: a room or a holiday let is never a candidate
            self._matches_price,
            self._matches_surface,
            self._matches_rooms,
            self._matches_floor,
            self._matches_dpe,
            self._matches_furnished,
            self._matches_charges,
            self._matches_heating,
            self._matches_photos,
            self._matches_advertiser,
            self._matches_age,
            self._matches_location,  # last: the only one doing geodesic maths
        )
        return all(check(listing, search_filter) for check in checks)

    def _is_a_home(self, listing: Listing, f: SearchFilter) -> bool:
        """Reject rooms in a shared flat and short-term lets, whatever the filter says.

        Not a criterion the user sets: it is what the tool is about. Takes `f` only to
        share the signature of the other checks.
        """
        return not is_out_of_scope_tenancy(listing.title, listing.description)

    def _matches_location(self, listing: Listing, f: SearchFilter) -> bool:
        city_normalized = fold_commune_name(listing.location.city)

        if city_normalized in _normalise(tuple(f.excluded_cities)):
            return False

        apt_coords = self.find_position(listing)
        if apt_coords is None:
            # Town unknown to the geocoder — keep only on an exact filter-city match.
            return city_normalized in _normalise(tuple(f.cities))

        for city_name in f.cities:
            city_coords = self.find_commune_position(city_name)
            if city_coords and geodesic(apt_coords, city_coords).km <= f.radius_km:
                return True

        return False

    def find_position(self, listing: Listing) -> tuple[float, float] | None:
        """Where the radius check places a listing: its own coordinates, else its commune's.

        The map asks this too, so a pin always sits where the matcher measured from.
        None when neither is known.
        """
        if listing.location.has_coordinates:
            return listing.location.coordinates
        return self.find_commune_position(listing.location.city)

    def find_commune_position(self, city: str) -> tuple[float, float] | None:
        return self._geocoded_cities.get(fold_commune_name(city))

    def _matches_price(self, listing: Listing, f: SearchFilter) -> bool:
        total = float(listing.price.total)
        if f.min_price is not None and total < f.min_price:
            return False
        if f.max_price is not None and total > f.max_price:
            return False
        return True

    def _matches_surface(self, listing: Listing, f: SearchFilter) -> bool:
        if listing.surface_m2 is None:
            return True
        if f.min_surface_m2 is not None and listing.surface_m2 < f.min_surface_m2:
            return False
        if f.max_surface_m2 is not None and listing.surface_m2 > f.max_surface_m2:
            return False
        return True

    def _matches_rooms(self, listing: Listing, f: SearchFilter) -> bool:
        if listing.rooms is None:
            return True
        if f.min_rooms is not None and listing.rooms < f.min_rooms:
            return False
        if f.max_rooms is not None and listing.rooms > f.max_rooms:
            return False
        return True

    def _matches_floor(self, listing: Listing, f: SearchFilter) -> bool:
        floor = listing.floor
        if floor is None or not floor.is_known:
            # top_floor_only: unknown floor can't be confirmed → exclude
            if f.top_floor_only:
                return False
            # exclude_ground_floor: check title/description for RDC keywords
            if f.exclude_ground_floor:
                text = " ".join(filter(None, [listing.title, listing.description]))
                if _RDC_RE.search(text):
                    return False
            return True
        if f.exclude_ground_floor and floor.is_ground:
            return False
        if f.exclude_first_floor and floor.is_first:
            return False
        if f.top_floor_only and not floor.is_top:
            return False
        return True

    def _matches_dpe(self, listing: Listing, f: SearchFilter) -> bool:
        if not f.accepted_dpe_ratings:
            return True
        if listing.dpe_rating is None:
            return True
        return listing.dpe_rating in f.accepted_dpe_ratings

    def _matches_furnished(self, listing: Listing, f: SearchFilter) -> bool:
        if f.furnished is None:
            return True
        furnished = listing.furnished
        if furnished is None:
            # Most crawlers don't expose a furnished flag — infer from the wording so
            # an "unfurnished" filter actually drops listings advertised as "meublé".
            furnished = detect_furnished(
                " ".join(filter(None, [listing.title, listing.description]))
            )
        if furnished is None:
            return True  # genuinely unknown — can't prove a mismatch, so keep
        return furnished == f.furnished

    def _matches_charges(self, listing: Listing, f: SearchFilter) -> bool:
        if f.charges_included is None:
            return True
        if listing.charges_included is None:
            return True
        return listing.charges_included == f.charges_included

    def _matches_heating(self, listing: Listing, f: SearchFilter) -> bool:
        if f.collective_heating is None:
            return True
        if listing.collective_heating is None:
            return True
        return listing.collective_heating == f.collective_heating

    def _matches_photos(self, listing: Listing, f: SearchFilter) -> bool:
        """Reject only a listing we know has too few photos.

        No crawler fills `images` yet, so an empty tuple means "not collected", not
        "this home has no photo". Counting it as zero made `min_photos > 0` reject
        every listing — the same trap the DPE and furnished checks avoid by letting an
        unknown through. An empty set of images is therefore an unknown.
        """
        if f.min_photos <= 0 or not listing.images:
            return True
        return len(listing.images) >= f.min_photos

    def _matches_advertiser(self, listing: Listing, f: SearchFilter) -> bool:
        """Drop listings whose advertiser the user banned.

        Substring, not equality: an advertiser prints its network name with a branch
        appended ("Laforêt Annecy", "Century 21 Lac Bleu"), and the user types the
        network. O(len(excluded) × len(advertiser)) — the list is a handful of names.
        """
        if not f.excluded_advertisers or not listing.advertiser:
            return True
        advertiser = listing.advertiser.strip().lower()
        return not any(banned in advertiser for banned in _normalise(tuple(f.excluded_advertisers)))

    def _matches_age(self, listing: Listing, f: SearchFilter) -> bool:
        if f.max_age_days is None:
            return True
        cutoff = datetime.now() - timedelta(days=f.max_age_days)
        # Local wall-clock time, as the sort and the SQL window read it: UTC here put an
        # aware date two hours off the cutoff the list showed.
        return build_published_key(listing) >= cutoff
