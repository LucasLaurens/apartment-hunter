# Design

Visual system for the Apartment Hunter web interface. The implementation lives in
`src/apartment_hunter/presentation/web/assets/` (`index.html`, `styles.css`,
`app.js`), inlined into one document by `web/ui.py`.

## Theme

**Clair, Sombre or Système, one list of colours** ([ADR-0011](docs/decisions/0011-le-theme-est-un-choix-du-chasseur.md)).
Every colour is declared once as `light-dark(light, dark)`; `color-scheme` on
`:root` picks the half (`data-theme="light"` → `light`, `"dark"` → `dark`,
`"system"` → `light dark`, which follows the OS). There is no
`prefers-color-scheme` branch and no second token block: a second theme is not a
second copy of every colour decision. Native controls follow `color-scheme`.

The choice is made on the Paramètres page (sidebar footer), kept in
`localStorage` under `ah-theme`, default Système, and applied by a `<head>` script
before the first paint. `tests/presentation/test_theme_tokens.py` fails on a colour
written without its dark value.

Light was designed for daylight, fifteen-second glances and number comparison;
dark keeps the same hue (155), the same colour budget and the same contrast floor.

## Color

Strategy: **Restrained.** Tinted neutrals carry the surface; the accent appears
on primary actions, current selection, focus and the "new listing" mark, and
nowhere else. Every neutral is tinted toward the accent hue (155) at chroma
0.004–0.020 so surfaces and brand cohere without reading as green: enough
for the sidebar to feel green-white, under the 0.02 line where a tint becomes a hue.

**The colour budget** (ticket 04). Hue is spent on state, never on decoration:
the accent for *new*, selection and the one primary action; danger for a
destructive action; warn for « charges ? » and the F/G letting ban; the DPE/GES
scale because it is regulatory. A source, a market position (« −12 % vs réf. »,
« sous la réf. » in weight 600), a dismissed home and « chauffage collectif » are
neutral text. `tests/presentation/test_colour_budget.py` fails on any other hue, on
a `--src-h` coming back, and on a card that animates.

All colours are authored in OKLCH.

### Neutrals and surfaces

| Token | Light | Dark | Use |
|---|---|---|---|
| `--canvas` | `oklch(97.2% 0.008 155)` | `oklch(17% 0.012 155)` | Content area, recessed |
| `--surface` | `oklch(99.5% 0.004 155)` | `oklch(21.5% 0.013 155)` | Cards, modal, raised |
| `--chrome` | `oklch(98.8% 0.012 155)` | `oklch(19.5% 0.014 155)` | Header, sidebar |
| `--sunken` | `oklch(95.4% 0.010 155)` | `oklch(25% 0.013 155)` | Inputs, counters |
| `--border` | `oklch(90% 0.014 155)` | `oklch(30% 0.015 155)` | Card and section separators |
| `--border-strong` | `oklch(83.5% 0.017 155)` | `oklch(38% 0.017 155)` | Hover borders, dividers under load |
| `--border-field` | `oklch(62% 0.018 155)` | `oklch(56% 0.018 155)` | Form control boundary (≈3.5:1) |
| `--text` | `oklch(25% 0.020 155)` | `oklch(93% 0.010 155)` | Body, headings, prices (15.6:1) |
| `--text-muted` | `oklch(46% 0.018 155)` | `oklch(73% 0.016 155)` | Labels, meta, hints (7:1) |

Never `#fff` or `#000`. The lightest surface stops at 99.5%.

### Accent and semantics

| Token | Light | Dark | Use |
|---|---|---|---|
| `--accent` | `oklch(50% 0.120 157)` | `oklch(78% 0.15 157)` | Primary button fill, links, selection (5.5:1) |
| `--accent-hover` | `oklch(43% 0.105 157)` | `oklch(84% 0.14 157)` | Pressed and hovered primary |
| `--accent-soft` | `oklch(94% 0.060 157)` | `oklch(28% 0.06 157)` | Selected filter row |
| `--accent-soft-hover` | `oklch(91% 0.085 157)` | `oklch(32% 0.075 157)` | Hovered watch-on button |
| `--accent-border` | `oklch(84% 0.120 157)` | `oklch(44% 0.1 157)` | Border of any accent-soft surface |
| `--accent-ring` | `oklch(58% 0.130 157)` | `oklch(72% 0.15 157)` | Focus ring, 2px offset |
| `--danger` | `oklch(52% 0.190 27)` | `oklch(72% 0.17 27)` | Delete action, required marker |
| `--danger-soft` | `oklch(94.5% 0.035 27)` | `oklch(28% 0.08 27)` | Invalid field fill, destructive hover |
| `--warn` | `oklch(51% 0.110 70)` | `oklch(82% 0.15 75)` | « charges ? », letting-ban notice |
| `--warn-soft` / `--warn-border` | `oklch(95% 0.06 75)` / `oklch(85% 0.11 75)` | `oklch(28% 0.06 70)` / `oklch(44% 0.09 70)` | Its fill and border |
| `--shimmer` | `oklch(99.5% 0.002 155 / 0.9)` | `oklch(32% 0.006 155 / 0.6)` | Skeleton sweep |
| `--overlay` | `oklch(26% 0.02 155 / 0.32)` | `oklch(5% 0.01 155 / 0.6)` | Modal scrim |

No colour literal appears outside this `:root` block. The one exception is the
DPE/GES formula below, which consumes `--dpe-h` rather than hardcoding a colour.

Forest green, not the reflex SaaS indigo. State colours sit at the edge of the
sRGB gamut for their lightness (green 0.12 at 50%), so they read lively rather than
muted; the budget, not a low chroma, keeps them from competing with the DPE scale.
Past that edge the browser clips, so pushing chroma further buys nothing.

### DPE / GES scale

Regulatory green-to-red progression, restated as light tinted chips with dark
same-hue letters: background `oklch(88% 0.13 H)`, text `oklch(32% 0.1 H)`,
hues A 148 · B 135 · C 110 · D 95 · E 70 · F 45 · G 25. Every chip clears 6:1,
where the saturated official fills with white text sat between 3 and 4:1. Dark
keeps the label's reading, a bright chip with a dark letter: `oklch(80% 0.15 H)`
fill, `oklch(20% 0.07 H)` text, above 6:1 as measured by `make ui-check`.

The letter is always rendered, so the rating never depends on colour alone.
Missing rating renders a neutral `?` chip, never an absent one: the same mark as
« charges ? », and no em-dash in the page text.

### Source pills

No hue per portal: a brand colour would be the first thing seen on the page, ahead
of *new*. The pills above the cards are neutral and their state reads from the
shape: pressed = `--sunken` fill, `--border-strong` border, `--text`; released =
outline, `--text-muted`; the chosen source carries a check. 11px, 28px tall. The
card names its source in grey text in its last line.

A pill's count is the number of homes that source carries over the whole filter,
computed by the server, never the page on screen. Picking a source asks the server
again: the list, its pages and its total are then that source's, so a page can never
say « aucun logement » while another page holds some.

## Typography

One family: `-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui,
sans-serif`. No display face, no web font request. Product register: labels,
buttons, data.

Fixed rem-free px scale, ratio ≈1.15–1.25: 11 (micro) · 12 (meta) · 13 (UI
default) · 14 (card facts, body) · 20 (price) · 26 (modal-scale). Weights 400 /
500 / 600 / 700.

`font-variant-numeric: tabular-nums` on prices, surfaces, counts and page
numbers so digits align down a scanned column.

## Spacing & layout

Dense scale: 4 · 6 · 8 · 12 · 16 · 20 · 24 · 32. Header 56px, sidebar 264px.
Radius: 6 (controls) · 10 (cards, modal) · 999 (chips). Elevation is one soft
shadow at `oklch(26% 0.02 155 / 0.06)`; cards separate by border, not shadow.

The cards pack as a masonry: each takes the end of the shortest column, in sort order,
so a short card leaves no hole under it and the reading order stays the sort order.
Placement only, never motion: a resize re-packs without a transition. Without the
script, the plain grid. Held by `test_the_card_masonry_keeps_the_reading_order`.

Structural responsive behaviour, not fluid type: below 900px the sidebar becomes
a horizontal filter strip above the results and the layout scrolls as one column.

## Motion

150–200ms, `cubic-bezier(0.16, 1, 0.3, 1)` (ease-out-expo family). Motion marks
state only: skeleton shimmer while loading, toast entry, modal entry. A card does
not move or pulse: "new" is the badge and the accent border, nothing else. No
page-load choreography. `prefers-reduced-motion: reduce` disables shimmer and
spin, and keeps the state change instant.

## Components

Every interactive element ships default / hover / focus-visible / active /
disabled. Focus is a 2px `--accent-ring` outline with 2px offset, never removed.

- **Icons**: inline SVG from a `<symbol>` sprite in `index.html`, 1.5px stroke,
  `currentColor`. No emoji: they render per-platform and carry no name.
- **Icon-only controls**: `aria-label` required, 28px minimum hit box.
- **Loading**: skeleton cards matching the real card geometry, not a centred
  spinner over an empty panel.
- **Empty states**: name what is missing and offer the action that fixes it.
- **Freshness and search states (ticket 15)**: the toolbar says « Dernière recherche : il y
  a 12 min », the latest answer a source gave this filter, never the browser's clock;
  « Pas encore de recherche » before the first one. While a search runs, one neutral tag
  per source sits under the toolbar (« pap : 12 annonces », « orpi : en cours »,
  « paruvendu : échec », the failure in weight 600) and goes when the search ends. An
  action the server refused says so with the alert icon, never the success check.
- **Forms**: visible `<label for>` on every control, error text under the field
  it belongs to, `aria-invalid` and `aria-describedby` wired. A bound the server refuses
  comes back as `{field, message}` (`FilterBoundError` → `format_filter_error`) and is
  shown under that field, in French, saying how to fix it (ticket 16). Placeholders are
  examples ending in « … » (« ex. 1 200… »), never a value-looking number. The filter
  modal keeps its secondary criteria in a « Plus de critères » fold that opens by itself
  when the filter uses one of them.
- **Modal**: `role="dialog"` `aria-modal`, focus moved in and restored out,
  Escape closes, Tab cycles inside.
- **Action hierarchy**, one hue: *primary* is the filled accent button, one per
  view (Rechercher, Enregistrer); *secondary* is the outlined `.btn` (Surveiller,
  Nouveau filtre, Annuler, Retour aux résultats); *tertiary* is text or icon only
  (`.nav-link` Paramètres, `.btn-icon`). A second filled button above the fold
  competes with the first (W17).
- **Map (ticket 14)**: a « Liste / Carte » switch in the results toolbar; the map is
  fitted to the filter's whole circle (never a fixed zoom that crops it), drawn in neutral
  ink, with one pin per commune carrying its number of homes (pins are `--text` on
  `--canvas`: a count, not a status) and the commune's name under it, as a map text
  layer so colliding names give way and come back on zoom. A pin opens the commune's
  homes, its distance from the centre, and per home a link with its « Nouveau » mark and
  the card's « Écarter »; it does not narrow the list. One popup at a time; its close is a
  32px button in the title row; Escape closes the popup before the dialog or the reason
  bar behind it. The filter modal carries a compact map (360px): the circle follows the
  radius as it is typed and stays fitted; a tap on a commune names it first (name,
  distance, « Exclure / Réinclure cette commune »), never excludes on the first touch.
  An excluded commune is a hollow ring struck through (shape, not hue). Basemap
  OpenFreeMap (positron / dark, by theme) and its attribution box follow the theme,
  credited under the map.
- **Dismissal (ticket 05)**: a tertiary « × Écarter » on each card, above the stretched
  link, opens one reason bar fixed at the bottom of the page (never inside the card):
  the closed list of reasons with `hunt review`'s keys, « autre » adding a labelled text
  field. Keyboard: `j`/`k` move the focus between cards, `x` opens the bar, the reason's
  key dismisses, `Échap` cancels. The page reloads from the server (duplicates go with
  the home) and the toast offers « Annuler » for 6 s. « Écartés » in the sidebar lists
  what is in force, each with « Restaurer ».
- **Listing card**: one decision line per home, in the order the dismissal
  reasons judge it. Top: « Nouveau » badge, total `1 210 € CC` (thousands
  separated, never `CC` then `HC`), commune on the right. Then size · storey · DPE ·
  GES; then what the total is made of (`loyer 1 150 € + 60 € de charges`, or
  « loyer seul, charges ? » in `--warn`) and who publishes; then notes (meublé,
  chauffage collectif, letting ban, unreachable source); then the title; then
  source · date · photos · duplicates, each duplicate with its own link. The
  title link is stretched over the whole card, so the hover keeps its promise.
  The market position (ADR-0010) sits right under the total line (« −12 % vs réf. »,
  or « pas de repère (raison) »), in `--text`, 12px: weight (600) marks « hors
  fourchette », never a hue. The reference it was measured against is read out to a
  screen reader and shown on hover. Under the cards, one muted line names the source
  (Carte des loyers, ANIL): the licence asks for it wherever a position shows.
- **Pagination**: windowed (first · … · current ±2 · … · last), never one button
  per page. A page past the last (an old link) serves the last one.
- **Address bar**: filter, page, order, source and view live in the URL
  (`?filtre=…&page=2&tri=…&source=…&vue=carte`; defaults are left out), so a reload
  or a shared link reopens the same list. Another filter is a history step that Back
  returns from; a page, an order, a source or a view only rewrite the current entry.
- **Tab and heading**: the tab reads « Annecy centre · 25 logements »; a visually
  hidden `h1` names the filter. Side pages title the tab with their own `h1`.
- **Narrow screens** (≤ 560px): the count takes its own row, the order and the view
  switch share the next; « · page 2 sur 3 » never breaks away from the count.
