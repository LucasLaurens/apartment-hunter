---
paths:
  - "tests/**/*.py"
---

## Testing Rules
- Fakes live in `tests/fakes/` — concrete implementations, no mocking
- AAA structure always: `# Arrange / # Act / # Assert`
- Faker for all test data (`fake()` in Python → `Faker()` from faker lib)
- No real HTTP calls in tests — use `InMemoryCrawler`
