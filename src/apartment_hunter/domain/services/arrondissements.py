"""The arrondissement a home in Paris, Lyon or Marseille sits in.

The Carte des loyers has no row for these three communes as a whole, only one per
arrondissement (« Paris 11e Arrondissement »). A home there is assessed against the
arrondissement its postal code, or its city label, names; without either it has none.
"""

import re
from typing import Final

from .commune_names import fold_commune_name

# Folded commune → (name the Carte des loyers prints, postal prefix, arrondissement count).
_CITIES_WITH_ARRONDISSEMENTS: Final = {
    "paris": ("Paris", "75", 20),
    "lyon": ("Lyon", "69", 9),
    "marseille": ("Marseille", "13", 16),
}
# INSEE codes of the arrondissements themselves: 75101-75120, 69381-69389, 13201-13216.
ARRONDISSEMENT_CODE_PREFIXES: Final = ("751", "6938", "132")
# Paris's 16e has a second postal code, 75116, on top of 75016.
_PARIS_16E_NORTH: Final = "75116"
# « Paris 11e », « Lyon 3ème », « Marseille 1er Arrondissement », « Paris 11 ».
_LABEL_RE: Final = re.compile(r"^(paris|lyon|marseille) (\d{1,2})(?: ?(?:er|e|eme))?\b")


def build_arrondissement_name(city: str, postal_code: str | None) -> str:
    """« Paris 11e Arrondissement » for Paris + 75011 or for « Paris 11e »; "" otherwise.

    The postal code is read only when the city is exactly one of the three communes:
    « Marseille-en-Beauvaisis » (Oise) has no arrondissement.
    """
    folded = fold_commune_name(city)
    if label := _LABEL_RE.match(folded):
        return _format_name(label.group(1), int(label.group(2)))
    if folded in _CITIES_WITH_ARRONDISSEMENTS and postal_code:
        return _format_name(folded, _parse_postal_number(folded, postal_code.strip()))
    return ""


def is_arrondissement_code(insee_code: str) -> bool:
    return insee_code.startswith(ARRONDISSEMENT_CODE_PREFIXES)


def _parse_postal_number(folded_city: str, postal_code: str) -> int:
    """0 when the postal code is not one of the city's own."""
    if postal_code == _PARIS_16E_NORTH and folded_city == "paris":
        return 16
    _, prefix, _ = _CITIES_WITH_ARRONDISSEMENTS[folded_city]
    if len(postal_code) != 5 or not postal_code.startswith(prefix + "0"):
        return 0
    return int(postal_code[2:])


def _format_name(folded_city: str, number: int) -> str:
    name, _, count = _CITIES_WITH_ARRONDISSEMENTS[folded_city]
    if not 1 <= number <= count:
        return ""
    return f"{name} {number}{'er' if number == 1 else 'e'} Arrondissement"
