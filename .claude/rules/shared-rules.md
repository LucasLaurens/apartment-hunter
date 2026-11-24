---
paths:
  - "src/**/*.py"
  - "src/**/*.js"
  - "src/**/*.css"
  - "tests/**/*.py"
---

## Shared Rules — single source of truth
- Watch policy (when to re-crawl, when to alert, what to do on failure):
  `application/use_cases/watch_filters.py` — the entry points only report. The clock is
  a port (`ClockPort`), which is what makes the policy testable without sleeping
- One crawl of one filter, then its purge: `application/use_cases/refresh_filter.py` —
  three spellings of this existed in the two presentation layers, and they had drifted
- Which communes count, and which are worth crawling: `GeocodingPort`, answered by
  `infrastructure/geocoding.py`. No use case takes a ready-made coordinate table: its
  contents used to be a per-call-site decision, so a listing could match in the CLI and
  not on the web
- JSON shape of a saved filter: `infrastructure/storage/filter_codec.py` — the encoder
  enumerates its keys by hand, and `tests/infrastructure/test_filter_codec.py` fails when
  a criterion is added to `SearchFilter` without being encoded
- Commune spelling ("Chambery", "Saint Felix", "Alby Sur Cheran" vs the INSEE name):
  `domain/services/commune_names.py` (`fold_commune_name`) — the matcher and the home key
  both fold; stored `dismissals.home_city` is folded too, rewritten by a `DATA_MIGRATIONS`
  entry that calls it as a SQL function. Never compare raw city names
- Duplicate grouping (one home, several publications): `domain/services/duplicates.py`
  (`build_home_key`, `group_duplicates`, `ListingGroup`) — display only, applied before pagination so the
  counts are homes; never drops a listing, and never merges two ads from one source
- Dismissed homes (the hunter's « écarté »): `domain/services/dismissals.py`
  (`DismissedHomes`, `build_dismissal`) — a listing is hidden when it would group with a
  dismissed one (same URL, or same `HomeKey` on another source). `GetTopListings`,
  `NotifyNewListings` and `hunt review` all ask it; the `dismissals` table has no FK to
  `listings` so the purge never erases a dismissal (ADR-0009). Restoring sets
  `restored_at` (a trace, no longer in force, shown as « restauré le … » via
  `RestoredHomes`) — `RestoreHome`, also the web undo. A rent
  change breaks the recognition, same URL included; the home comes back carrying
  `former_dismissal`, found by `HomeKey.layout` (no rent) — display only, never hides.
  The mention is `Dismissal.format_mention`, the reason's wording `DismissalReason.label`
  (`REASON_KEYS` derives from it)
- Criterion suggestions (3rd dismissal in force for one reason and value → the most prudent
  filter change, never applied unasked): `domain/services/criterion_suggestions.py`
  (`build_criterion_suggestion`, `SUGGESTION_THRESHOLD`), orchestrated by
  `application/use_cases/suggest_criteria.py` (impact count, apply, refuse). Refusals sit in
  `criterion_refusals`, no FK to `listings`, dropped with their filter
- Opened homes (what turns *Nouvelle* off): `domain/services/openings.py` (`OpenedHomes`,
  `build_opening`), on the same `RecognisedHomes` index as dismissals — one meaning of
  « the same home » for both judgements. The `openings` table survives the purge;
  `listings.opened_at` is read by nothing since its one-time migration. `OpenHome` is
  the only writer, for the review's `o` and the web route alike
- Dismissal reasons as typed and read (keys 1–8, 0): `presentation/dismissal_reasons.py`
  (`REASON_KEYS`) — `hunt review` and the web reason bar share it, the web reads it
  from `/api/dismissal-reasons`
- Network brand behind a branch name: `domain/services/advertiser.py` (`NETWORK_NAMES`,
  `find_network`) — one home shared with the agency-source list
- Thermal-sieve wording and the letting-ban calendar: `domain/services/energy_regulation.py`
  (`RENTAL_BAN_DATES`, `is_thermal_sieve`, `build_rental_ban_warning`) — the date is a
  parameter, never a clock read; warn on F/G, never exclude
- Expired listings and unreachable sources: `domain/services/expiry.py` (`SourceFreshness`,
  `compute_stale_after`, `build_source_down_warning`), fed by `filter_source_successes`
  (written by `RefreshFilter`) and `listings.last_seen_at`. Time is counted in the filter's
  crawls, never the wall clock; display-only, the purge stays the delisting one
- Where a listing sits (its own coordinates, else its commune's): `ListingMatcher.find_position`
  — the radius check and the map (`application/use_cases/map_filter_homes.py`) both ask it.
  The map library is pinned with SRI and loaded only when a map opens (`MAP_LIBRARY` in
  `app.js`, held by `test_web_asset_guards.py`); popups are DOM + `textContent`, never HTML
- Who publishes (particulier / agence / inconnu): `domain/services/advertiser.py` —
  its source lists are held to the crawler list by
  `tests/infrastructure/test_advertiser_source_parity.py`
- Out-of-scope tenancies (room in a shared flat, mobility lease, holiday let):
  `domain/services/tenancy_scope.py`, applied unconditionally by `ListingMatcher` —
  not a filter option; stay conservative, a missed listing costs more than a room to skip
- Money as the hunter reads it (« 1 210 € CC », narrow no-break spaces, « CC » only when
  charges are known): `domain/value_objects/price.py` (`format_euros`, `format_total`,
  `format_display`) — CLI, review, alerts; the web card formats the same way in `app.js`
- Unsettled monthly total: `Listing.charges_unknown` — web card, CLI table and
  `build_summary_line()` must all carry the mark, or the trap comes back
- Furnished detection: `domain/services/furnishing.py` — `detect_furnished` (card text, keyword),
  `detect_furnished_label` (whole detail page, "Meublé : non" label only: the bare word sits in
  every site's own nav) and `detect_furnished_chip` (criteria chips whose *whole* text is the word,
  for sites that label nothing — Laforêt prints a bare "Meublé" chip). The detail page's answer
  overrides the card's.
- Card ↔ detail-page merge (DPE, GES, storey, furnished, date): `base_crawler.py`
  (`merge_details`) — a crawler driving its own enrichment loop must fold fields the same way
- Storey parsing (label *and* prose, all sources): `infrastructure/crawlers/base_crawler.py`
  (`parse_floor`) — never re-derive « étage » per crawler
- Detail-page values landing on rows already stored (DPE, GES, storey, furnished):
  `sqlite_repository.py` (`_backfill_detail_fields`); the rent follows the source on every
  re-crawl, and so do the commune and title (`_update_price_and_place`) — `INSERT OR IGNORE` alone would
  freeze the first, blank reading forever
- Scraped-text and scraped-link hardening: `domain/services/sanitising.py`; a listing whose rent
  reads 0 € is a failed parse and is never stored (`SqliteRepository._keep_storable`, W5)
- Filter bounds: `domain/entities/search_filter.py` (`MIN_*`/`MAX_*` + `__post_init__`)
- Market position (ADR-0010): `domain/services/rent_reference_book.py` (`RentReferenceBook`,
  `assess` in the fixed order meublé → charges inconnues → sans surface → commune absente)
  over `domain/value_objects/market_position.py`; references come through
  `RentReferencePort`, answered by `infrastructure/rent_map.py` (Carte des loyers CSV,
  cached per vintage) with INSEE codes from `geocoder.find_commune_codes`. Paris, Lyon and
  Marseille have no city row, only arrondissements: `domain/services/arrondissements.py`
  (`build_arrondissement_name`, from the postal code or the city label). Never a median of
  our own listings, never a wider area; every surface showing a position carries
  `RENT_MAP_CREDIT`
- Source pills and the source pick: `GetTopListings.execute_paginated` (`source_counts`,
  `source=`) over the whole filter, before the page is cut. `app.js` never counts or
  filters a page itself: per-page counts lied (W8)
- Display order + parution-date normalisation: `domain/services/listing_order.py`
  (`sort_listings`, `build_published_key`) — mirrored in SQL by `_ORDER_BY` in
  `sqlite_repository.py`, kept honest by `tests/infrastructure/test_sqlite_sort_parity.py`
- Filter defaults: `domain/entities/search_filter.py` (`DEFAULT_*`)
- Web form → `SearchFilter`: `presentation/web/filter_payload.py` (create *and* edit). `_read_form`
  is the only list of what the form edits; an edit applies it onto the stored filter
  (`apply_payload`), so criteria the form never shows survive — rebuilding erased them (W4).
  `tests/presentation/test_filter_edit.py` fails when the server reads a criterion that
  `filterPayload()` in `app.js` never sends (that is how `max_rooms` was being blanked)
- A filter bound refused names its field (`FilterBoundError.field_name`); the web turns it into
  a French sentence under that field (`format_filter_error`, `FIELD_BY_CRITERION` in `app.js`)
- CLI ad-hoc flags → `SearchFilter`: `presentation/cli/adhoc.py`
- Yes/no/indifferent answers: `presentation/tri_state.py` (`parse_tri_state`)
- Verb-first function names: enforced by `tests/test_function_naming.py` — its `_VERBS`
  set is the list of actions the codebase speaks; a nominal name fails the suite
- Theme (Clair / Sombre / Système): every colour in `styles.css` is `light-dark(light, dark)`,
  `color-scheme` on `:root` picks; the choice is applied by the `<head>` script of
  `index.html` (`THEME_STORAGE_KEY`). Held by `tests/presentation/test_theme_tokens.py`
  and `make ui-check` (AA in each theme) — ADR-0011
- Colour budget (hue for state only: new, danger, warn, DPE/GES; no source hue, no card
  motion): `DESIGN.md` § Color, held by `tests/presentation/test_colour_budget.py`
- Web page assets: `presentation/web/assets/` (never inline HTML/CSS/JS in Python)
