from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Final

# French typography: a narrow no-break space between thousands and before the sign, so
# « 1 210 € » never wraps and reads like the web card (Intl.NumberFormat 'fr-FR').
NARROW_NBSP: Final = "\u202f"


def format_euros(amount: Decimal) -> str:
    whole = int(amount.quantize(Decimal(1), rounding=ROUND_HALF_UP))
    return f"{whole:,}".replace(",", NARROW_NBSP) + f"{NARROW_NBSP}€"


@dataclass(frozen=True)
class Price:
    amount: Decimal
    charges: Decimal | None = None
    currency: str = "EUR"

    @property
    def total(self) -> Decimal:
        return self.amount + (self.charges or Decimal(0))

    @property
    def has_charges(self) -> bool:
        return self.charges is not None

    def format_display(self) -> str:
        """What the total is made of: « loyer 1 150 € + 60 € de charges »."""
        rent = f"loyer {format_euros(self.amount)}"
        if self.charges:
            return f"{rent} + {format_euros(self.charges)} de charges"
        return rent

    def format_total(self) -> str:
        """The monthly figure the hunter compares: « 1 210 € CC », or the rent alone.

        "CC" only when charges are known: printing it on a bare rent would claim what
        the listing never said. The reader marks that case (`Listing.charges_unknown`).
        """
        if self.charges:
            return f"{format_euros(self.total)} CC"
        return format_euros(self.amount)
