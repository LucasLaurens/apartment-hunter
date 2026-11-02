from dataclasses import dataclass


@dataclass(frozen=True)
class Location:
    city: str
    postal_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    full_address: str | None = None
    department: str | None = None

    @property
    def has_coordinates(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    @property
    def coordinates(self) -> tuple[float, float] | None:
        if self.has_coordinates:
            return (self.latitude, self.longitude)  # type: ignore[return-value]
        return None

    def format_display(self) -> str:
        city_part = f"{self.city} ({self.postal_code})" if self.postal_code else self.city
        if self.full_address:
            return f"{self.full_address}, {city_part}"
        return city_part
