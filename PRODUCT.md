# Product

## Register

product

## Users

A single operator hunting a rental flat in the Annecy area. Checks the app many
times a day, in short bursts, between other tasks, on a laptop in daylight.
The job: spot the two or three genuinely new listings among 25 per page, and
reject the rest in under a second, using price, surface, rooms, DPE and city.

The physical scene that shaped the light theme: *a laptop screen at 14h next to a
window, in a bright room, glanced at for fifteen seconds at a time.* Daylight
ambient, short exposures, comparison work on numbers. The same hunter also checks
in the evening, on a device set to dark: the theme is theirs to choose (ADR-0011).

## Product Purpose

Aggregate rental listings from a dozen French agency sites, filter them against
saved criteria (cities, radius, price, surface, rooms, floor, DPE), and surface
what is new since the last look. Success is a listing found here before it is
found by scrolling the source portals, and a rejected listing never looked at
twice.

## Brand Personality

Quiet, factual, fast. The tool states what it found and gets out of the way.
No enthusiasm, no persuasion, no marketing voice: it is a private instrument,
not a product being sold. French UI, sentence case, numbers over adjectives.

## Anti-references

- The source portals themselves (SeLoger, Logic-Immo): ad-stuffed, carousel-led,
  every listing shouting equally loud.
- Luxury real-estate aesthetics: serif display faces, gold accents, hero
  photography, "prestige" vocabulary. This is a search tool, not a brochure.
- Generic SaaS dashboard: gradient hero metric, purple-to-blue accents, card
  grid of identical tiles, onboarding tour.
- Emoji standing in for icons. They render differently on every platform and
  carry no accessible name.

## Design Principles

1. **The data is the interface.** Price, surface, DPE and city must be readable
   without hovering, expanding, or clicking. Chrome shrinks; content does not.
2. **New is the only status that earns colour.** Everything else is neutral.
   An accent used on decoration cannot mark a new listing. Actions rank as
   primary, secondary and tertiary on one hue: fill, outline, text.
3. **The hunter chooses the theme, the colours are written once.** Clair, Sombre
   or Système on the Paramètres page. Every colour carries its light and dark
   value in one declaration: no second set of tokens to keep in sync (ADR-0011).
4. **Rejection speed over completeness.** Scanning is the primary act. Density
   serves it; a comfortable layout that halves listings-per-screen does not.
5. **Every state is designed.** Loading, empty, error, crawling, no-results-
   for-this-source. A blank panel is a bug.

## Accessibility & Inclusion

- WCAG 2.1 AA in every theme. Body and muted text at 4.5:1 minimum against their
  own surface, UI borders and icons at 3:1.
- Full keyboard operation: every filter, source toggle, page and modal control
  reachable by Tab with a visible focus ring. No hover-only affordance.
- DPE and GES are conveyed by letter *and* colour, never colour alone: the
  regulatory palette runs green to red and is unreadable to red-green colour
  blindness on its own.
- `prefers-reduced-motion` removes the spinner spin and the skeleton shimmer.
  Cards carry no motion at all.
- Icons are SVG with an accessible name on every icon-only control.
