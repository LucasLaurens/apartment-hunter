"""A home key spread over four nullable columns, shared by every judgement table.

Not serialised into one value: a listing without rooms or surface has no key, and SQL
must be able to say so.
"""

from decimal import Decimal
from typing import Any

from ...domain.value_objects import HomeKey

HOME_KEY_COLUMNS = ("home_city", "home_rooms", "home_surface_m2", "home_rent")


def home_key_to_row(key: HomeKey | None) -> tuple[str | int | None, ...]:
    if key is None:
        return (None, None, None, None)
    return (key.city, key.rooms, key.surface_m2, str(key.rent))


def home_key_from_row(r: dict[str, Any]) -> HomeKey | None:
    if r["home_city"] is None:
        return None
    return HomeKey(
        city=r["home_city"],
        rooms=r["home_rooms"],
        surface_m2=r["home_surface_m2"],
        rent=Decimal(r["home_rent"]),
    )
