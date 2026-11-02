"""
Seed all predefined filters into the database.
Usage: uv run python scripts/seed_filters.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from apartment_hunter.domain.entities import SearchFilter
from apartment_hunter.domain.value_objects import DpeRating
from apartment_hunter.infrastructure.config import get_settings
from apartment_hunter.infrastructure.container import Container

FILTERS: list[SearchFilter] = [
    SearchFilter(
        id="paris-01",
        name="Paris premium",
        cities=["Paris"],
        radius_km=8.0,
        excluded_cities=["Saint-Denis", "Aubervilliers", "Ivry-sur-Seine"],
        min_price=1600,
        max_price=2800,
        min_surface_m2=55.0,
        min_rooms=3,
        furnished=None,
        exclude_ground_floor=True,
        exclude_first_floor=False,
        top_floor_only=False,
        accepted_dpe_ratings=DpeRating.up_to(DpeRating.C),
        min_photos=2,
        notification_interval_minutes=15,
        enabled=True,
    ),
    SearchFilter(
        id="paris-02",
        name="Studio économique",
        cities=["Paris"],
        radius_km=8.0,
        excluded_cities=[],
        min_price=700,
        max_price=1100,
        min_surface_m2=20.0,
        max_surface_m2=40.0,
        min_rooms=1,
        max_rooms=2,
        furnished=True,
        exclude_ground_floor=True,
        exclude_first_floor=False,
        top_floor_only=False,
        accepted_dpe_ratings=DpeRating.up_to(DpeRating.D),
        charges_included=True,
        min_photos=1,
        notification_interval_minutes=10,
        enabled=True,
    ),
    SearchFilter(
        id="paris-03",
        name="Grand appart famille",
        cities=["Paris", "Vincennes", "Montreuil"],
        radius_km=6.0,
        excluded_cities=[],
        min_price=2000,
        max_price=3500,
        min_surface_m2=80.0,
        min_rooms=4,
        furnished=False,
        exclude_ground_floor=True,
        exclude_first_floor=False,
        top_floor_only=False,
        accepted_dpe_ratings=DpeRating.up_to(DpeRating.D),
        min_photos=3,
        notification_interval_minutes=20,
        enabled=True,
    ),
    SearchFilter(
        id="paris-04",
        name="Dernier étage",
        cities=["Paris"],
        radius_km=10.0,
        excluded_cities=[],
        min_price=1100,
        max_price=2400,
        min_surface_m2=40.0,
        exclude_ground_floor=True,
        exclude_first_floor=True,
        top_floor_only=True,
        accepted_dpe_ratings=DpeRating.up_to(DpeRating.D),
        notification_interval_minutes=15,
        enabled=True,
    ),
    SearchFilter(
        id="paris-05",
        name="Propriétaires directs",
        cities=["Paris"],
        radius_km=10.0,
        excluded_cities=[],
        min_price=900,
        max_price=1600,
        min_surface_m2=40.0,
        accepted_dpe_ratings=DpeRating.up_to(DpeRating.D),
        min_photos=1,
        notification_interval_minutes=15,
        enabled=True,
    ),
]


async def main() -> None:
    settings = get_settings()
    container = Container(settings)
    await container.repository.connect()
    manage = container.make_manage_filters_use_case()

    for f in FILTERS:
        await manage.save(f)
        print(f"✓ [{f.id}] {f.name}")

    await container.close()
    print(f"\n{len(FILTERS)} filters saved to {settings.database_url}")


asyncio.run(main())
