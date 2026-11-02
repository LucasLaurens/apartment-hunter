"""The rent-reference port, answered by the Carte des loyers (ADR-0010).

ANIL publishes one CSV per segment and per vintage on data.gouv.fr, with no per-commune
API: each file is downloaded once, kept under `RENT_MAP_CACHE_DIR/{vintage}/`, and read
from there afterwards. The URLs below belong to one vintage; a new one (each December)
is a new dataset, updated here by hand — two vintages are never mixed or compared.
"""

import asyncio
import csv
import shutil
import time
import urllib.parse
import urllib.request
from collections.abc import Awaitable, Callable, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Final

from loguru import logger

from ..domain.entities import SearchFilter
from ..domain.ports import RentReferencePort
from ..domain.services import RentReferenceBook, is_arrondissement_code
from ..domain.value_objects import RentReference, RentSegment
from .geocoder import find_commune_codes

RENT_MAP_VINTAGE: Final = 2025
_SEGMENT_URLS: Final = {
    RentSegment.ALL_APARTMENTS: "https://www.data.gouv.fr/fr/datasets/r/55b34088-0964-415f-9df7-d87dd98a09be",
    RentSegment.ONE_TWO_ROOMS: "https://www.data.gouv.fr/fr/datasets/r/14a1fe11-b2d1-49b3-9f6b-83d12df9482c",
    RentSegment.THREE_PLUS_ROOMS: "https://www.data.gouv.fr/fr/datasets/r/5e3b28a4-cf56-43a3-ae79-43cceeb27f8c",
}
# Redirects lead to static.data.gouv.fr; anything else is refused rather than stored.
_TRUSTED_HOST_SUFFIX: Final = "data.gouv.fr"
_MAX_DOWNLOAD_BYTES: Final = 20 * 1024 * 1024  # one file is ~4.7 MB
_DOWNLOAD_TIMEOUT_SECONDS: Final = 60
_CHUNK_BYTES: Final = 64 * 1024
# After a failed download, pages go without positions for a while instead of each
# request waiting on another timeout.
_RETRY_AFTER_SECONDS: Final = 3600
# The files are Windows-1252, `;`-separated, with decimal commas.
_ENCODING: Final = "cp1252"
_DELIMITER: Final = ";"
_REQUIRED_COLUMNS: Final = frozenset(
    {"INSEE_C", "LIBGEO", "loypredm2", "lwr.IPm2", "upr.IPm2", "nbobs_com", "R2_adj"}
)

type CommuneCodeLookup = Callable[[list[str]], Awaitable[dict[str, str]]]


class RentMapError(Exception):
    """A file that could not be fetched or does not look like the Carte des loyers."""


class CarteDesLoyers(RentReferencePort):
    def __init__(self, cache_dir: Path, find_codes: CommuneCodeLookup = find_commune_codes):
        self._vintage_dir = cache_dir / str(RENT_MAP_VINTAGE)
        self._find_codes = find_codes
        # Parsed once per process: ~35 000 communes per segment, a few MB in all.
        self._tables: dict[RentSegment, dict[str, RentReference]] = {}
        # Two requests at once must not download the same file twice.
        self._lock = asyncio.Lock()
        self._failed_at = -float(_RETRY_AFTER_SECONDS)

    async def find_references(self, filters: Sequence[SearchFilter]) -> RentReferenceBook:
        codes = await self._find_codes(sorted({city for f in filters for city in f.cities}))
        if time.monotonic() - self._failed_at < _RETRY_AFTER_SECONDS:
            return RentReferenceBook.build_unavailable()
        try:
            tables = await self._load_tables()
        except (OSError, RentMapError) as exc:
            self._failed_at = time.monotonic()
            logger.warning(f"Carte des loyers unavailable, no market position: {exc}")
            return RentReferenceBook.build_unavailable()
        codes |= _find_arrondissement_codes(tables[RentSegment.ALL_APARTMENTS])
        return RentReferenceBook(
            {
                name: {seg: table[code] for seg, table in tables.items() if code in table}
                for name, code in codes.items()
            }
        )

    def delete_downloads(self) -> None:
        """Forget this vintage's files; the next position read downloads them again."""
        shutil.rmtree(self._vintage_dir, ignore_errors=True)
        self._tables.clear()

    async def _load_tables(self) -> dict[RentSegment, dict[str, RentReference]]:
        async with self._lock:
            for segment in RentSegment:
                if segment not in self._tables:
                    path = self._vintage_dir / _build_file_name(segment)
                    if not path.exists():
                        await asyncio.to_thread(_download, _SEGMENT_URLS[segment], path)
                    self._tables[segment] = await asyncio.to_thread(_read_table, path, segment)
        return self._tables


def _find_arrondissement_codes(table: dict[str, RentReference]) -> dict[str, str]:
    """{« Paris 11e Arrondissement »: "75111"}, the 45 rows standing for the three cities.

    O(r) over the ~35 000 rows; found on every call rather than cached, it stays well
    under the cost of the commune-code lookup that precedes it.
    """
    return {ref.commune: code for code, ref in table.items() if is_arrondissement_code(code)}


def _build_file_name(segment: RentSegment) -> str:
    return f"pred-{segment.value}-mef-dhup.csv"


def _download(url: str, path: Path) -> None:
    """Bounded, host-checked, written to a temporary file then renamed: a cut download
    never leaves a half file that the next start would trust."""
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(".part")
    with urllib.request.urlopen(url, timeout=_DOWNLOAD_TIMEOUT_SECONDS) as response:
        host = urllib.parse.urlparse(response.geturl()).hostname or ""
        if not host.endswith(_TRUSTED_HOST_SUFFIX):
            raise RentMapError(f"redirected to an untrusted host: {host}")
        received = 0
        with partial.open("wb") as out:
            while chunk := response.read(_CHUNK_BYTES):
                received += len(chunk)
                if received > _MAX_DOWNLOAD_BYTES:
                    partial.unlink(missing_ok=True)
                    raise RentMapError(f"{url} is larger than {_MAX_DOWNLOAD_BYTES} bytes")
                out.write(chunk)
    partial.replace(path)
    logger.info(f"Carte des loyers {RENT_MAP_VINTAGE} downloaded: {path.name}")


def _read_table(path: Path, segment: RentSegment) -> dict[str, RentReference]:
    """{INSEE code: reference}. O(r) for r rows; a malformed row is skipped, logged."""
    table: dict[str, RentReference] = {}
    with path.open(encoding=_ENCODING, newline="") as handle:
        reader = csv.DictReader(handle, delimiter=_DELIMITER)
        if not _REQUIRED_COLUMNS <= set(reader.fieldnames or ()):
            raise RentMapError(f"{path.name} lacks the Carte des loyers columns")
        for row in reader:
            try:
                table[row["INSEE_C"]] = _parse_row(row, segment)
            except (InvalidOperation, ValueError) as exc:
                logger.warning(f"Carte des loyers: skipped row {row.get('INSEE_C')}: {exc}")
    return table


def _parse_row(row: dict[str, str], segment: RentSegment) -> RentReference:
    return RentReference(
        commune=row["LIBGEO"],
        segment=segment,
        per_m2=_parse_decimal(row["loypredm2"]),
        lower_per_m2=_parse_decimal(row["lwr.IPm2"]),
        upper_per_m2=_parse_decimal(row["upr.IPm2"]),
        observed_in_commune=int(row["nbobs_com"]),
        r2_adjusted=float(_parse_decimal(row["R2_adj"])),
        vintage=RENT_MAP_VINTAGE,
    )


def _parse_decimal(raw: str) -> Decimal:
    return Decimal(raw.strip().replace(",", "."))
