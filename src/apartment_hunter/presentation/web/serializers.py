"""Convert domain entities to JSON-serializable dicts for the web API."""

from datetime import date
from typing import Any

from ...application.use_cases import FilterArea, FilterMap
from ...domain.entities import Dismissal, Listing, SearchFilter
from ...domain.services import (
    ListingGroup,
    UnreachableSource,
    build_rental_ban_warning,
    build_source_down_warning,
    detect_advertiser_kind,
    find_network,
    format_restored_label,
)
from ...domain.value_objects import MarketAssessment, MarketPosition
from ..dismissal_reasons import REASON_LABELS


def market_position_to_dict(position: MarketAssessment) -> dict[str, Any]:
    """Label as the review and the alert print it; `reference` is '' without one."""
    if isinstance(position, MarketPosition):
        return {
            "label": position.format_label(),
            "outside_range": position.is_outside_range,
            "reference": position.reference.format_detail(),
        }
    return {"label": position.format_label(), "outside_range": False, "reference": ""}


def listing_to_dict(listing: Listing, today: date | None = None) -> dict[str, Any]:
    """One listing as JSON. `today` dates the rental-ban wording; defaults to now."""
    on = today or date.today()
    return {
        "id": listing.id,
        "url": listing.url,
        "title": listing.title,
        "source": listing.source,
        "location": {
            "city": listing.location.city,
            "postal_code": listing.location.postal_code,
            "lat": listing.location.latitude,
            "lng": listing.location.longitude,
            "display": listing.location.format_display(),
        },
        "price": {
            "amount": float(listing.price.amount),
            "charges": float(listing.price.charges) if listing.price.charges else None,
            "total": float(listing.price.total),
            "display": listing.price.format_display(),
            "display_total": listing.price.format_total(),
        },
        "surface_m2": listing.surface_m2,
        "rooms": listing.rooms,
        "floor": {
            "level": listing.floor.level,
            "is_top": listing.floor.is_top,
            "is_ground": listing.floor.is_ground,
            "label": listing.floor.format_label(),
        }
        if listing.floor
        else None,
        "dpe_rating": listing.dpe_rating.value if listing.dpe_rating else None,
        "ges_rating": listing.ges_rating.value if listing.ges_rating else None,
        # '' when the rating carries no ban — the card shows the sentence as-is.
        "rental_ban_warning": build_rental_ban_warning(listing.dpe_rating, on),
        "furnished": listing.furnished,
        "charges_included": listing.charges_included,
        # True → the monthly total is a rent with no charges accounted for.
        "charges_unknown": listing.charges_unknown,
        # '' while the source answers; otherwise the listing may be gone (ticket 13).
        "source_down_warning": build_source_down_warning(listing.source_down_days),
        "market_position": market_position_to_dict(listing.market_position),
        "collective_heating": listing.collective_heating,
        "advertiser": listing.advertiser,
        "advertiser_kind": detect_advertiser_kind(listing.source, listing.advertiser).value,
        # '' when the branch belongs to no network we know — printed as-is.
        "network": find_network(listing.advertiser),
        # False → never opened towards its source, which is what "new" means here.
        "opened": listing.opened,
        # '' unless this home was dismissed at another rent: it came back (ADR-0009).
        "former_dismissal": (
            listing.former_dismissal.format_mention() if listing.former_dismissal else ""
        ),
        # '' unless the hunter dismissed this home once and took it back.
        "restored": format_restored_label(listing.restored_at) if listing.restored_at else "",
        "description": listing.description,
        "images": list(listing.images),
        "published_at": listing.published_at.isoformat() if listing.published_at else None,
        # False → the site published no date and this is our first-seen time.
        "published_at_from_site": listing.has_site_publication_date,
    }


def group_to_dict(group: ListingGroup, today: date | None = None) -> dict[str, Any]:
    """One home as JSON: the listing to show, plus the re-publications behind it.

    The duplicates travel whole, each with its own link — a wrong grouping must cost a
    glance, never a missed home.
    """
    return {
        **listing_to_dict(group.primary, today),
        "also_on": [listing_to_dict(other, today) for other in group.others],
        "sources": list(group.sources),
    }


def _position_to_dict(position: tuple[float, float] | None) -> dict[str, float] | None:
    return {"lat": position[0], "lng": position[1]} if position else None


def filter_map_to_dict(filter_map: FilterMap) -> dict[str, Any]:
    """One pin per commune, each with the homes the list shows there."""
    return {
        "radius_km": filter_map.radius_km,
        "centre": _position_to_dict(filter_map.centre),
        "pins": [
            {
                "name": pin.name,
                **(_position_to_dict(pin.position) or {}),
                "homes": [group_to_dict(group) for group in pin.homes],
            }
            for pin in filter_map.pins
        ],
        "unplaced": filter_map.unplaced,
    }


def filter_area_to_dict(area: FilterArea) -> dict[str, Any]:
    return {
        "radius_km": area.radius_km,
        "centre": _position_to_dict(area.centre),
        "communes": [
            {"name": name, **(_position_to_dict(position) or {})}
            for name, position in area.communes
        ],
    }


def dismissal_to_dict(dismissal: Dismissal) -> dict[str, Any]:
    """What the restore page shows of a dismissed home: its snapshot, not the listing."""
    key = dismissal.home_key
    return {
        "listing_id": dismissal.listing_id,
        "source": dismissal.source,
        "city": key.city if key else "",
        "rooms": key.rooms if key else None,
        "surface_m2": dismissal.surface_m2,
        "total_price": float(dismissal.total_price),
        "reason": REASON_LABELS[dismissal.reason],
        "note": dismissal.note,
        "dismissed_at": dismissal.dismissed_at.isoformat(),
    }


def unreachable_source_to_dict(source: UnreachableSource) -> dict[str, Any]:
    return {
        "source": source.source,
        "down_days": source.down_days,
        "hidden_count": source.hidden_count,
    }


def filter_to_dict(f: SearchFilter) -> dict[str, Any]:
    return {
        "id": f.id,
        "name": f.name,
        "cities": f.cities,
        "radius_km": f.radius_km,
        "excluded_cities": f.excluded_cities,
        "min_price": f.min_price,
        "max_price": f.max_price,
        "min_surface_m2": f.min_surface_m2,
        "max_surface_m2": f.max_surface_m2,
        "min_rooms": f.min_rooms,
        "max_rooms": f.max_rooms,
        "furnished": f.furnished,
        "accepted_dpe_ratings": sorted(r.value for r in f.accepted_dpe_ratings),
        "max_results": f.max_results,
        "charges_included": f.charges_included,
        "collective_heating": f.collective_heating,
        "min_photos": f.min_photos,
        "excluded_advertisers": f.excluded_advertisers,
        "max_age_days": f.max_age_days,
        "exclude_ground_floor": f.exclude_ground_floor,
        "exclude_first_floor": f.exclude_first_floor,
        "top_floor_only": f.top_floor_only,
        "enabled": f.enabled,
        "notification_interval_minutes": f.notification_interval_minutes,
        "refresh_interval_minutes": f.refresh_interval_minutes,
    }
