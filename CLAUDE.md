# Apartment Hunter — Claude Code Project Rules

## Architecture (Clean Architecture)
```
domain/       → pure Python, zero framework deps, zero IO
application/  → use cases, orchestration, no infra imports
infrastructure/ → crawlers, sqlite, notifications, cache
presentation/ → CLI (Typer + Rich) + web (FastAPI)
```

**Dependency rule**: outer layers import inner; inner NEVER import outer.
`infrastructure` may import `domain` and `application`.
`domain` imports nothing from this project.

## Best Practices & Documentation (mandatory)
Every change follows the project's coding rules **and** ships its doc update in the
same commit. Full rationale: `docs/technical/conventions.md`.

1. **Reuse before writing** — search for an existing helper/constant first
   (`base_crawler.py` toolkit, `domain/services/`, `domain/entities/search_filter.py`
   defaults, `presentation/tri_state.py`). A second copy of a rule is a bug in waiting.
2. **Put it in the right layer** — business rule → `domain/`, orchestration →
   `application/`, IO → `infrastructure/`, input/output translation → `presentation/`.
   Never import outward.
3. **SOLID / Law of Demeter** — one responsibility per module, ports over concrete
   classes, ask the object instead of chaining through it.
4. **Clean Code** — no magic value (named constant or backed enum), no dead
   parameter, comments explain *why*, immutable by default, avoid nullable.
5. **A function is an action — name it with a verb** — `find_top`, `build_city_slug`,
   `parse_floor`, `read_tag_attr`, `format_published_label`, `detect_furnished`. Pick
   the verb that is true: `find…`/`list…` queries a store, `compute…`/`build…`/`format…`
   derives, `read…`/`resolve…` resolves an indirection, `parse…`/`detect…` reads scraped
   text, `save…`/`delete…`/`apply…` changes state. `get…` is for a plain accessor over a
   loaded field only (`get_settings`), never in front of a query. Exempt: `@property`,
   named constructors (`Floor.from_int`), conversions (`listing_to_dict`,
   `filter_from_json`, `with_site_date`), framework hooks (`lifespan`, `on_response`),
   pytest fixtures. Rename the noun-named functions in the files a change already opens,
   call sites included — but never rename a JSON key (`display_total`,
   `rental_ban_warning`, `advertiser_kind`) or a SQLite column (`listing_id`): those are
   contracts with `app.js` and the database. Full rule:
   `docs/technical/conventions.md` § Nommage.
6. **Complexity** — reason in Big O before writing; `set`/`dict` for membership,
   memoize repeated normalisation, annotate when non-obvious, name the bounds
   (`MAX_PAGES`, `*_CONCURRENCY`, timeouts).
7. **Tests** — concrete fakes only (no mocks), `# Arrange / # Act / # Assert`, Faker
   for data.
8. **Update the docs in the same change** — see the table below. A doc code sample
   must match the real signature.
9. **Run `make full` before committing** (ruff check + format + mypy strict + pytest).

| Change | Doc to update |
|--------|---------------|
| Layer, module, moved file | `docs/technical/architecture.md` (incl. the file tree) |
| Crawler, shared base, anti-bot | `docs/technical/crawlers.md` |
| Entity, field, migration | `docs/technical/data-model.md` |
| Watch mode, intervals, concurrency | `docs/technical/scheduler.md` |
| CLI command, source, env var | `README.md` |
| Coding convention, a function name | `docs/technical/conventions.md` |
| Business term, its definition, a naming choice | `docs/functional/glossaire.md` |
| A business arbitration that closes off options | a new ADR in `docs/decisions/` |

## Domain Rules
- `Listing` is frozen dataclass (immutable)
- `SearchFilter` is mutable dataclass (user configures it)
- All money as `Decimal`, never `float`
- DPE ordering: A < B < C < D < E < F < G (best → worst)
- `Floor.level=0` = rez-de-chaussée, `is_top=True` = dernier étage

## CLI Commands
```
hunt search              # one-shot: crawl + display top 10
hunt watch               # polling mode with notifications
hunt review              # terminal review, by market position: j/k or ↑/↓, o open, x dismiss, u undo, s sort, d dismissed
hunt review --dismissed  # dismissed homes, u restores one, d back to the review
hunt filter add          # interactive filter wizard
hunt filter list         # list saved filters
hunt filter show <id>    # show filter details
hunt filter delete <id>  # delete filter
hunt clean               # drop listings no filter wants + unseen 7 days (--unseen-days N, --cache, -y)
hunt rules               # site rules: show; `hunt rules ignore` / `hunt rules honour` (ADR-0012)
```

## Env Vars (see .env.example)
`DATABASE_URL`, `GEOCODING_USER_AGENT`, `LOG_LEVEL`, `RENT_MAP_CACHE_DIR`


## Rules loaded on demand

Loaded only when a matching file is read or edited (`.claude/rules/`):

- `crawlers.md`: adding a crawler, crawler rules (rate limit, robots, site rules, no evasion) (`src/apartment_hunter/infrastructure/crawlers/**`, `tests/infrastructure/**/*.py`, `docs/technical/crawlers.md`)
- `shared-rules.md`: single source of truth for each business rule (`src/**/*.py`, `src/**/*.js`, `src/**/*.css`, `tests/**/*.py`)
- `testing.md`: fakes, AAA, Faker, no real HTTP (`tests/**/*.py`)
- `performance-complexity.md`: caching, concurrency, Big O (`src/**/*.py`, `tests/**/*.py`)
- `security.md`: config, sanitising, web UI escaping, filter bounds (`src/**/*.py`, `src/**/*.js`, `src/**/*.html`)
