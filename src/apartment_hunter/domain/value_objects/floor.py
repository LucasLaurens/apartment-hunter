from dataclasses import dataclass

GROUND_FLOOR_LEVEL = 0
UNKNOWN_FLOOR_LEVEL = -1


@dataclass(frozen=True)
class Floor:
    level: int
    is_top: bool = False

    @property
    def is_ground(self) -> bool:
        return self.level == GROUND_FLOOR_LEVEL

    @property
    def is_first(self) -> bool:
        return self.level == 1

    @property
    def is_known(self) -> bool:
        return self.level != UNKNOWN_FLOOR_LEVEL

    def format_label(self) -> str:
        if not self.is_known:
            return "Étage inconnu"
        if self.is_ground:
            return "Rez-de-chaussée"
        suffix = "er" if self.level == 1 else "e"  # French ordinal: 1er, 2e — never "2ème"
        top = " (dernier)" if self.is_top else ""
        return f"{self.level}{suffix} étage{top}"

    @classmethod
    def unknown(cls) -> "Floor":
        return cls(level=UNKNOWN_FLOOR_LEVEL)

    @classmethod
    def ground(cls) -> "Floor":
        return cls(level=GROUND_FLOOR_LEVEL)

    @classmethod
    def from_int(cls, level: int, is_top: bool = False) -> "Floor":
        return cls(level=level, is_top=is_top)
