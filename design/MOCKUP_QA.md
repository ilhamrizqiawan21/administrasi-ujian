# Mockup verification

Browser Chromium via Playwright, local HTML loaded into browser context (no remote assets). All 20 routes rendered without page errors. Captured 25 screen/state PNG and 12 individual group PNG. Visually inspected dashboard light/dark, seating, document preview. Smoke tested: opening Add Student modal, Escape dismissal, search filtering to one record, delete confirm/cancel, seat selection/swap, theme toggle. Screenshots 1440×900, compact 1024×768 and narrow 720×900. Native file navigation was blocked by this environment; HTML uses no external dependencies and should be opened as a normal local file in the user's browser, or via a local static server if file restrictions apply.

Not tested: real backend, production persistence, schedule solver, export, installer, Windows WebView2, contrast audit of every state, all keyboard/DPI paths. This is design review only. All implementation backlog remains TODO.
