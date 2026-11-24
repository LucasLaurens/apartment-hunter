---
paths:
  - "src/apartment_hunter/infrastructure/crawlers/**"
  - "tests/infrastructure/**/*.py"
  - "docs/technical/crawlers.md"
---

## Adding a New Crawler
1. Inherit `BaseCrawler` from `infrastructure/crawlers/base_crawler.py`
2. Set `source_name`, `BASE_URL` (and `MAX_PAGES` if 4 doesn't fit); implement
   `async def fetch(filter) -> list[Listing]`
3. Reuse the base toolkit — `_gather_cities`, `_paginate`, `_fetch_html`,
   `_enrich_details`, `build_city_slug`, `parse_surface_m2`, `parse_rooms`, `parse_floor`,
   `parse_price_from_euro_node`, `is_in_department`, `parse_commune_label`,
   `parse_room_type` (« T2 », « Studio »). Do not
   re-implement them locally. A listing carries the commune **its card** names, never the
   searched one: raise `MissingCommuneError` when the card names none.
4. Add to the list returned by `build_crawlers()` in `infrastructure/container.py`
5. Write a fake in `tests/fakes/in_memory_crawler.py` — no mocking
6. Document the source in `docs/technical/crawlers.md`, `docs/functional/sources.md`
   and the README table

## Crawler Rules
- `RATE_LIMIT_SECONDS` is a budget per *window*, not a serial delay: a source is crawled
  `CITY_CONCURRENCY` communes at a time, so the spacing between two request starts is
  `RATE_LIMIT_SECONDS / CITY_CONCURRENCY` (`compute_request_spacing_seconds()`). One gate holds
  it for the whole crawler — `BaseCrawler._await_turn()`, HTML path and `_get_throttled`
  alike. Never re-derive a delay in a crawler.
- Retry 3× with exponential backoff via `tenacity`
- One honest user agent, `CRAWLER_USER_AGENT` (`base_crawler.py`): no rotation, no browser
  headers or TLS fingerprint imitated. A 401/403 is a refusal: no retry
- Log raw HTML snippet on parse errors for debugging
- robots.txt is enforced, not trusted to memory: `infrastructure/crawlers/robots.py`
  (`RobotsRules`, RFC 9309) gates `_fetch_html` and `_get_throttled`, read once a day per
  host; 4xx = no rules, 5xx/no answer = everything disallowed; `Crawl-delay` honoured.
  Wildcards need Python ≥ 3.13 (`test_robots_rules.py` fails otherwise)
- Site rules (ADR-0012): `SiteRules` (HONOURED by default, stored in `app_settings`), set in
  the web Paramètres page or `hunt rules`. `CrawlAllSources` reads it at every crawl,
  tells each crawler (`apply_site_rules`) and leaves out `forbids_reproduction` sources
  unless IGNORED; IGNORED skips the robots gate. It never touches the anti-bot line below
- No anti-bot evasion: no stealth scripts, no faked `navigator.webdriver`, no TLS
  impersonation, no CAPTCHA solving, no account. A source that only passes that way is
  removed (SeLoger 2026-10-30; Figaro, EntreParticuliers 2026-10-31). Held by
  `tests/infrastructure/test_no_evasion.py`
