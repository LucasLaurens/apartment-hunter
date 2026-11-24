---
paths:
  - "src/**/*.py"
  - "src/**/*.js"
  - "src/**/*.html"
---

## Security
- All config via env vars or `.env` — never commit credentials (`.env.example` is the template)
- No eval/exec on scraped data
- Scraped data is sanitised at the storage boundary: `clean_text` (null bytes, length) and
  `is_web_url` (only http(s) links are stored) — `domain/services/sanitising.py`
- Web UI: `escHtml` for text/attributes, `safeUrl` before any `href`, and a scraped value
  never lands in inline JS (`data-*` + `wireSourceButtons()`) — an HTML entity is decoded
  before an `onclick` body is compiled, so escaping can't protect that context
- `SearchFilter` refuses intervals < 5 min, radius outside 1–150 km, absurd result caps,
  more than `MAX_CITIES`, a freshness window over `MAX_AGE_DAYS`, and any non-finite number:
  a past deadline makes the watch loop re-crawl every source every tick
- Web server: only its own page may talk to it — `TrustedHostMiddleware` (DNS rebinding) and
  `reject_cross_site_writes` (`presentation/web/request_guard.py`) on every write
- Nominatim is paced at one request a second (geopy `RateLimiter`, `geocoder.py`)
- Rate limiting is both courtesy AND self-protection
