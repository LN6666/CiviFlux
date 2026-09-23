# Embedding CiviFlux

Build with `npm ci && npm run build`; the Python local API serves `dist/` on the same origin. The reference host is `/`, and `/headless.html` is a standalone vanilla HTML host using the same `plugin.js` and shared component chunk. The latter has no MapLibre dependency. Both run real API workflows; neither provides mock analysis results.

```html
<script type="module" src="/plugin.js"></script>
<urban-impact-panel></urban-impact-panel>
```

Serve the component's `assets/` directory alongside `plugin.js`. The host must expose the same-origin `/api/v1` API. Session tokens remain in component memory; model credentials remain on the backend. Shadow DOM isolates panel styles. The component emits `scenario-change`, `run-complete`, `entity-select` and `error` events with `bubbles` and `composed` enabled. Removing the component aborts requests, stops polling and unsubscribes map listeners; the host owns the map lifecycle and calls its adapter's `dispose()`.

For a map host, set `panel.mapAdapter` to an implementation of `src/map-adapter.ts`: local GeoJSON data, selection, highlights, perimeter, fit extent and an optional polygon-drawing method. MapLibre is entirely in the host adapter. No tiles, geocoding, remote fonts, telemetry or source URLs are loaded. User-supplied data is rendered as text; no HTML interpolation is accepted.

`npm test` starts an isolated real Python backend on `127.0.0.1:8766`, creates actual scenario Actions, runs routing/PPR, reads Object View and downloads evidence ZIPs in both hosts. It also checks fire boundary confirmation, invalid times, Qwen API unavailability and zero external HTTP requests. The test server forcibly disables paid API egress irrespective of `.env` credentials. Chromium is a separate Playwright test dependency. Browser artifacts are written under `test-results/`; screenshots are inspection evidence, not scientific validation.

The UI labels current/synthetic data, missing/unreachable physical metrics, generated semantic attention, assumptions and simulation separately. Selected fire polygons are user-confirmed what-if boundaries and are never described as certified safety perimeters. Controls submit typed scenario Actions; no graph mutation endpoint exists.
