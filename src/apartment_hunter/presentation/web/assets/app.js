// ── Named values ──────────────────────────────────────────────────────────────
// Nothing below this block repeats a literal: an endpoint, a field id, a status
// or an icon name has exactly one authoritative spelling here.

const API = Object.freeze({
  FILTERS: '/api/filters',
  COUNTS: '/api/counts',
  LISTINGS: '/api/listings',
  SEARCH: '/api/search',
  SEARCH_STATUS: '/api/search/status',
  WATCH_START: '/api/watch/start',
  WATCH_STOP: '/api/watch/stop',
  DISMISSAL_REASONS: '/api/dismissal-reasons',
  DISMISSALS: '/api/dismissals',
  filter: id => `/api/filters/${id}`,
  opened: id => `/api/listings/${encodeURIComponent(id)}/opened`,
  dismiss: id => `/api/listings/${encodeURIComponent(id)}/dismiss`,
  dismissal: id => `/api/dismissals/${encodeURIComponent(id)}`,
  filterMap: id => `/api/filters/${encodeURIComponent(id)}/map`,
  area: (cities, radiusKm) => `/api/area?cities=${encodeURIComponent(cities)}&radius_km=${encodeURIComponent(radiusKm)}`,
  // The source comes back from the address bar, so every value is encoded, never pasted.
  listings: (filterId, page, sort, source) =>
    `/api/listings?${new URLSearchParams({filter_id: filterId, page, sort, source})}`,
  searchStatus: filterId => `/api/search/status?filter_id=${filterId}`,
});

const HTTP = Object.freeze({
  POST: 'POST',
  PUT: 'PUT',
  DELETE: 'DELETE',
  JSON_HEADERS: Object.freeze({'Content-Type': 'application/json'}),
});

// Element ids, mirrored from index.html.
const EL = Object.freeze({
  FILTER_LIST: 'filterList',
  MAIN: 'mainArea',
  STATUS: 'statusText',
  TOAST: 'toast',
  MODAL: 'filterModal',
  MODAL_TITLE: 'modalTitle',
  SEARCH_BTN: 'searchBtn',
  WATCH_BTN: 'watchBtn',
  SORT: 'sortSelect',
  SETTINGS_LINK: 'settingsLink',
  DISMISSED_LINK: 'dismissedLink',
  REASON_BAR: 'reasonBar',
});

// Listing orders, spelled exactly as `domain/value_objects/listing_sort.py`.
const SORT = Object.freeze({
  PUBLISHED_DESC: 'published_desc',
  PRICE_ASC: 'price_asc',
  PRICE_DESC: 'price_desc',
  SURFACE_DESC: 'surface_desc',
  PRICE_PER_M2_ASC: 'price_per_m2_asc',
  MARKET_POSITION: 'market_position',
});

// Order of the options in the select, and their wording.
const SORT_OPTIONS = Object.freeze([
  Object.freeze({value: SORT.PUBLISHED_DESC, label: 'Parution : plus récentes'}),
  Object.freeze({value: SORT.PRICE_ASC, label: 'Prix : moins cher'}),
  Object.freeze({value: SORT.PRICE_DESC, label: 'Prix : plus cher'}),
  Object.freeze({value: SORT.SURFACE_DESC, label: 'Surface : plus grande'}),
  Object.freeze({value: SORT.PRICE_PER_M2_ASC, label: 'Prix au m² : moins cher'}),
  Object.freeze({value: SORT.MARKET_POSITION, label: 'Position au marché : plus bas'}),
]);

// Licence Ouverte: a page that shows positions names their source (ADR-0010).
const RENT_MAP_CREDIT = 'Positions : estimations ANIL, à partir des données du Groupe SeLoger et de leboncoin (Carte des loyers).';

// Filter-form field ids. `<field>-error` is the id convention for its error slot.
const FIELD = Object.freeze({
  NAME: 'fm-name',
  CITIES: 'fm-cities',
  RADIUS: 'fm-radius',
  EXCLUDED: 'fm-excluded',
  MIN_PRICE: 'fm-min-price',
  MAX_PRICE: 'fm-max-price',
  MIN_SURFACE: 'fm-min-surface',
  MIN_ROOMS: 'fm-min-rooms',
  EXCLUDE_GROUND: 'fm-excl-rdc',
  EXCLUDE_FIRST: 'fm-excl-1st',
  TOP_ONLY: 'fm-top-only',
  MAX_RESULTS: 'fm-max-results',
  NOTIFY_INTERVAL: 'fm-interval',
  REFRESH_INTERVAL: 'fm-refresh',
  MAX_SURFACE: 'fm-max-surface',
  MAX_ROOMS: 'fm-max-rooms',
  MIN_PHOTOS: 'fm-min-photos',
  MAX_AGE: 'fm-max-age',
  EXCLUDED_ADVERTISERS: 'fm-excluded-advertisers',
});
const FURNISHED_RADIO = 'fm-furnished';
const CHARGES_RADIO = 'fm-charges';
const HEATING_RADIO = 'fm-heating';
const MORE_CRITERIA = 'moreCriteria';
// Which form field the server means when it refuses a criterion (W10).
const FIELD_BY_CRITERION = Object.freeze({
  cities: FIELD.CITIES,
  radius_km: FIELD.RADIUS,
  min_price: FIELD.MIN_PRICE,
  max_price: FIELD.MAX_PRICE,
  min_surface_m2: FIELD.MIN_SURFACE,
  max_surface_m2: FIELD.MAX_SURFACE,
  min_rooms: FIELD.MIN_ROOMS,
  max_rooms: FIELD.MAX_ROOMS,
  min_photos: FIELD.MIN_PHOTOS,
  max_age_days: FIELD.MAX_AGE,
  max_results: FIELD.MAX_RESULTS,
  notification_interval_minutes: FIELD.NOTIFY_INTERVAL,
  refresh_interval_minutes: FIELD.REFRESH_INTERVAL,
});
const DPE_CHECKBOX = 'fm-dpe-cb';
const ERROR_SUFFIX = '-error';

// Sprite symbol names, defined once in index.html.
const ICON = Object.freeze({
  SEARCH: 'search',
  WATCH: 'watch',
  STOP: 'stop',
  PLUS: 'plus',
  PENCIL: 'pencil',
  TRASH: 'trash',
  SLIDERS: 'sliders',
  ALERT: 'alert',
  CHEVRON_LEFT: 'chevron-left',
  CHEVRON_RIGHT: 'chevron-right',
  CHECK: 'check',
  SETTINGS: 'settings',
  CLOSE: 'close',
});

const CSS = Object.freeze({
  ICON: 'icon',
  ICON_SM: 'icon-sm',
  SHOW: 'show',
  ACTIVE: 'active',
  HAS_RESULTS: 'has-results',
  FILTER_COUNT: 'filter-count',
  DPE_UNKNOWN: 'dpe-na',
  MASONRY: 'is-masonry',
});

// What the main area shows. Background refreshes only redraw the listings view.
const VIEW = Object.freeze({LISTINGS: 'listings', SETTINGS: 'settings', DISMISSED: 'dismissed'});

// The map (ticket 14). The library is the page's only third-party code: pinned to an
// exact version, integrity-checked, and fetched only when a map is opened.
const MAP_LIBRARY = Object.freeze({
  JS: 'https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js',
  JS_SRI: 'sha384-SYKAG6cglRMN0RVvhNeBY0r3FYKNOJtznwA0v7B5Vp9tr31xAHsZC0DqkQ/pZDmj',
  CSS: 'https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css',
  CSS_SRI: 'sha384-MinO0mNliZ3vwppuPOUnGa+iq619pfMhLVUXfC4LHwSCvF9H+6P/KO4Q7qBOYV5V',
});
const MAP_STYLE = Object.freeze({
  light: 'https://tiles.openfreemap.org/styles/positron',
  dark: 'https://tiles.openfreemap.org/styles/dark',
});
// The whole zone in frame, whatever the box's size: the circle is fitted, not zoomed to.
const MAP_FIT_PADDING_PX = 24;
// Pin names are a text layer, so MapLibre hides the ones that collide and shows them as
// the hunter zooms in. The font is one both tile styles already ship.
const MAP_LABEL_FONT = ['Noto Sans Bold'];
const MAP_LABEL_SIZE_PX = 12;
const MAP_LABEL_OFFSET_EM = 1.6;
const EARTH_RADIUS_KM = 6371;
const MAP_PIN_OFFSET_PX = 16;
const MAP_POPUP_WIDTH = '320px';
const MAP_ZONE_FILL_OPACITY = 0.06;
const MAP_ZONE_LINE_WIDTH = 1.5;
const CIRCLE_STEPS = 64;
const KM_PER_DEGREE = 111.32;
const VIEW_MODE = Object.freeze({LIST: 'list', MAP: 'map'});
const DATA_VIEW = 'data-view';
const MAP_NOTE = 'Carte : OpenFreeMap, données © OpenStreetMap, chargée à la demande.';

// The dismissal gesture speaks `hunt review`'s keys (ticket 05): j/k move, x dismisses,
// then the reason's own key. The reasons and their keys come from the server.
const KEY = Object.freeze({NEXT: 'j', PREVIOUS: 'k', DISMISS: 'x', CANCEL: 'Escape'});
const OTHER_REASON = 'other';
const DATA_DISMISS = 'data-dismiss-id';
const DATA_RESTORE = 'data-restore-id';
const DATA_REASON = 'data-reason';
const TYPING_TARGETS = 'input, textarea, select, [contenteditable]';

// Values of `data-theme` on <html>. `THEME_STORAGE_KEY` and `DEFAULT_THEME` are declared
// by the <head> script of index.html, which applies the choice before the first paint.
const THEME = Object.freeze({LIGHT: 'light', DARK: 'dark', SYSTEM: 'system'});
const THEME_OPTIONS = Object.freeze([
  {value: THEME.LIGHT, label: 'Clair', hint: 'toujours clair'},
  {value: THEME.DARK, label: 'Sombre', hint: 'toujours sombre'},
  {value: THEME.SYSTEM, label: 'Système', hint: 'suit le réglage de l’appareil'},
]);

// Crawl lifecycle reported by /api/search/status.
const SEARCH_STATUS = Object.freeze({SEARCHING: 'searching', DONE: 'done', IDLE: 'idle'});

// Tri-state furnished answer; ANY means "no filter" and maps to null server-side.
const FURNISHED = Object.freeze({ANY: 'any', YES: 'yes', NO: 'no'});

// Form defaults — one home, used by both the edit prefill and the save payload.
const DEFAULT = Object.freeze({
  RADIUS_KM: 20,
  MAX_RESULTS: 25,
  NOTIFY_INTERVAL_MIN: 15,
  REFRESH_INTERVAL_MIN: 30,
});

// Named bounds — no literal in a render or polling path.
const SKELETON_CARDS = 4;
const PAGE_WINDOW = 2;        // pages kept either side of the current one
const LOAD_TIMEOUT_MS = 15_000;
const SEARCH_POLL_MS = 4_000;
const SEARCH_GIVEUP_MS = 360_000;
const WATCH_REFRESH_MS = 30_000;
const TOAST_MS = 3_500;
const UNDO_MS = 6_000;      // long enough to read the toast and reach "Annuler"
const ADVERTISER_MAX_CHARS = 22;
const EUROS = new Intl.NumberFormat('fr-FR', {maximumFractionDigits: 0});

// Relative-date thresholds.
const SECOND_MS = 1_000;
const MINUTE_S = 60;
const HOUR_S = 3_600;
const DAY_S = 86_400;

// Carries a scraped source name from markup to handler without ever becoming JS source.
const DATA_SOURCE = 'data-source';
// No source picked: the list shows every source. Mirrors EVERY_SOURCE in get_top_listings.py.
const ALL_SOURCES = '';

// The list's state as the address bar carries it (W21): a reload or a shared link
// reopens the same filter, page, order, source and view.
const URL_PARAM = Object.freeze({FILTER: 'filtre', PAGE: 'page', SORT: 'tri', SOURCE: 'source', VIEW: 'vue'});
const URL_MAP_VIEW = 'carte';
// Same rule for the listing id: read back from the attribute, never inlined in JS.
const DATA_LISTING = 'data-listing-id';

// Advertiser kinds, spelled exactly as `domain/services/advertiser.py`.
const ADVERTISER = Object.freeze({PRIVATE: 'particulier', AGENCY: 'agence', UNKNOWN: 'inconnu'});

// Protocols an <a href> may carry — mirrors WEB_SCHEMES in domain/services/sanitising.py.
const WEB_PROTOCOLS = Object.freeze(['http:', 'https:']);

const FOCUSABLE = 'button:not([disabled]), [href], input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])';
const MODAL_HIDDEN = 'none';
const MODAL_VISIBLE = 'flex';

const state = {
  filterId: null,
  filters: [],
  listings: [],
  knownIds: new Set(),
  watching: false,
  pollTimer: null,
  counts: {},
  editingFilterId: null,
  activeSource: ALL_SOURCES,
  sourceCounts: {},         // homes per source over the whole filter (W8)
  sort: SORT.PUBLISHED_DESC,
  page: 1,
  pages: 1,
  total: 0,
  unreachable: [],
  lastSearchedAt: null,     // when a source last answered this filter (server's word, W2)
  searchSources: [],        // each source's progress while a search runs (W3)
  view: VIEW.LISTINGS,
  reasons: [],
  focusIndex: -1,
  pendingDismissal: null,   // listing id the reason bar is asking about
  toastTimer: null,
  showMap: false,           // the Liste / Carte switch of the results
  resultsMap: null,         // MapLibre instances, removed before they are redrawn
  filterMap: null,
  mapPopup: null,           // the one popup open on either map; a second never stacks
  mapHomes: [],             // homes the results map loaded, for the popup's « Écarter »
  filterArea: null,
  searchPollTimer: null,
  searchStart: 0,
};

// ── DOM & fetch helpers ───────────────────────────────────────────────────────

const el = id => document.getElementById(id);
const fieldValue = id => el(id).value.trim();
const isChecked = id => el(id).checked;

// Sprite symbols live in index.html; `aria-hidden` because every icon sits next
// to a text label or inside a control carrying its own aria-label.
function icon(name, extra = '') {
  return `<svg class="${CSS.ICON}${extra ? ' ' + extra : ''}" aria-hidden="true"><use href="#i-${name}"/></svg>`;
}

function sendJson(url, method, payload) {
  return fetch(url, {method, headers: HTTP.JSON_HEADERS, body: JSON.stringify(payload)});
}

// ── Init ──────────────────────────────────────────────────────────────────────

window.addEventListener('popstate', () => {
  if (state.filters.length) restoreUrlState();
});

window.addEventListener('load', async () => {
  loadReasons();
  await loadFilters();
  loadAllCounts();
});

async function loadFilters() {
  const res = await fetch(API.FILTERS);
  state.filters = await res.json();
  renderSidebar();
  if (state.filters.length > 0) {
    await restoreUrlState();
  } else {
    renderMain(noFilterState());
  }
}

function emptyState(iconName, title, body, actionHtml = '') {
  return `<div class="empty">
    ${icon(iconName)}
    <p class="empty-title">${title}</p>
    <p>${body}</p>
    ${actionHtml}
  </div>`;
}

function newFilterButton() {
  return `<button type="button" class="btn btn-primary" onclick="openFilterModal()">${icon(ICON.PLUS)} Nouveau filtre</button>`;
}

function noFilterState() {
  return emptyState(ICON.SLIDERS, 'Aucun filtre configuré',
    'Un filtre définit les villes, le budget et les critères à surveiller. Créez le premier pour lancer une recherche.',
    newFilterButton());
}

// ── Sidebar ───────────────────────────────────────────────────────────────────

function renderSidebar() {
  const list = el(EL.FILTER_LIST);
  if (!state.filters.length) {
    list.innerHTML = '<div class="aside-empty">Aucun filtre enregistré.</div>';
    return;
  }
  list.innerHTML = state.filters.map(f => {
    const count = state.counts[f.id];
    const countLabel = count === undefined ? '–' : count;
    const countClass = count > 0 ? `${CSS.FILTER_COUNT} ${CSS.HAS_RESULTS}` : CSS.FILTER_COUNT;
    const isActive = f.id === state.filterId;
    const name = escHtml(f.name);
    const meta = `${escHtml(f.cities.join(', '))} · ±${f.radius_km} km${f.max_price ? ' · max ' + f.max_price + ' €' : ''}`;
    return `
    <div class="filter-row" role="listitem">
      <button type="button" class="filter-item${isActive ? ' ' + CSS.ACTIVE : ''}" ${isActive ? 'aria-current="true"' : ''}
              onclick="selectFilter('${f.id}')">
        <span class="filter-name-row">
          <span class="filter-dot ${f.enabled ? '' : 'off'}" title="Filtre ${f.enabled ? 'actif' : 'désactivé'}"></span>
          <span class="filter-name">${name}</span>
          <span class="${countClass}" title="${countLabel} logement(s) connu(s)">${countLabel}</span>
        </span>
        <span class="filter-meta">${meta}</span>
      </button>
      <div class="filter-actions">
        <button type="button" class="btn-icon" onclick="openFilterModal('${f.id}')" aria-label="Modifier le filtre ${name}">${icon(ICON.PENCIL, CSS.ICON_SM)}</button>
        <button type="button" class="btn-icon is-danger" onclick="deleteFilter('${f.id}')" aria-label="Supprimer le filtre ${name}">${icon(ICON.TRASH, CSS.ICON_SM)}</button>
      </div>
    </div>`;
  }).join('');
}

async function loadAllCounts() {
  try {
    const res = await fetch(API.COUNTS);
    if (!res.ok) return;
    state.counts = await res.json();
    renderSidebar();
  } catch(e) { /* non-critical — sidebar still works without counts */ }
}

// Another filter is a step the Back button returns from; a page, an order, a source or
// a view only rewrite the current entry (`applyListings`), so Back never walks pages.
async function selectFilter(id) {
  enterListings({filterId: id, page: 1, sort: state.sort, source: ALL_SOURCES, showMap: state.showMap});
  history.pushState(null, '', buildPageUrl());
  await loadListings();
}

// Reload, shared link, Back/Forward: the address bar says what to show. A filter id it
// does not know (deleted since) opens the first filter rather than an empty page.
async function restoreUrlState() {
  const params = new URLSearchParams(window.location.search);
  const filterId = params.get(URL_PARAM.FILTER);
  if (!state.filters.some(f => f.id === filterId)) {
    enterListings({filterId: state.filters[0].id, page: 1, sort: state.sort, source: ALL_SOURCES, showMap: false});
    await loadListings();
    return;
  }
  // Values are only hints: the server clamps the page and falls back on an unknown order.
  const page = Number.parseInt(params.get(URL_PARAM.PAGE), 10) || 1;
  enterListings({
    filterId,
    page,
    sort: params.get(URL_PARAM.SORT) || SORT.PUBLISHED_DESC,
    source: params.get(URL_PARAM.SOURCE) || ALL_SOURCES,
    showMap: params.get(URL_PARAM.VIEW) === URL_MAP_VIEW,
  });
  await loadListings(page);
}

function enterListings({filterId, page, sort, source, showMap}) {
  clearTimeout(state.searchPollTimer);  // stop polling a previous filter's crawl
  showListingsView();
  Object.assign(state, {filterId, page, sort, activeSource: source, showMap});
  renderSidebar();
}

function buildPageUrl() {
  const params = new URLSearchParams({[URL_PARAM.FILTER]: state.filterId});
  if (state.page > 1) params.set(URL_PARAM.PAGE, state.page);
  if (state.sort !== SORT.PUBLISHED_DESC) params.set(URL_PARAM.SORT, state.sort);
  if (state.activeSource) params.set(URL_PARAM.SOURCE, state.activeSource);
  if (state.showMap) params.set(URL_PARAM.VIEW, URL_MAP_VIEW);
  return `?${params}`;
}

// ── Listings ────────────────────────────────────────────────────────────────

async function loadListings(page = 1, highlightNew = false, background = false) {
  // A watch or crawl refresh must not tear a side page away from under the reader —
  // checked again once the answer arrives, since the hunter may have left meanwhile.
  if (!state.filterId || state.view !== VIEW.LISTINGS) return;
  // shortcut: a watch refresh leaves an open map alone (no redraw, no lost popup); the
  // counts catch up when the hunter switches back to the list.
  if (background && state.showMap) return;
  state.page = Math.max(1, page);
  if (!background) renderSkeleton();
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), LOAD_TIMEOUT_MS);
  try {
    const res = await fetch(API.listings(state.filterId, state.page, state.sort, state.activeSource), {signal: ctrl.signal});
    clearTimeout(timer);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (state.view !== VIEW.LISTINGS) return;
    state.total = data.total;
    state.sourceCounts = data.source_counts;
    state.unreachable = data.unreachable_sources;
    state.lastSearchedAt = data.last_searched_at;
    state.pages = data.pages;
    state.page = data.page;
    state.sort = data.sort;  // the order actually applied server-side
    applyListings(data.items, highlightNew);
  } catch(e) {
    clearTimeout(timer);
    ctrl.abort();  // drop the rest — ignore any partial response still in flight
    // background refresh (during a crawl) must not flash an empty state
    if (!background && state.view === VIEW.LISTINGS) renderNoListings();
  }
}

function renderSkeleton() {
  const main = el(EL.MAIN);
  main.setAttribute('aria-busy', 'true');
  const card = '<div class="skeleton-card"><div class="sk-line sk-title"></div><div class="sk-line sk-price"></div><div class="sk-line sk-meta"></div></div>';
  main.innerHTML = `<div class="cards" aria-hidden="true">${card.repeat(SKELETON_CARDS)}</div>`
    + '<span class="sr-only">Chargement des logements…</span>';
}

function renderNoListings() {
  // Timeout or error → ignore partial results, present a clean empty state.
  state.listings = []; state.total = 0; state.pages = 1; state.page = 1; state.unreachable = [];
  if (state.filterId) { state.counts[state.filterId] = 0; renderSidebar(); }
  renderMain(emptyState(ICON.ALERT, 'Résultats indisponibles',
    'La liste n’a pas pu être chargée. Relancez une recherche ou réessayez dans un instant.',
    '<button type="button" class="btn" onclick="loadListings(1)">Réessayer</button>'));
}

function applyListings(data, highlightNew) {
  const incoming = new Set(data.map(a => a.id));
  const newIds = highlightNew ? new Set([...incoming].filter(id => !state.knownIds.has(id))) : new Set();
  state.listings = data;
  state.knownIds = incoming;
  // With a source picked, the total is that source's; the sidebar counts every home.
  if (state.filterId && !state.activeSource) { state.counts[state.filterId] = state.total; renderSidebar(); }

  const active = state.filters.find(f => f.id === state.filterId);
  const filterName = active ? active.name : '';

  // The server counts each source over the whole filter, not this page (W8).
  const srcCounts = state.sourceCounts;
  const sources = Object.keys(srcCounts);

  // The source name is a data attribute, never a fragment of inline JS: an HTML entity
  // is decoded before the onclick body is compiled, so escaping cannot protect that
  // context. `wireSourceButtons()` reads the value back after render.
  const pillsHtml = sources.map(src => {
    const pressed = !state.activeSource || state.activeSource === src;
    // The chosen source carries a check: once one is picked, shape and mark agree.
    const check = state.activeSource === src ? icon(ICON.CHECK, CSS.ICON_SM) : '';
    return `<button type="button" class="source-pill" aria-pressed="${pressed}"
      ${DATA_SOURCE}="${escHtml(src)}">${check}${escHtml(src)} <span class="pill-count">${srcCounts[src]}</span></button>`;
  }).join('');

  const pageLabel = state.pages > 1 ? ` <span class="results-page">· page ${state.page} sur ${state.pages}</span>` : '';

  // The tab names the filter and its count; the heading names the page for a screen reader.
  document.title = `${filterName} · ${countHomes(state.total)}`;
  history.replaceState(null, '', buildPageUrl());

  let html = `
    <h1 class="sr-only">${escHtml(filterName)}</h1>
    <div class="main-toolbar">
      <p class="results-meta"><strong>${state.total}</strong> logement${state.total > 1 ? 's' : ''} pour <strong>${escHtml(filterName)}</strong>${pageLabel}</p>
      ${sortControlHtml()}
      ${viewSwitchHtml()}
      <span id="lastUpdated">${lastSearchedLabel()}</span>
    </div>
    ${searchProgressHtml()}
    ${unreachableHtml(state.unreachable)}
    ${sources.length ? `<div class="source-filter-bar" role="group" aria-label="Filtrer par source">${pillsHtml}</div>` : ''}
  `;

  if (state.showMap) {
    html += `<div class="map-view"><div class="map-canvas" id="resultsMap"></div><p class="map-note" id="resultsMapNote">${MAP_NOTE}</p></div>`;
  } else if (!data.length) {
    html += noResultState();
  } else {
    html += `<div class="cards">${data.map(a => renderCard(a)).join('')}</div>`;
    html += `<p class="rent-credit">${RENT_MAP_CREDIT}</p>`;
    html += paginationHtml();
  }

  state.resultsMap?.remove();
  state.resultsMap = null;
  renderMain(html);
  wireViewSwitch();
  if (state.showMap) openResultsMap();
  wireSourceButtons();
  wireOpenLinks();
  wireDismissButtons();
  state.focusIndex = -1;

  // "Détectée", not "nouvelle": this counts what this refresh brought in, while the
  // card badge answers a different question — whether the listing has been opened.
  if (newIds.size > 0) {
    const plural = newIds.size > 1 ? 's' : '';
    showToast(`${newIds.size} annonce${plural} détectée${plural}`);
  }
}

// One observer for the cards on screen: a card's height changes with the column
// width, when its « Nouveau » badge goes, when the fonts arrive. Setting its span never
// changes its height (cards align to the start of their area), so it cannot loop.
const masonryObserver = new ResizeObserver(entries => {
  for (const { target } of entries) spanMasonryCard(target);
});
let masonryGap = 0;

function arrangeMasonry() {
  masonryObserver.disconnect();
  const list = document.querySelector('.cards:not([aria-hidden])');
  if (!list) return;
  // The gap stays in the stylesheet; the rows become 1px, so a card spans gap + height.
  masonryGap = parseFloat(getComputedStyle(list).rowGap) || 0;
  list.classList.add(CSS.MASONRY);
  for (const card of list.children) masonryObserver.observe(card);
}

function spanMasonryCard(card) {
  card.style.gridRowEnd = `span ${Math.ceil(card.getBoundingClientRect().height + masonryGap)}`;
}

function sortControlHtml() {
  const options = SORT_OPTIONS.map(o =>
    `<option value="${o.value}"${o.value === state.sort ? ' selected' : ''}>${o.label}</option>`
  ).join('');
  return `<div class="sort-control">
    <label class="sort-label" for="${EL.SORT}">Trier par</label>
    <select id="${EL.SORT}" class="sort-select" onchange="changeSort(this.value)">${options}</select>
  </div>`;
}

// Changing the order reshuffles the whole result set, so it restarts at page 1.
function changeSort(value) {
  if (value === state.sort) return;
  state.sort = value;
  loadListings(1);
}

// Every source-toggling control carries its source as data, wired after render.
function wireSourceButtons() {
  document.querySelectorAll(`[${DATA_SOURCE}]`).forEach(btn => {
    btn.addEventListener('click', () => toggleSource(btn.dataset.source));
  });
}

// Opening a listing towards its source is what makes it stop being new. The card is
// updated straight away rather than after a reload — the operator is already gone to
// the other tab, and coming back to a still-flagged card reads as a lost click.
function wireOpenLinks() {
  document.querySelectorAll(`[${DATA_LISTING}]`).forEach(link => {
    link.addEventListener('click', () => markOpened(link));
  });
}

function markOpened(link) {
  const listingId = link.dataset.listingId;
  const listing = findListing(listingId);
  if (!listing || listing.opened) return;
  listing.opened = true;
  // Failure is silent on purpose: the listing is open in the other tab either way,
  // and the next read of the DB is what the badge ultimately trusts.
  sendJson(API.opened(listingId), HTTP.POST, {}).catch(() => {});
  // Only the card's own title clears the badge; a duplicate's link marks that other
  // publication read without pretending this one has been.
  if (!link.classList.contains('card-title')) return;
  const card = link.closest('.card');
  if (card) {
    card.classList.remove('is-new');
    card.querySelector('.card-new-badge')?.remove();
  }
}

// A listing is either a group's leader or one of the duplicates behind it.
function findListing(id) {
  for (const home of [...state.listings, ...state.mapHomes]) {
    if (home.id === id) return home;
    const duplicate = (home.also_on || []).find(other => other.id === id);
    if (duplicate) return duplicate;
  }
  return null;
}

function noResultState() {
  if (state.activeSource) {
    return emptyState(ICON.SEARCH, 'Aucun logement pour cette source',
      'Réactivez la source ou repassez sur toutes les sources.',
      `<button type="button" class="btn" ${DATA_SOURCE}="${escHtml(state.activeSource)}">Toutes les sources</button>`);
  }
  return emptyState(ICON.SEARCH, 'Aucun logement pour ce filtre',
    'Rien en base pour ces critères. Lancez un crawl, ou élargissez le rayon et le budget du filtre.',
    `<button type="button" class="btn btn-primary" onclick="triggerSearch()">${icon(ICON.SEARCH)} Rechercher</button>`);
}

// Windowed pagination: first, last, and the current page ±PAGE_WINDOW.
// O(w) per render with w = window size, instead of one button per page.
function pageNumbers(current, total) {
  const shown = new Set([1, total]);
  for (let p = current - PAGE_WINDOW; p <= current + PAGE_WINDOW; p++) {
    if (p >= 1 && p <= total) shown.add(p);
  }
  return [...shown].sort((a, b) => a - b);
}

function paginationHtml() {
  if (state.pages <= 1) return '';
  const arrow = (label, iconName, target, disabled) =>
    `<button type="button" class="page-btn" aria-label="${label}" ${disabled ? 'disabled' : `onclick="gotoPage(${target})"`}>${icon(iconName, CSS.ICON_SM)}</button>`;

  let nums = '';
  let previous = 0;
  for (const p of pageNumbers(state.page, state.pages)) {
    if (p - previous > 1) nums += '<span class="page-gap" aria-hidden="true">…</span>';
    nums += `<button type="button" class="page-btn" ${p === state.page ? 'aria-current="page"' : ''}
      aria-label="Page ${p}" onclick="gotoPage(${p})">${p}</button>`;
    previous = p;
  }

  return `<nav class="pagination" aria-label="Pagination des logements">
    ${arrow('Page précédente', ICON.CHEVRON_LEFT, state.page - 1, state.page === 1)}
    ${nums}
    ${arrow('Page suivante', ICON.CHEVRON_RIGHT, state.page + 1, state.page === state.pages)}
  </nav>`;
}

function gotoPage(p) {
  if (p < 1 || p > state.pages || p === state.page) return;
  loadListings(p);
  window.scrollTo({top: 0, behavior: 'smooth'});
}

// The server picks the source, so its homes are paged together and never lost on a
// page that holds none of them.
function toggleSource(src) {
  state.activeSource = state.activeSource === src ? ALL_SOURCES : src;
  loadListings(1);
}

function energyBadge(label, rating) {
  // Always show the label and the letter; colour never carries the rating alone.
  const cls = rating ? `dpe-${rating}` : CSS.DPE_UNKNOWN;
  const spoken = rating ? `${label} ${rating}` : `${label} non communiqué`;
  return `<span class="energy-pair">
    <span class="energy-label" aria-hidden="true">${label}</span>
    <span class="dpe-badge ${cls}" aria-hidden="true">${rating || '?'}</span>
    <span class="sr-only">${spoken}</span>
  </span>`;
}

// One statement about money (W1): the total is charges included, and this line says
// what it is made of. A total with no charges accounted for understates the real cost.
function chargesHtml(a) {
  if (a.charges_unknown) return '<span class="is-uncertain">loyer seul, charges&nbsp;?</span>';
  if (a.price.charges) return `loyer ${formatEuros(a.price.amount)} + ${formatEuros(a.price.charges)} de charges`;
  return 'charges comprises';
}

function formatEuros(amount) {
  return `${EUROS.format(amount)}\u202f€`;
}

// F and G carry a letting ban with a date; the server words it, the card prints it.
function rentalBanHtml(warning) {
  if (!warning) return '';
  return `<p class="card-warning">${icon(ICON.ALERT, CSS.ICON_SM)}${escHtml(warning)}</p>`;
}

// A source that stopped answering: its listing may be gone. Neutral, it is a doubt
// about the data, not a status (ticket 04 keeps colour for "new").
function sourceDownHtml(warning) {
  if (!warning) return '';
  return `<p class="card-source-down">${escHtml(warning)}</p>`;
}

// What the page does not show, and why: listings of a source down for over a week.
function unreachableHtml(unreachable) {
  if (!unreachable.length) return '';
  const lines = unreachable.map(u => {
    const down = `${escHtml(u.source)} injoignable depuis ${u.down_days} j`;
    if (!u.hidden_count) return `${down} : ses annonces sont peut-être expirées`;
    const plural = u.hidden_count > 1 ? 's' : '';
    return `${u.hidden_count} annonce${plural} masquée${plural} : ${down}`;
  });
  return `<div class="results-notice" role="status">${lines.map(l => `<p>${l}</p>`).join('')}</div>`;
}

// Who publishes: an agency charges letting fees, a private landlord charges none.
function advertiserLabel(a) {
  if (a.advertiser_kind === ADVERTISER.PRIVATE) return 'Particulier';
  if (!a.advertiser) return a.advertiser_kind === ADVERTISER.AGENCY ? 'Agence' : 'annonceur inconnu';
  const name = a.advertiser.length > ADVERTISER_MAX_CHARS ? `${a.advertiser.substring(0, ADVERTISER_MAX_CHARS)}…` : a.advertiser;
  return `<span title="${escHtml(a.advertiser)}">${escHtml(name)}</span>`;
}

// The same home published elsewhere. Every duplicate keeps its own link and its own
// id, so a wrong grouping costs a glance — and opening one clears its own badge.
function duplicatesHtml(alsoOn) {
  if (!alsoOn || !alsoOn.length) return '';
  const links = alsoOn.map(other => {
    const url = safeUrl(other.url);
    const label = escHtml(other.network || other.source);
    const price = escHtml(other.price.display_total);
    return url
      ? `<a class="dup-link" href="${escHtml(url)}" target="_blank" rel="noopener noreferrer"
           ${DATA_LISTING}="${escHtml(other.id)}" title="${price}">${label}</a>`
      : `<span class="dup-link">${label}</span>`;
  }).join(', ');
  return `<span>aussi sur ${links}</span>`;
}

function publishedLabel(a) {
  // Sites that publish no date (Century 21, Laforêt, Citya) fall back to our
  // first-seen time — prefix it so it never reads as a real parution date.
  const relative = a.published_at ? relativeDate(a.published_at) : '';
  const fromSite = a.published_at_from_site !== false;
  return {
    text: relative ? `${fromSite ? 'paru' : 'vu'} ${relative}` : '',
    title: fromSite
      ? 'Date de parution annoncée par le site'
      : 'Date de première détection : ce site ne publie pas de date de parution',
    estimated: !fromSite,
  };
}

// A listing whose link isn't http(s) still shows — as plain text, never as a link.
// The id rides as a data attribute so opening the link can clear the "Nouveau" mark.
function titleHtml(a) {
  const url = safeUrl(a.url);
  const title = escHtml(a.title);
  return url
    ? `<a href="${escHtml(url)}" target="_blank" rel="noopener noreferrer" class="card-title"
         ${DATA_LISTING}="${escHtml(a.id)}">${title}</a>`
    : `<span class="card-title">${title}</span>`;
}

// Where the rent sits against the Carte des loyers, right after the total. Neutral like
// every figure: « hors fourchette » earns weight, never a hue (colour budget). The
// reference it was measured against is spelled out for a screen reader and on hover.
function positionHtml(position) {
  const cls = position.outside_range ? 'card-position is-outside' : 'card-position';
  const reference = position.reference ? ` <span class="sr-only">Référence : ${escHtml(position.reference)}</span>` : '';
  const title = position.reference ? ` title="Réf. ${escHtml(position.reference)}"` : '';
  return `<p class="${cls}"${title}>${escHtml(position.label)}${reference}</p>`;
}

// One decision line per home (ticket 06): the figures the dismissal reasons judge come
// first — total and commune, then size, storey, energy — then money and who publishes. The
// title is only the way in, and the whole card is that way in.
function renderCard(a) {
  // "Nouveau" means never opened towards its source — not "arrived in this page load".
  const isNew = a.opened === false;
  const size = `${a.rooms ? 'T' + a.rooms : 'T?'} · ${a.surface_m2 ? Math.round(a.surface_m2) + '\u202fm²' : '? m²'}`;
  const storey = a.floor ? escHtml(a.floor.label) : 'étage ?';
  const notes = [];
  if (a.furnished === true) notes.push('Meublé');
  if (a.collective_heating === true) notes.push('Chauffage collectif');

  const published = publishedLabel(a);
  const meta = [`<span>${escHtml(a.source)}</span>`];
  if (published.text) meta.push(`<span class="${published.estimated ? 'is-estimated' : ''}" title="${published.title}">${published.text}</span>`);
  if (a.images && a.images.length) meta.push(`<span>${a.images.length} photo${a.images.length > 1 ? 's' : ''}</span>`);
  const duplicates = duplicatesHtml(a.also_on);
  if (duplicates) meta.push(duplicates);

  return `
    <article class="card${isNew ? ' is-new' : ''}" tabindex="-1">
      <div class="card-top">
        ${isNew ? '<span class="card-new-badge">Nouveau</span>' : ''}
        <span class="card-price">${formatEuros(a.price.total)}</span><span class="card-price-unit">CC</span>
        <span class="card-city">${escHtml(a.location.city)}</span>
        <button type="button" class="card-dismiss" ${DATA_DISMISS}="${escHtml(a.id)}" aria-keyshortcuts="${KEY.DISMISS}">${icon(ICON.CLOSE, CSS.ICON_SM)}Écarter</button>
      </div>
      ${positionHtml(a.market_position)}
      <p class="card-facts">${size} · ${storey} · ${energyBadge('DPE', a.dpe_rating)} ${energyBadge('GES', a.ges_rating)}</p>
      <p class="card-money">${chargesHtml(a)} · ${advertiserLabel(a)}</p>
      ${notes.length ? `<p class="card-note">${notes.join(' · ')}</p>` : ''}
      ${a.former_dismissal ? `<p class="card-note">${escHtml(a.former_dismissal)}</p>` : ''}
      ${a.restored ? `<p class="card-note">${escHtml(a.restored)}</p>` : ''}
      ${rentalBanHtml(a.rental_ban_warning)}
      ${sourceDownHtml(a.source_down_warning)}
      <p class="card-title-row">${titleHtml(a)}</p>
      <p class="card-meta">${meta.join(' · ')}</p>
    </article>
  `;
}

// ── Paramètres ──────────────────────────────────────────────────────────────

// A side page takes the main area; background refreshes leave it alone until the
// hunter goes back (loadListings only draws the listings view).
function showSidePage(view, linkId, html) {
  showListingsView();
  state.view = view;
  el(linkId).setAttribute('aria-current', 'page');
  renderMain(html);
  document.title = el(EL.MAIN).querySelector('h1').textContent;
  el(EL.MAIN).focus();
}

function openSettings() {
  showSidePage(VIEW.SETTINGS, EL.SETTINGS_LINK, settingsPageHtml());
}

async function closeSidePage() {
  showListingsView();
  if (state.filterId) await loadListings(state.page);
  else renderMain(noFilterState());
}

function showListingsView() {
  state.view = VIEW.LISTINGS;
  el(EL.SETTINGS_LINK).removeAttribute('aria-current');
  el(EL.DISMISSED_LINK).removeAttribute('aria-current');
}

function readTheme() {
  return document.documentElement.dataset.theme;
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  try { localStorage.setItem(THEME_STORAGE_KEY, theme); } catch(e) { /* private mode: this session only */ }
}

function themePreviewHtml(theme) {
  const lines = '<span class="preview-line is-title"></span><span class="preview-line is-accent"></span><span class="preview-line"></span>';
  if (theme !== THEME.SYSTEM) return `<span class="theme-preview is-${theme}" aria-hidden="true">${lines}</span>`;
  // Système is either, depending on the device: show both halves.
  return `<span class="theme-preview is-split" aria-hidden="true">
    <span class="theme-preview is-${THEME.LIGHT}">${lines}</span><span class="theme-preview is-${THEME.DARK}">${lines}</span>
  </span>`;
}

function settingsPageHtml() {
  const current = readTheme();
  const options = THEME_OPTIONS.map(o => `
    <label class="theme-option">
      <input type="radio" name="theme" value="${o.value}"${o.value === current ? ' checked' : ''} onchange="applyTheme(this.value)">
      ${themePreviewHtml(o.value)}
      <span class="theme-name">${o.label}<small>${o.hint}</small></span>
    </label>`).join('');
  return `
    <section class="settings-page" aria-labelledby="settingsTitle">
      <h1 id="settingsTitle">Paramètres</h1>
      <p class="settings-hint">Réglages de cette interface, enregistrés dans ce navigateur.</p>
      <h2 class="settings-section" id="themeTitle">Apparence</h2>
      <p class="settings-hint">Le terminal (<code>hunt review</code>) garde les couleurs de votre terminal.</p>
      <fieldset class="theme-options" aria-labelledby="themeTitle">${options}</fieldset>
      <button type="button" class="btn settings-back" onclick="closeSidePage()">${icon(ICON.CHEVRON_LEFT)} Retour aux résultats</button>
    </section>`;
}

// ── Écarter (ticket 05, ADR-0009) ───────────────────────────────────────────

async function loadReasons() {
  try {
    const res = await fetch(API.DISMISSAL_REASONS);
    if (res.ok) state.reasons = await res.json();
  } catch(e) { /* the bar opens empty and says so; listing still works */ }
}

function wireDismissButtons() {
  document.querySelectorAll(`[${DATA_DISMISS}]`).forEach(btn => {
    btn.addEventListener('click', () => openReasonBar(btn.getAttribute(DATA_DISMISS)));
  });
}

function describeHome(a) {
  return `${formatEuros(a.price.total)} CC · ${escHtml(a.location.city)} · ${a.rooms ? 'T' + a.rooms : 'T?'}`;
}

function openReasonBar(id) {
  const listing = findListing(id);
  if (!listing) return;
  state.pendingDismissal = id;
  const chips = state.reasons.map(r =>
    `<button type="button" class="reason-chip" ${DATA_REASON}="${r.value}"><kbd>${r.key}</kbd>${r.label}</button>`).join('');
  const bar = el(EL.REASON_BAR);
  bar.innerHTML = `
    <p class="reason-title" id="reasonBarTitle">Écarter ${describeHome(listing)} : pour quelle raison ?</p>
    <div class="reason-chips">${chips || 'Raisons indisponibles, rechargez la page.'}</div>
    <p class="reason-hint">Touche de la raison, <kbd>Échap</kbd> annule. Au clavier : <kbd>${KEY.NEXT}</kbd>/<kbd>${KEY.PREVIOUS}</kbd> pour passer d’une carte à l’autre, <kbd>${KEY.DISMISS}</kbd> pour écarter.</p>`;
  bar.hidden = false;
  bar.querySelectorAll(`[${DATA_REASON}]`).forEach(chip =>
    chip.addEventListener('click', () => chooseReason(chip.getAttribute(DATA_REASON))));
  bar.querySelector('button')?.focus();
}

function closeReasonBar() {
  const id = state.pendingDismissal;
  el(EL.REASON_BAR).hidden = true;
  state.pendingDismissal = null;
  // Back where the gesture started, so the next j/k carries on from there.
  if (id) document.querySelector(`[${DATA_DISMISS}="${CSS.escape(id)}"]`)?.focus();
}

function chooseReason(value) {
  if (value !== OTHER_REASON) return dismissHome(state.pendingDismissal, value, '');
  const bar = el(EL.REASON_BAR);
  if (bar.querySelector('form')) return;
  bar.insertAdjacentHTML('beforeend', `
    <form class="reason-other">
      <label for="reasonNote">Autre raison</label>
      <input id="reasonNote" type="text" maxlength="200" autocomplete="off" placeholder="En quelques mots…">
      <button type="submit" class="btn">Écarter</button>
    </form>`);
  const form = bar.querySelector('form');
  form.addEventListener('submit', e => {
    e.preventDefault();
    dismissHome(state.pendingDismissal, OTHER_REASON, el('reasonNote').value.trim());
  });
  el('reasonNote').focus();
}

async function dismissHome(id, reason, note) {
  const listing = findListing(id);
  const label = state.reasons.find(r => r.value === reason)?.label || reason;
  try {
    const res = await sendJson(API.dismiss(id), HTTP.POST, {reason, note});
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
  } catch(e) {
    showErrorToast(`Écart impossible (${e.message}) : rien n’a changé.`);
    return;
  }
  el(EL.REASON_BAR).hidden = true;
  state.pendingDismissal = null;
  // Reloaded rather than patched: the server hides the home's duplicates with it.
  await loadListings(state.page, false, true);
  showActionToast(`Écarté : ${listing ? describeHome(listing) : ''} (${escHtml(label)})`, 'Annuler', () => restoreHome(id));
}

async function restoreHome(id) {
  try {
    const res = await fetch(API.dismissal(id), {method: HTTP.DELETE});
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
  } catch(e) {
    showErrorToast(`Restauration impossible (${e.message}).`);
    return;
  }
  showToast('Logement restauré');
  if (state.view === VIEW.DISMISSED) await openDismissed();
  else await loadListings(state.page, false, true);
}

function moveCardFocus(step) {
  const cards = [...document.querySelectorAll('#mainArea .card')];
  if (!cards.length) return;
  state.focusIndex = Math.max(0, Math.min(cards.length - 1, state.focusIndex + step));
  cards[state.focusIndex].focus();
}

function findFocusedCardId() {
  const card = document.activeElement?.closest('.card');
  return card?.querySelector(`[${DATA_DISMISS}]`)?.getAttribute(DATA_DISMISS);
}

document.addEventListener('keydown', e => {
  if (e.target.closest(TYPING_TARGETS) || e.metaKey || e.ctrlKey || e.altKey) return;
  if (el(EL.MODAL).style.display === MODAL_VISIBLE) return;
  if (!el(EL.REASON_BAR).hidden) {
    if (e.key === KEY.CANCEL) { e.preventDefault(); closeReasonBar(); return; }
    const reason = state.reasons.find(r => r.key === e.key);
    if (reason) { e.preventDefault(); chooseReason(reason.value); }
    return;
  }
  if (state.view !== VIEW.LISTINGS) return;
  if (e.key === KEY.NEXT) { e.preventDefault(); moveCardFocus(1); }
  if (e.key === KEY.PREVIOUS) { e.preventDefault(); moveCardFocus(-1); }
  if (e.key === KEY.DISMISS) {
    const id = findFocusedCardId();
    if (id) { e.preventDefault(); openReasonBar(id); }
  }
});

// The restore page: what `hunt review --dismissed` would list, with one button each.
async function openDismissed() {
  let dismissals = [];
  try {
    const res = await fetch(API.DISMISSALS);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    dismissals = await res.json();
  } catch(e) {
    showErrorToast(`Écartés indisponibles (${e.message}).`);
    return;
  }
  showSidePage(VIEW.DISMISSED, EL.DISMISSED_LINK, dismissedPageHtml(dismissals));
  document.querySelectorAll(`[${DATA_RESTORE}]`).forEach(btn =>
    btn.addEventListener('click', () => restoreHome(btn.getAttribute(DATA_RESTORE))));
}

function dismissedPageHtml(dismissals) {
  const rows = dismissals.map(d => {
    const size = [d.rooms ? `T${d.rooms}` : '', d.surface_m2 ? `${Math.round(d.surface_m2)}\u202fm²` : ''].filter(Boolean).join(' · ');
    const when = new Date(d.dismissed_at).toLocaleDateString('fr-FR', {day: '2-digit', month: '2-digit'});
    const reason = d.note ? `${escHtml(d.reason)} : ${escHtml(d.note)}` : escHtml(d.reason);
    return `<li class="dismissed-row">
      <span><strong>${formatEuros(d.total_price)} CC</strong> · ${[d.city ? `<span class="dismissed-city">${escHtml(d.city)}</span>` : '', size, escHtml(d.source)].filter(Boolean).join(' · ')}<br>
      <small>écarté le ${when} · ${reason}</small></span>
      <button type="button" class="btn" ${DATA_RESTORE}="${escHtml(d.listing_id)}">Restaurer</button>
    </li>`;
  }).join('');
  return `
    <section class="settings-page" aria-labelledby="dismissedTitle">
      <h1 id="dismissedTitle">Logements écartés</h1>
      <p class="settings-hint">Masqués partout, sur toutes les sources : page, revue et alertes. Restaurer les remet dans la liste.</p>
      ${rows ? `<ul class="dismissed-list">${rows}</ul>` : '<p class="settings-hint">Aucun logement écarté.</p>'}
      <button type="button" class="btn settings-back" onclick="closeSidePage()">${icon(ICON.CHEVRON_LEFT)} Retour aux résultats</button>
    </section>`;
}

// ── Carte (ticket 14) ───────────────────────────────────────────────────────

let mapLibraryPromise = null;

function loadMapLibrary() {
  mapLibraryPromise ??= new Promise((resolve, reject) => {
    const css = Object.assign(document.createElement('link'), {
      rel: 'stylesheet', href: MAP_LIBRARY.CSS, integrity: MAP_LIBRARY.CSS_SRI, crossOrigin: 'anonymous'});
    const script = Object.assign(document.createElement('script'), {
      src: MAP_LIBRARY.JS, integrity: MAP_LIBRARY.JS_SRI, crossOrigin: 'anonymous'});
    script.onload = () => resolve(window.maplibregl);
    script.onerror = () => { mapLibraryPromise = null; reject(new Error('bibliothèque de carte injoignable')); };
    document.head.append(css, script);
  });
  return mapLibraryPromise;
}

function resolveThemeName() {
  const theme = readTheme();
  if (theme !== THEME.SYSTEM) return theme;
  return matchMedia('(prefers-color-scheme: dark)').matches ? THEME.DARK : THEME.LIGHT;
}

// MapLibre paints with plain colours: a token is resolved, then rasterised to rgb.
function readTokenColour(token) {
  const probe = document.createElement('span');
  probe.style.color = `var(${token})`;
  document.body.appendChild(probe);
  const computed = getComputedStyle(probe).color;
  probe.remove();
  const ctx = document.createElement('canvas').getContext('2d');
  ctx.fillStyle = computed;
  ctx.fillRect(0, 0, 1, 1);
  const [r, g, b] = ctx.getImageData(0, 0, 1, 1).data;
  return `rgb(${r}, ${g}, ${b})`;
}

// Kilometres between two points, as the radius check measures them (haversine).
function computeDistanceKm(a, b) {
  const toRad = deg => deg * Math.PI / 180;
  const x = Math.sin(toRad(b.lat - a.lat) / 2) ** 2
    + Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(toRad(b.lng - a.lng) / 2) ** 2;
  return 2 * EARTH_RADIUS_KM * Math.asin(Math.sqrt(x));
}

function buildCircleBounds(centre, radiusKm) {
  const ring = buildCircle(centre, radiusKm).geometry.coordinates[0];
  const lngs = ring.map(([lng]) => lng);
  const lats = ring.map(([, lat]) => lat);
  return [[Math.min(...lngs), Math.min(...lats)], [Math.max(...lngs), Math.max(...lats)]];
}

function buildCircle({lat, lng}, radiusKm) {
  const ring = [];
  for (let i = 0; i <= CIRCLE_STEPS; i++) {
    const angle = (i / CIRCLE_STEPS) * 2 * Math.PI;
    ring.push([
      lng + (radiusKm / (KM_PER_DEGREE * Math.cos(lat * Math.PI / 180))) * Math.cos(angle),
      lat + (radiusKm / KM_PER_DEGREE) * Math.sin(angle),
    ]);
  }
  return {type: 'Feature', geometry: {type: 'Polygon', coordinates: [ring]}};
}

function showMapUnavailable(container, reason) {
  container.replaceChildren(Object.assign(document.createElement('p'), {
    className: 'map-unavailable',
    textContent: `Carte indisponible (${reason}). La liste et le filtre restent utilisables.`,
  }));
}

// The zone is drawn in neutral ink: a radius is a fact about the filter, not a status.
async function createZoneMap(container, centre, radiusKm) {
  let maplibregl;
  try {
    maplibregl = await loadMapLibrary();
  } catch(e) {
    showMapUnavailable(container, e.message);
    return null;
  }
  const map = new maplibregl.Map({
    container, style: MAP_STYLE[resolveThemeName()],
    bounds: buildCircleBounds(centre, radiusKm), fitBoundsOptions: {padding: MAP_FIT_PADDING_PX},
    attributionControl: {compact: true},
  });
  map.on('load', () => {
    map.resize();
    const ink = readTokenColour('--text-muted');
    map.addSource('zone', {type: 'geojson', data: buildCircle(centre, radiusKm)});
    map.addLayer({id: 'zone-fill', type: 'fill', source: 'zone', paint: {'fill-color': ink, 'fill-opacity': MAP_ZONE_FILL_OPACITY}});
    map.addLayer({id: 'zone-line', type: 'line', source: 'zone', paint: {'line-color': ink, 'line-width': MAP_ZONE_LINE_WIDTH}});
  });
  return map;
}

// A marker is a real button built with textContent: a commune name never becomes HTML.
function createMarkerButton(className, text, label) {
  const button = Object.assign(document.createElement('button'), {type: 'button', className, textContent: text});
  button.setAttribute('aria-label', label);
  return button;
}

// One popup at a time: a marker click stops propagation, so MapLibre's own
// close-on-map-click never fires and popups used to pile up.
function openMapPopup(map, lngLat, content) {
  state.mapPopup?.remove();
  state.mapPopup = new window.maplibregl.Popup({offset: MAP_PIN_OFFSET_PX, maxWidth: MAP_POPUP_WIDTH, focusAfterOpen: false})
    .setLngLat(lngLat).setDOMContent(content).addTo(map);
  state.mapPopup.getElement().querySelector('.maplibregl-popup-close-button')?.setAttribute('aria-label', 'Fermer');
  state.mapPopup.on('close', () => { state.mapPopup = null; });
}

function whenMapLoaded(map, action) {
  if (map.loaded()) action();
  else map.once('load', action);
}

// Each pin names its commune under it: a count alone left « which town is this? » to a
// click, and a pin north of the lake read as Annecy.
function labelPins(map, pins) {
  map.addSource('pin-names', {type: 'geojson', data: {type: 'FeatureCollection', features: pins.map(pin => ({
    type: 'Feature', properties: {name: pin.name}, geometry: {type: 'Point', coordinates: [pin.lng, pin.lat]}}))}});
  map.addLayer({id: 'pin-names', type: 'symbol', source: 'pin-names', layout: {
    'text-field': ['get', 'name'], 'text-font': MAP_LABEL_FONT, 'text-size': MAP_LABEL_SIZE_PX,
    'text-anchor': 'top', 'text-offset': [0, MAP_LABEL_OFFSET_EM]}, paint: {
    'text-color': readTokenColour('--text'), 'text-halo-color': readTokenColour('--surface'), 'text-halo-width': 2}});
}

function formatDistanceLabel(centre, point) {
  return `à ${Math.round(computeDistanceKm(centre, point))}\u202fkm du centre`;
}

function placeMarker(map, button, {lat, lng}) {
  new window.maplibregl.Marker({element: button}).setLngLat([lng, lat]).addTo(map);
  // MapLibre names every marker "Map marker"; the commune keeps its own name.
  button.setAttribute('aria-label', button.dataset.label);
}

function viewSwitchHtml() {
  return `<div class="view-switch" role="group" aria-label="Affichage">
    <button type="button" ${DATA_VIEW}="${VIEW_MODE.LIST}" aria-pressed="${!state.showMap}">Liste</button>
    <button type="button" ${DATA_VIEW}="${VIEW_MODE.MAP}" aria-pressed="${state.showMap}">Carte</button>
  </div>`;
}

function wireViewSwitch() {
  document.querySelectorAll(`[${DATA_VIEW}]`).forEach(btn => btn.addEventListener('click', () => {
    state.showMap = btn.getAttribute(DATA_VIEW) === VIEW_MODE.MAP;
    applyListings(state.listings, false);
  }));
}

function countHomes(count) {
  return `${count} logement${count > 1 ? 's' : ''}`;
}

async function openResultsMap() {
  const container = el('resultsMap');
  let filterMap;
  try {
    const res = await fetch(API.filterMap(state.filterId));
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    filterMap = await res.json();
  } catch(e) {
    showMapUnavailable(container, e.message);
    return;
  }
  if (!filterMap.centre) { showMapUnavailable(container, 'commune du filtre non géocodée'); return; }
  const map = await createZoneMap(container, filterMap.centre, filterMap.radius_km);
  if (!map || !state.showMap) { map?.remove(); return; }
  state.resultsMap = map;
  state.mapHomes = filterMap.pins.flatMap(pin => pin.homes.flatMap(home => [home, ...(home.also_on || [])]));
  filterMap.pins.forEach(pin => {
    const label = `${pin.name} : ${countHomes(pin.homes.length)}`;
    const button = createMarkerButton('map-pin', String(pin.homes.length), label);
    button.dataset.label = label;
    button.addEventListener('click', e => {
      e.stopPropagation();
      openMapPopup(map, [pin.lng, pin.lat], buildPinDetail(pin, filterMap.centre));
    });
    placeMarker(map, button, pin);
  });
  whenMapLoaded(map, () => labelPins(map, filterMap.pins));
  if (filterMap.unplaced) {
    el('resultsMapNote').textContent = `${MAP_NOTE} ${countHomes(filterMap.unplaced)} sans position : leur commune n’est pas géocodée.`;
  }
}

// What a pin opens: the commune's homes, each one decision line, its own link, and the
// same « Écarter » as its card.
function buildPinDetail(pin, centre) {
  const box = document.createElement('div');
  box.className = 'map-detail';
  box.appendChild(Object.assign(document.createElement('p'), {
    className: 'map-detail-title', textContent: `${pin.name} · ${countHomes(pin.homes.length)}`}));
  box.appendChild(Object.assign(document.createElement('p'), {
    className: 'map-detail-meta', textContent: formatDistanceLabel(centre, pin)}));
  const list = Object.assign(document.createElement('ul'), {className: 'map-detail-list'});
  pin.homes.forEach(home => {
    const item = document.createElement('li');
    const size = [home.rooms ? `T${home.rooms}` : '', home.surface_m2 ? `${Math.round(home.surface_m2)}\u202fm²` : ''].filter(Boolean).join(' · ');
    const text = [`${formatEuros(home.price.total)} CC`, size, home.dpe_rating ? `DPE ${home.dpe_rating}` : ''].filter(Boolean).join(' · ');
    const url = safeUrl(home.url);
    const line = url
      ? Object.assign(document.createElement('a'), {href: url, target: '_blank', rel: 'noopener noreferrer', textContent: text, title: home.title})
      : Object.assign(document.createElement('span'), {textContent: text});
    if (url) {
      line.setAttribute(DATA_LISTING, home.id);
      line.addEventListener('click', () => markOpened(line));
    }
    if (home.opened === false) item.appendChild(Object.assign(document.createElement('span'), {className: 'card-new-badge', textContent: 'Nouveau'}));
    item.appendChild(line);
    const dismiss = Object.assign(document.createElement('button'), {type: 'button', className: 'card-dismiss', textContent: 'Écarter'});
    dismiss.setAttribute(DATA_DISMISS, home.id);
    dismiss.setAttribute('aria-label', `Écarter ${line.textContent}`);
    dismiss.addEventListener('click', () => { state.mapPopup?.remove(); openReasonBar(home.id); });
    item.appendChild(dismiss);
    list.appendChild(item);
  });
  box.appendChild(list);
  return box;
}

// The filter modal's map: the radius as it is typed, and a click excludes a commune.
async function openFilterAreaMap() {
  const container = el('filterMap');
  state.filterMap?.remove();
  state.filterMap = null;
  const cities = fieldValue(FIELD.CITIES);
  const radiusKm = Number(fieldValue(FIELD.RADIUS));
  if (!cities) { container.replaceChildren(Object.assign(document.createElement('p'), {className: 'map-unavailable', textContent: 'Indiquez une ville pour voir la zone.'})); return; }
  try {
    const res = await fetch(API.area(cities, radiusKm));
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    state.filterArea = await res.json();
  } catch(e) {
    showMapUnavailable(container, e.message);
    return;
  }
  if (!state.filterArea.centre) { showMapUnavailable(container, 'ville inconnue du géocodage'); return; }
  container.replaceChildren();
  const map = await createZoneMap(container, state.filterArea.centre, radiusKm);
  if (!map) return;
  state.filterMap = map;
  const excluded = new Set(readExcludedCities().map(normaliseCommune));
  state.filterArea.communes.forEach(commune => {
    const name = formatCommuneName(commune.name);
    const isExcluded = excluded.has(normaliseCommune(name));
    const button = createMarkerButton(`map-commune${isExcluded ? ' is-excluded' : ''}`, '', name);
    button.dataset.label = describeCommuneMarker(name, isExcluded);
    button.title = name;
    // A tap names the commune first: excluding straight away punished the hunter for
    // asking « which town is this dot? ».
    button.addEventListener('click', e => {
      e.stopPropagation();
      openMapPopup(map, [commune.lng, commune.lat], buildCommuneDetail(name, commune, button));
    });
    placeMarker(map, button, commune);
  });
}

function describeCommuneMarker(name, isExcluded) {
  return isExcluded ? `${name} (exclue)` : name;
}

function buildCommuneDetail(name, commune, marker) {
  const box = document.createElement('div');
  box.className = 'map-detail';
  box.appendChild(Object.assign(document.createElement('p'), {className: 'map-detail-title', textContent: name}));
  box.appendChild(Object.assign(document.createElement('p'), {
    className: 'map-detail-meta', textContent: formatDistanceLabel(state.filterArea.centre, commune)}));
  const isExcluded = marker.classList.contains('is-excluded');
  const action = Object.assign(document.createElement('button'), {
    type: 'button', className: 'btn', textContent: isExcluded ? 'Réinclure cette commune' : 'Exclure cette commune'});
  action.addEventListener('click', () => {
    toggleExcludedCommune(name, marker);
    state.mapPopup?.remove();
  });
  box.appendChild(action);
  return box;
}

function readExcludedCities() {
  return fieldValue(FIELD.EXCLUDED).split(',').map(s => s.trim()).filter(Boolean);
}

// Same comparison as the matcher: trimmed, lower case.
function normaliseCommune(name) {
  return name.trim().toLowerCase();
}

// The commune table is keyed in lower case; the form shows the name with its capitals.
function formatCommuneName(name) {
  return name.replace(/(^|[\s-])\p{L}/gu, letter => letter.toUpperCase());
}

function toggleExcludedCommune(name, button) {
  const list = readExcludedCities();
  const isExcluded = list.some(city => normaliseCommune(city) === normaliseCommune(name));
  el(FIELD.EXCLUDED).value = (isExcluded ? list.filter(city => normaliseCommune(city) !== normaliseCommune(name)) : [...list, name]).join(', ');
  button.classList.toggle('is-excluded', !isExcluded);
  button.dataset.label = describeCommuneMarker(name, !isExcluded);
  button.setAttribute('aria-label', button.dataset.label);
}

// The circle follows the radius as it is typed; the communes follow once it settles.
el(FIELD.RADIUS).addEventListener('input', () => {
  const radiusKm = Number(fieldValue(FIELD.RADIUS));
  const zone = state.filterMap?.getSource('zone');
  if (!zone || !state.filterArea?.centre || !(radiusKm > 0)) return;
  zone.setData(buildCircle(state.filterArea.centre, radiusKm));
  state.filterMap.fitBounds(buildCircleBounds(state.filterArea.centre, radiusKm), {padding: MAP_FIT_PADDING_PX});
});
el(FIELD.RADIUS).addEventListener('change', openFilterAreaMap);
el(FIELD.CITIES).addEventListener('change', openFilterAreaMap);

// ── Search ────────────────────────────────────────────────────────────────────

// Non-blocking search: kick off the crawl, then poll. The POST returns instantly,
// so the request can never time out; results stream into the list as sources finish.
async function triggerSearch() {
  if (!state.filterId) return;
  setSearchButton(true);
  setStatus('Recherche en cours…');
  try {
    const res = await sendJson(API.SEARCH, HTTP.POST, {filter_id: state.filterId});
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
  } catch(e) {
    setStatus('Erreur au lancement de la recherche');
    setSearchButton(false);
    return;
  }
  state.searchStart = Date.now();
  pollSearch();
}

// The page's freshness is the last answer a source gave, never the browser's clock (W2).
function lastSearchedLabel() {
  return state.lastSearchedAt ? `Dernière recherche : ${relativeDate(state.lastSearchedAt)}` : 'Pas encore de recherche';
}

const SOURCE_PROGRESS_LABEL = Object.freeze({
  running: () => 'en cours',
  found: count => `${count} annonce${count > 1 ? 's' : ''}`,
  empty: () => 'aucune annonce',
  failed: () => 'échec',
});

// One tag per source while a search runs; it disappears with the search (W3).
function searchProgressHtml() {
  if (!state.searchSources.length) return '';
  const tags = state.searchSources.map(s =>
    `<span class="search-source is-${escHtml(s.state)}">${escHtml(s.source)} : ${(SOURCE_PROGRESS_LABEL[s.state] || SOURCE_PROGRESS_LABEL.running)(s.count)}</span>`);
  return `<div class="search-progress" aria-label="Avancement de la recherche">${tags.join('')}</div>`;
}

function setSearchButton(busy) {
  const btn = el(EL.SEARCH_BTN);
  btn.disabled = busy;
  btn.innerHTML = busy ? `${icon(ICON.WATCH)} Recherche…` : `${icon(ICON.SEARCH)} Rechercher`;
}

async function pollSearch() {
  clearTimeout(state.searchPollTimer);
  let status = SEARCH_STATUS.SEARCHING, newCount = 0;
  try {
    const res = await fetch(API.searchStatus(state.filterId));
    const payload = await res.json();
    status = payload.status; newCount = payload.new_count || 0;
    state.searchSources = payload.sources || [];
  } catch(e) { /* transient — keep polling */ }

  await loadListings(state.page, false, true);  // refresh from DB, no skeleton flash

  const elapsed = Date.now() - state.searchStart;
  const finished = status === SEARCH_STATUS.DONE || status === SEARCH_STATUS.IDLE;
  if (finished || elapsed > SEARCH_GIVEUP_MS) {
    setSearchButton(false);
    state.searchSources = [];
    if (status === SEARCH_STATUS.IDLE) setStatus('Recherche interrompue');
    else setStatus(newCount > 0 ? `${newCount} nouvelle${newCount > 1 ? 's' : ''} annonce${newCount > 1 ? 's' : ''}` : 'Aucune nouvelle annonce');
    await loadListings(state.page, true);  // final refresh, highlight new
    return;
  }
  state.searchPollTimer = setTimeout(pollSearch, SEARCH_POLL_MS);
}

// ── Watch ─────────────────────────────────────────────────────────────────────

async function toggleWatch() {
  if (state.watching) {
    await stopWatch();
  } else {
    await startWatch();
  }
}

async function startWatch() {
  if (!state.filterId) return;
  try {
    const res = await sendJson(API.WATCH_START, HTTP.POST, {filter_id: state.filterId});
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
  } catch(e) {
    showErrorToast(`Surveillance non lancée (${e.message}).`);
    return;
  }
  state.watching = true;
  updateWatchBtn();
  setStatus('Surveillance active');
  await triggerSearch();  // first pass immediately
  state.pollTimer = setInterval(pollApartments, WATCH_REFRESH_MS);
}

async function stopWatch() {
  if (state.pollTimer) clearInterval(state.pollTimer);
  state.pollTimer = null;
  if (state.filterId) {
    try {
      const res = await sendJson(API.WATCH_STOP, HTTP.POST, {filter_id: state.filterId});
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
    } catch(e) {
      showErrorToast(`Surveillance non arrêtée (${e.message}).`);
      return;
    }
  }
  state.watching = false;
  updateWatchBtn();
  setStatus('Surveillance arrêtée');
}

async function pollApartments() {
  if (!state.filterId || !state.watching) return;
  try {
    await loadListings(state.page, true);
  } catch(e) { /* silent */ }
}

function updateWatchBtn() {
  const btn = el(EL.WATCH_BTN);
  btn.className = state.watching ? 'btn btn-watch-on' : 'btn btn-watch-idle';
  btn.setAttribute('aria-pressed', String(state.watching));
  btn.innerHTML = state.watching ? `${icon(ICON.STOP)} Arrêter` : `${icon(ICON.WATCH)} Surveiller`;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function renderMain(html) {
  const main = el(EL.MAIN);
  main.innerHTML = html;
  main.setAttribute('aria-busy', 'false');
  arrangeMasonry();
}

function setStatus(message) {
  el(EL.STATUS).textContent = message;
}

function showToast(message) {
  const toast = el(EL.TOAST);
  toast.innerHTML = `${icon(ICON.CHECK)} ${escHtml(message)}`;
  revealToast(TOAST_MS);
}

// An error never wears the success check (W10): the alert icon, and the reason.
function showErrorToast(message) {
  el(EL.TOAST).innerHTML = `${icon(ICON.ALERT)} ${escHtml(message)}`;
  revealToast(UNDO_MS);
}

// A toast that offers to take the action back. `message` is already escaped HTML.
function showActionToast(message, actionLabel, onAction) {
  const toast = el(EL.TOAST);
  toast.innerHTML = `<span>${message}</span><button type="button" class="toast-action">${actionLabel}</button>`;
  toast.querySelector('button').addEventListener('click', () => {
    toast.classList.remove(CSS.SHOW);
    onAction();
  });
  revealToast(UNDO_MS);
}

function revealToast(durationMs) {
  const toast = el(EL.TOAST);
  clearTimeout(state.toastTimer);
  toast.classList.add(CSS.SHOW);
  state.toastTimer = setTimeout(() => toast.classList.remove(CSS.SHOW), durationMs);
}

function relativeDate(iso) {
  if (!iso) return '';
  const published = new Date(iso);
  const seconds = Math.floor((new Date() - published) / SECOND_MS);
  if (seconds < MINUTE_S) return "à l'instant";
  if (seconds < HOUR_S) return `il y a ${Math.floor(seconds / MINUTE_S)} min`;
  if (seconds < DAY_S) return `il y a ${Math.floor(seconds / HOUR_S)} h`;
  return published.toLocaleDateString('fr-FR', {day: '2-digit', month: '2-digit'});
}

// Escapes for *both* contexts this output lands in: HTML text, and an attribute
// value — including the single-quoted JS strings inside onclick handlers, which a
// bare apostrophe would close.
function escHtml(value) {
  if (!value) return '';
  return String(value).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;').replace(/`/g,'&#96;');
}

// A listing link comes from a third-party site: only http(s) may reach an href,
// or a `javascript:` URL would run on click, in this page's origin.
function safeUrl(value) {
  try {
    const parsed = new URL(String(value), window.location.origin);
    return WEB_PROTOCOLS.includes(parsed.protocol) ? parsed.href : '';
  } catch (e) {
    return '';
  }
}

// ── Filter modal ──────────────────────────────────────────────────────────────

const modal = el(EL.MODAL);
let focusBeforeModal = null;

function getSelectedDpe() {
  // Returns the exact set of checked ratings — empty array = no DPE filter.
  return [...document.querySelectorAll(`.${DPE_CHECKBOX}:checked`)].map(cb => cb.value);
}

function setDpeFromList(ratings) {
  const accepted = new Set(ratings || []);
  document.querySelectorAll(`.${DPE_CHECKBOX}`).forEach(cb => {
    cb.checked = accepted.has(cb.value);
  });
}

function clearFieldError(id) {
  el(id).removeAttribute('aria-invalid');
  el(id + ERROR_SUFFIX).classList.remove(CSS.SHOW);
}

function showFieldError(id) {
  const input = el(id);
  input.setAttribute('aria-invalid', 'true');
  el(id + ERROR_SUFFIX).classList.add(CSS.SHOW);
  input.focus();
}

const REQUIRED_FIELDS = [FIELD.NAME, FIELD.CITIES];
REQUIRED_FIELDS.forEach(id => el(id).addEventListener('input', () => clearFieldError(id)));

function triStateRadio(name, value) {
  return document.querySelector(`input[name="${name}"][value="${value}"]`);
}

// Yes / no / indifferent, read as the server's `parse_tri_state` expects it.
function readTriState(name) {
  if (triStateRadio(name, FURNISHED.YES).checked) return FURNISHED.YES;
  return triStateRadio(name, FURNISHED.NO).checked ? FURNISHED.NO : null;
}

function setTriState(name, value) {
  const answer = value === true ? FURNISHED.YES : (value === false ? FURNISHED.NO : FURNISHED.ANY);
  triStateRadio(name, answer).checked = true;
}

// The server's sentence under the field it refused, marked invalid (W10).
function showServerFieldError(id, message) {
  const input = el(id);
  let slot = el(id + ERROR_SUFFIX);
  if (!slot) {
    slot = Object.assign(document.createElement('span'), {className: 'form-error', id: id + ERROR_SUFFIX});
    input.insertAdjacentElement('afterend', slot);
    input.setAttribute('aria-describedby', [input.getAttribute('aria-describedby'), slot.id].filter(Boolean).join(' '));
  }
  slot.innerHTML = icon(ICON.ALERT, CSS.ICON_SM);
  slot.append(` ${message}`);
  slot.classList.add(CSS.SHOW);
  input.setAttribute('aria-invalid', 'true');
  input.closest('details')?.setAttribute('open', '');
  input.focus();
}

Object.values(FIELD_BY_CRITERION).forEach(id => el(id).addEventListener('input', () => {
  el(id).removeAttribute('aria-invalid');
  el(id + ERROR_SUFFIX)?.classList.remove(CSS.SHOW);
}));

function openFilterModal(filterId = null) {
  state.editingFilterId = filterId;
  focusBeforeModal = document.activeElement;
  el(EL.MODAL_TITLE).textContent = filterId ? 'Modifier le filtre' : 'Nouveau filtre de recherche';

  const f = filterId ? state.filters.find(x => x.id === filterId) : null;

  el(FIELD.NAME).value = f?.name || '';
  el(FIELD.CITIES).value = f?.cities?.join(', ') || '';
  el(FIELD.RADIUS).value = f?.radius_km ?? DEFAULT.RADIUS_KM;
  el(FIELD.EXCLUDED).value = f?.excluded_cities?.join(', ') || '';
  el(FIELD.MIN_PRICE).value = f?.min_price ?? '';
  el(FIELD.MAX_PRICE).value = f?.max_price ?? '';
  el(FIELD.MIN_SURFACE).value = f?.min_surface_m2 ?? '';
  el(FIELD.MIN_ROOMS).value = f?.min_rooms ?? '';
  el(FIELD.MAX_ROOMS).value = f?.max_rooms ?? '';
  el(FIELD.MAX_SURFACE).value = f?.max_surface_m2 ?? '';
  el(FIELD.MIN_PHOTOS).value = f?.min_photos || '';
  el(FIELD.MAX_AGE).value = f?.max_age_days ?? '';
  el(FIELD.EXCLUDED_ADVERTISERS).value = f?.excluded_advertisers?.join(', ') || '';
  setTriState(FURNISHED_RADIO, f?.furnished);
  setTriState(CHARGES_RADIO, f?.charges_included);
  setTriState(HEATING_RADIO, f?.collective_heating);
  // A filter that uses a hidden criterion opens with it in view, never behind a fold.
  const usesMoreCriteria = [f?.max_rooms, f?.max_surface_m2, f?.max_age_days, f?.charges_included, f?.collective_heating]
    .some(v => v !== null && v !== undefined) || f?.min_photos > 0 || f?.excluded_advertisers?.length > 0;
  el(MORE_CRITERIA).open = !!usesMoreCriteria;

  el(FIELD.EXCLUDE_GROUND).checked = f?.exclude_ground_floor || false;
  el(FIELD.EXCLUDE_FIRST).checked = f?.exclude_first_floor || false;
  el(FIELD.TOP_ONLY).checked = f?.top_floor_only || false;

  setDpeFromList(f?.accepted_dpe_ratings || []);

  el(FIELD.MAX_RESULTS).value = f?.max_results ?? DEFAULT.MAX_RESULTS;
  el(FIELD.NOTIFY_INTERVAL).value = f?.notification_interval_minutes ?? DEFAULT.NOTIFY_INTERVAL_MIN;
  el(FIELD.REFRESH_INTERVAL).value = f?.refresh_interval_minutes ?? DEFAULT.REFRESH_INTERVAL_MIN;

  REQUIRED_FIELDS.forEach(clearFieldError);
  Object.values(FIELD_BY_CRITERION).forEach(id => {
    el(id).removeAttribute('aria-invalid');
    el(id + ERROR_SUFFIX)?.classList.remove(CSS.SHOW);
  });
  modal.style.display = MODAL_VISIBLE;
  el(FIELD.NAME).focus();
  openFilterAreaMap();
}

function closeFilterModal() {
  modal.style.display = MODAL_HIDDEN;
  state.filterMap?.remove();
  state.filterMap = null;
  if (focusBeforeModal) focusBeforeModal.focus();
}

// Escape closes a map popup before anything else: the modal or the reason bar behind it
// stays open, so one key undoes one thing.
document.addEventListener('keydown', e => {
  if (e.key !== KEY.CANCEL || !state.mapPopup) return;
  e.preventDefault();
  e.stopImmediatePropagation();
  state.mapPopup.remove();
}, true);

// Overlay click closes; Escape closes; Tab cycles inside the dialog.
modal.addEventListener('click', e => {
  if (e.target === e.currentTarget) closeFilterModal();
});

modal.addEventListener('keydown', e => {
  if (e.key === 'Escape') { closeFilterModal(); return; }
  if (e.key !== 'Tab') return;
  const items = [...modal.querySelectorAll(FOCUSABLE)];
  if (!items.length) return;
  const first = items[0], last = items[items.length - 1];
  if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
});

function filterPayload() {
  return {
    name: fieldValue(FIELD.NAME),
    cities: fieldValue(FIELD.CITIES),
    radius_km: parseFloat(el(FIELD.RADIUS).value) || DEFAULT.RADIUS_KM,
    excluded_cities: fieldValue(FIELD.EXCLUDED),
    min_price: el(FIELD.MIN_PRICE).value || null,
    max_price: el(FIELD.MAX_PRICE).value || null,
    min_surface_m2: el(FIELD.MIN_SURFACE).value || null,
    min_rooms: el(FIELD.MIN_ROOMS).value || null,
    max_rooms: el(FIELD.MAX_ROOMS).value || null,
    max_surface_m2: el(FIELD.MAX_SURFACE).value || null,
    furnished: readTriState(FURNISHED_RADIO),
    charges_included: readTriState(CHARGES_RADIO),
    collective_heating: readTriState(HEATING_RADIO),
    min_photos: el(FIELD.MIN_PHOTOS).value || null,
    max_age_days: el(FIELD.MAX_AGE).value || null,
    excluded_advertisers: fieldValue(FIELD.EXCLUDED_ADVERTISERS),
    exclude_ground_floor: isChecked(FIELD.EXCLUDE_GROUND),
    exclude_first_floor: isChecked(FIELD.EXCLUDE_FIRST),
    top_floor_only: isChecked(FIELD.TOP_ONLY),
    accepted_dpe_ratings: getSelectedDpe(),
    max_results: parseInt(el(FIELD.MAX_RESULTS).value) || DEFAULT.MAX_RESULTS,
    notification_interval_minutes: parseInt(el(FIELD.NOTIFY_INTERVAL).value) || DEFAULT.NOTIFY_INTERVAL_MIN,
    refresh_interval_minutes: parseInt(el(FIELD.REFRESH_INTERVAL).value) || DEFAULT.REFRESH_INTERVAL_MIN,
  };
}

async function saveFilter() {
  if (!fieldValue(FIELD.NAME)) { showFieldError(FIELD.NAME); return; }
  if (!fieldValue(FIELD.CITIES)) { showFieldError(FIELD.CITIES); return; }

  const isEdit = !!state.editingFilterId;
  const url = isEdit ? API.filter(state.editingFilterId) : API.FILTERS;

  try {
    const res = await sendJson(url, isEdit ? HTTP.PUT : HTTP.POST, filterPayload());
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const field = FIELD_BY_CRITERION[err.detail?.field];
      if (field) showServerFieldError(field, err.detail.message);
      else showErrorToast(`Filtre non enregistré (${typeof err.detail === 'string' ? err.detail : res.status}).`);
      return;
    }
    const saved = await res.json();
    closeFilterModal();
    if (isEdit) {
      state.filters = state.filters.map(f => f.id === saved.id ? saved : f);
    } else {
      state.filters.push(saved);
    }
    renderSidebar();
    await selectFilter(saved.id);
    showToast(isEdit ? 'Filtre mis à jour' : 'Filtre créé');
  } catch(e) {
    showErrorToast(`Filtre non enregistré (${e.message}).`);
  }
}

async function deleteFilter(id) {
  const target = state.filters.find(f => f.id === id);
  if (!confirm(`Supprimer le filtre « ${target ? target.name : id} » ?`)) return;
  try {
    const res = await fetch(API.filter(id), {method: HTTP.DELETE});
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    state.filters = state.filters.filter(f => f.id !== id);
    delete state.counts[id];
    if (state.filterId === id) {
      state.filterId = state.filters.length ? state.filters[0].id : null;
    }
    renderSidebar();
    if (state.filterId) {
      await selectFilter(state.filterId);
    } else {
      showListingsView();
      renderMain(noFilterState());
    }
    showToast('Filtre supprimé');
  } catch(e) {
    showErrorToast(`Suppression impossible (${e.message}) : le filtre est conservé.`);
  }
}
