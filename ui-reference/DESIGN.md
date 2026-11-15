# AstroPulse UI reference

The original Figma implementation is kept here for visual reference only. Django templates and static assets do not import or serve these files.

## Visual direction

- Dark mission navigation around a light, low-noise content surface.
- Strong page titles, short context labels, clear cards, and generous separation between tasks.
- Use the system font stack; no web fonts.
- Every status uses a shape, a plain-language label, and a matching color.
- Keep SIMULATED visible wherever demonstration records appear.
- Keep the body map, forms, trend descriptions, relay actions, and privacy information understandable without relying on color.

## Tokens from `index.css`

| Token group | Values |
| --- | --- |
| Type | 12, 14, 16, 18, 20, 24, 32, 40, 64px; 16px base line height 1.5 |
| Spacing | 4px steps, including 4, 8, 12, 16, 20, 24, 28, 32, 40, 48px |
| Corners | 8px and 12px; pills may be fully rounded |
| Motion | 160ms for interface transitions; respect reduced-motion preference |
| Surfaces | base `#f5f7f6`, panel `#ffffff`, nav `#0e1412`, topbar `#0d1210`, dark `#121b1e` |
| Borders and ink | line `#cfd6d2`, strong line `#bec8c4`, ink `#121b18`, soft ink `#3c4e48`, muted `#5f706b` |
| Brand | `#0f766e`; hover `#0d5f57`; soft `#eef6f3`; text `#0c4a45` |
| Normal | `#15805d` / `#e9f6f2` |
| Watch | `#926d0e` / `#fbf6dc` |
| Concern | `#b45309` / `#fdf0e3` |
| Contact ground | `#b3433d` / `#fdeae6` |
| Not enough data | `#6b7a75` / `#eef2f1` |

The Django implementation maps the supplied values into `core/static/core/app.css`. Server data and behavior continue to come from Django, the database, the engine, and `data/*.json`.
