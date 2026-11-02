"""
Map raw energy/emission figures to French DPE & GES letter classes.

Listings advertise two numbers — primary-energy consumption (kWh/m².an) and
greenhouse-gas emissions (kg CO₂/m².an). The official thresholds (in force since
the 2021 DPE reform) convert each to an A–G letter. The final DPE letter is the
*worse* of the energy and emission classes, which is exactly the letter sites
print on their cards.

Reuses DpeRating as the shared A–G value object for both metrics.
"""

from .dpe_rating import DpeRating

# Upper bound (inclusive) of each class → letter. Above the last bound ⇒ G.
_ENERGY_BOUNDS: list[tuple[float, DpeRating]] = [
    (70, DpeRating.A),
    (110, DpeRating.B),
    (180, DpeRating.C),
    (250, DpeRating.D),
    (330, DpeRating.E),
    (420, DpeRating.F),
]
_GES_BOUNDS: list[tuple[float, DpeRating]] = [
    (6, DpeRating.A),
    (11, DpeRating.B),
    (30, DpeRating.C),
    (50, DpeRating.D),
    (70, DpeRating.E),
    (100, DpeRating.F),
]


def _classify(value: float, bounds: list[tuple[float, DpeRating]]) -> DpeRating:
    for upper, rating in bounds:
        if value <= upper:
            return rating
    return DpeRating.G


def classify_energy(consumption_kwh: float) -> DpeRating:
    """A–G class from primary-energy consumption (kWh/m².an)."""
    return _classify(consumption_kwh, _ENERGY_BOUNDS)


def classify_ges(emission_co2: float) -> DpeRating:
    """A–G class from greenhouse-gas emissions (kg CO₂/m².an)."""
    return _classify(emission_co2, _GES_BOUNDS)


def classify_dpe(consumption_kwh: float, emission_co2: float) -> DpeRating:
    """Final DPE letter = the worse of the energy and emission classes."""
    return max(classify_energy(consumption_kwh), classify_ges(emission_co2))
