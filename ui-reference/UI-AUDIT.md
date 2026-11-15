# UI port review

This is a code-level review of the port. The supplied Figma archive did not include page screenshots, so visual comparison at 1440px and 390px remains a manual review item.

## Route mapping

| Figma view | Django route | Data and behavior |
| --- | --- | --- |
| Today | `/status/` and `/` | Status engine, saved readings, selected date, region detail HTMX partial |
| Check-in | `/checkin/` | `CheckInForm`, environment-driven equipment fields, database write, existing error associations |
| Trends | `/trend/<indicator_key>/` | Engine readings, baseline, sourced limits, uncertain Plotly forecast |
| Relay | `/relay/` | Database-backed open/resolved items; explicit download or copy actions |
| Progress | `/progress/` | Check-in and action participation only |

## Port decisions

- Removed mock scenario readings, demo-specific source wording, hard-coded chart series, and browser `localStorage` behavior from the product UI. The reference `App.tsx` remains unserved and unimported.
- Kept the server-rendered SVG body map and added a 3D progressive enhancement. The local model and WebGL canvas replace the SVG only after both initialize; failures leave the SVG in place. Region buttons stay visible and usable with JavaScript off, while mouse, keyboard, labels, and 3D hit markers use the existing region detail endpoint.
- Kept the context card tied to the latest stored check-in and `data/environments.json`. With no stored environment, it reports that the environment has not been recorded.
- Kept the safety footer, local-data message, simulated badge, status text and symbols, source-backed guidance, and explicit relay export behavior.
- Bundled three.js 0.187.0 into `core/static/vendor/bodymap3d.js`; the Django runtime does not need Node. Its MIT license is included beside the bundle. The source GLB is in `core/static/core/models/`.

## Responsive and accessibility review

- Navigation collapses behind an `aria-expanded` / `aria-controls` menu button at the mobile breakpoint.
- The region detail area is a polite live region. Region buttons have names containing the region, severity word, and severity value.
- 3D marker selections update the same live announcement and trigger the corresponding region button request. Reduced-motion preference disables OrbitControls easing.
- Form labels and existing `aria-describedby` validation links are preserved.
- Layout breakpoints are defined at 1050px, 760px, and 480px. Check labels, chart legends, and cards for wrapping at 390px during the manual visual pass.
- Automated CSS checks require 12px minimum type; footer text is 14px.

## Manual visual pass still needed

Capture `/status/` at 1440px and 390px for calm, drift, and fever-blackout data. Check label wrapping, map controls, chart readability, and the blackout banner. Repeat on pages `/checkin/`, `/trend/resting_hr/`, `/relay/`, and `/progress/` before calling the visual match complete.
