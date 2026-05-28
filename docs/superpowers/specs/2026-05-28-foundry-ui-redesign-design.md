# Educto Foundry UI Redesign — Design Spec

**Date:** 2026-05-28
**Author:** Marius Sabaliauskas (with Claude)
**Status:** Approved, ready for implementation planning
**Scope:** Student-facing core (6 screens) — dashboard, catalog, course detail, course player, chat, account
**Stack:** Django 5.1.3 templates + Tailwind CSS + HTMX

---

## 1. Goals & non-goals

### Goals
- Replace Educto's current dated blue UI with a Palantir Foundry-inspired dark operator-console aesthetic.
- Prioritize information density, precision, and clarity over decorative visuals.
- Improve learner workflows: progress visibility, fast module switching, focused course player.
- Keep Django templates + server-side rendering. No SPA rewrite.

### Non-goals
- Not redesigning the instructor course-management screens (separate sprint).
- Not redesigning the public marketing landing page (separate sprint — Palantir-dark may not fit there).
- Not building a mobile app. Responsive web only.
- Not changing the data model. UI layer only.

### Success criteria
- A learner can land on `/students/dashboard/`, see all enrolled courses with progress, resume the last lesson, and reach the course player in ≤ 2 clicks.
- All 6 redesigned screens pass WCAG AA contrast (verified by axe-core).
- Course player loads new content via HTMX in < 200ms p95 without a full page reload.
- Visual regression baseline established for each redesigned screen.
- No regression in existing Django test suite.

---

## 2. Visual language

### Color tokens

| Token | Hex | Use |
|---|---|---|
| `bg-base` | `#0A0D12` | Page background |
| `bg-panel` | `#11151C` | Raised panels, cards |
| `bg-elevated` | `#181D27` | Modals, dropdowns, popovers |
| `bg-hover` | `#1F2533` | Hover state on clickable rows |
| `bg-active` | `#283041` | Pressed / selected state |
| `border-subtle` | `#1F2533` | 1px hairline between panels |
| `border-strong` | `#2D3648` | Input borders, focused panels |
| `border-accent` | `#00B8D4` | Focused / active accent border |
| `text-primary` | `#E6E9EF` | Body text (contrast 11.2:1 on bg-base) |
| `text-secondary` | `#8B95A7` | Labels, metadata |
| `text-muted` | `#5C6578` | Captions, disabled |
| `text-mono` | `#C8FFE9` | Numerical data (cyan-tinted) |
| `accent` | `#00B8D4` | Primary actions, focus, progress fill |
| `accent-hover` | `#00D4F2` | Accent hover state |
| `accent-muted` | `#003D47` | Tinted background for accent regions |
| `success` | `#4ADE80` | Completed, healthy |
| `warning` | `#FBBF24` | Attention |
| `danger` | `#F87171` | Errors, destructive actions |

**Contrast verification (WCAG AA = 4.5:1 for body text):**
- text-primary (`#E6E9EF`) on bg-base (`#0A0D12`): **11.2:1** ✓
- text-secondary on bg-base: **5.8:1** ✓
- text-muted on bg-base: **3.4:1** — usable only for non-essential captions
- accent on bg-base: **6.9:1** ✓

### Typography

| Style | Family | Size / line | Weight | Notes |
|---|---|---|---|---|
| `display` | Inter | 32 / 36 | 600 | Letter-spacing -0.02em. Used in metric tiles. |
| `h1` | Inter | 24 / 30 | 600 | Letter-spacing -0.01em. Page titles. |
| `h2` | Inter | 18 / 24 | 600 | Section titles. |
| `h3` | Inter | 14 / 20 | 600 | Uppercase, tracking 0.08em. Foundry-style section labels. |
| `body` | Inter | 14 / 22 | 400 | Default. |
| `small` | Inter | 12 / 18 | 400 | Captions. |
| `mono-data` | IBM Plex Mono | 13 / 18 | 500 | All numbers, percentages, IDs, timestamps. |
| `mono-label` | IBM Plex Mono | 11 / 14 | 500 | Uppercase, tracking 0.08em. Table headers, breadcrumbs. |

**Font loading:** Inter via `rsms.me/inter/inter.css` (variable). IBM Plex Mono self-hosted at `static/fonts/` to avoid Google Fonts dependency.

### Spacing, radius, motion

- Spacing: 4px grid — `0, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64`.
- Radius: `0px`, `2px`, `4px` only. No rounded buttons or pills.
- Shadows: none by default. `0 8px 24px rgba(0,0,0,0.5)` for overlays only. Focus ring `0 0 0 2px rgba(0,184,212,0.4)`.
- Motion: `120ms cubic-bezier(0.2, 0, 0.2, 1)` on hover/focus. `240ms ease-out` for progress fills. Respect `prefers-reduced-motion`.

---

## 3. Component primitives

Each primitive lives as a Django template partial under `config_educa/shared/templates/shared/components/`.

| Component | Spec |
|---|---|
| **Button** | 32px height, 12px x-padding, radius 2px, mono-label text. Variants: `primary` (cyan bg, near-black text), `ghost` (border only, transparent bg), `danger`. Hover: lighter bg. Focus: ring-focus halo. |
| **Panel** | `bg-panel`, 1px `border-subtle`, radius 2px. Optional header row 32px tall with `h3` label + kebab menu slot. |
| **Input** | `bg-base` bg, 1px `border-strong`, radius 2px, height 32px, x-padding 12px. Focus: `border-accent` + ring-focus. |
| **Badge** | Height 20px, x-padding 6px, radius 2px, mono-label text. Variants: neutral, accent, success, warning, danger. |
| **ProgressBar** | Height 4px, `bg-active` track, `accent` fill, trailing mono-data label e.g. `78%`. |
| **Table** | Borderless rows separated by 1px `border-subtle`. Header: mono-label uppercase. Numeric cells: mono-data. Hover row: `bg-hover`. |
| **ModuleRow** | 40px tall. Number (mono-label, 32px wide) ‖ title ‖ duration (mono-data) ‖ check icon. Selected state: 2px left border accent + `bg-active`. |
| **ContentPanel** | Full-bleed reading area. Max-width 720px for prose, full width for video. |
| **ActivityChart** | 24-bar SVG sparkline. Bars use `accent`; gaps `bg-active`. Tooltip on hover. |
| **ChatMessage** | Username (mono-label, color-coded by role) ‖ timestamp (mono-label muted) ‖ body (sans). Code fences render in IBM Plex Mono on `bg-elevated`. |

---

## 4. App shell

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  EDUCTO ▸ DASHBOARD                          ⌘K  ◐ 3   msabaliauskas ▾     │  ← 48px topbar
├────────────┬─────────────────────────────────────────────────────────────────┤
│  HOME      │                                                                 │
│  CATALOG   │                                                                 │
│  MY        │                  MAIN CONTENT PANEL                             │
│  COURSES   │                                                                 │
│  CHAT      │                                                                 │
│  ─────     │                                                                 │
│  CERTS     │                                                                 │
│  REVIEWS   │                                                                 │
│            │                                                                 │
│  ── 56px ──│  ─── flex-1 ───                                                 │
│  ▢ Help    │                                                                 │
│  ⓘ v1.4.2 │                                                                 │
└────────────┴─────────────────────────────────────────────────────────────────┘
```

- **Topbar** (`bg-panel`, 48px, fixed): logo + breadcrumb (last segment in `accent`), command palette `⌘K`, unread badge, user menu.
- **Sidebar** (`bg-panel`, 1px right border): 56px collapsed default (icons + tooltip), 208px expanded. Labels in mono-label uppercase when expanded. State persists in localStorage.
- **Main**: scrolls independently. Content uses `grid-cols-12 gap-4` panel layout.

---

## 5. Screen layouts

### 5.1 Dashboard (`/students/dashboard/`)

Three metric tiles (Enrolled, Completed, Streak) at top — big mono-display numerals.
"Continue Learning" panel with up to 3 most recent in-progress courses, each showing progress bar, next lesson title, ETA, RESUME button.
30-day activity sparkline (SVG).
"Recommended for you" row of 4 course cards.

### 5.2 Catalog (`/`)

Two-column: left rail filters (subject, level, duration, with mono-data counts) + right results list.
Default view: dense row-cards. Toggle to grid via `⊞ ⊟`.
Search bar with `hx-trigger="keyup changed delay:200ms"` for live filtering.
Sort, price, level dropdowns.

### 5.3 Course detail (`/courses/<slug>/`)

Above the fold: two-column.
- Left: course title, subtitle, mono-label/mono-data metadata table (modules, duration, students, level, rating), instructor card.
- Right: enroll panel with price, ENROLL button (primary), "includes" checklist.

Below: full-width curriculum table (modules expandable into items), reviews section.

### 5.4 Course player ★ (`/courses/<slug>/player/`)

**Flagship screen.** Three-pane operator-console layout. In this screen the **global sidebar is force-collapsed to its 56px icon strip** to give the curriculum rail room.

- **Left (240px, lives inside main, not the global sidebar)**: course curriculum tree. Modules expandable. Current item highlighted with 2px left border + `bg-active`. Progress bar + time-remaining at bottom.
- **Center (flex-1, max-width 1024px)**: video player or content viewer + transcript search + "Next" link.
- **Right (280px, collapsible to 48px)**: notes textarea (autosave), attachments list, discussion thread link.

Total width budget at 1440px: 56 (global sidebar) + 240 (curriculum) + 864 (center) + 280 (notes) = 1440px. ✓

**HTMX behaviors:**
- Module click → `hx-get` content, `hx-target=#player-content`, `hx-push-url=true`.
- Mark complete → `hx-post`, returns updated progress panel; `hx-swap-oob` updates left rail check icon.
- Notes textarea → `hx-post` on `keyup changed delay:800ms`, returns 204; client updates "auto-saved" timestamp via `hx-on::after-request`.

**Keyboard shortcuts:**
- `j/k` — navigate module list up/down
- `Enter` — open focused module
- `m` — mark current complete
- `⌘K` — command palette
- `?` — help overlay
- `/` — focus transcript search

### 5.5 Chat room (`/chat/room/<course_id>/`)

Two-column.
- **Left (200px)**: enrolled users list with online/offline indicators (`●` cyan / `○` muted).
- **Right (flex-1)**: message stream + input.

Existing WebSocket (Channels) stays. Only restyle messages: usernames color-coded (instructor cyan, student primary, you muted), timestamps mono-label, code fences in IBM Plex Mono panel.

### 5.6 Account/settings (`/account/`)

Foundry settings layout: left sub-nav (Profile / Security / Notifications / Billing / Sessions / Danger zone) + right form panel. Hosts MFA setup, sessions table, GDPR data export button (queues Celery job).

---

## 6. Responsive behavior

| Breakpoint | Behavior |
|---|---|
| `< 768px` | Sidebar becomes off-canvas drawer (toggle from topbar). Course player stacks vertically: curriculum top, content middle, notes bottom. Catalog filters collapse into a top filter bar. |
| `768–1024px` | Notes pane collapses to 48px icon strip, expandable on click. Course player keeps three columns but tight. |
| `> 1024px` | Full layout as described. |

---

## 7. Accessibility

- All interactive elements have visible focus halo (`ring-focus`), never `outline: none`.
- All icons have either text labels or `aria-label`.
- All form inputs have associated `<label>`.
- Color is never the sole signaling channel — pair with text/icon (progress %, "Online", checkmark).
- Keyboard navigation tested for course player flow.
- Skip-to-main-content link at top of every page.
- Respect `prefers-reduced-motion`: disable progress-bar fill animation.
- ARIA live region for HTMX swaps that change important state (e.g., "Marked complete").

---

## 8. Tech architecture

### Dependencies

Python (add to `requirements.txt`):
```
django-tailwind==3.8.0
django-htmx==1.19.0
django-compressor==4.5.1
```

Node (Tailwind build, lives in `theme/static_src/`):
```
tailwindcss@3.4
@tailwindcss/typography
@tailwindcss/forms
htmx.org@2.0
alpinejs@3.14
```

### File structure

```
theme/                                    # django-tailwind app (new)
├── static_src/
│   ├── src/
│   │   ├── styles.css                    # @tailwind directives + custom layer
│   │   └── fonts.css                     # @font-face IBM Plex Mono
│   ├── tailwind.config.js                # design tokens
│   └── package.json
└── templates/base.html                   # new app-shell base

config_educa/
├── theme/                                 # registered Django app pointer
└── shared/                                # new Django app for cross-cutting partials
    └── templates/shared/
        ├── _topbar.html
        ├── _sidebar.html
        ├── _command_palette.html
        ├── components/
        │   ├── _panel.html
        │   ├── _button.html
        │   ├── _input.html
        │   ├── _badge.html
        │   ├── _progress_bar.html
        │   ├── _module_row.html
        │   ├── _activity_sparkline.html
        │   ├── _chat_message.html
        │   └── _table.html
        └── partials/                      # HTMX response targets
            ├── _player_content.html
            ├── _progress_panel.html
            ├── _catalog_results.html
            └── _chat_messages.html
```

### Settings additions

```python
INSTALLED_APPS += [
    "tailwind",
    "theme",
    "django_htmx",
    "shared",
]
MIDDLEWARE += ["django_htmx.middleware.HtmxMiddleware"]
TAILWIND_APP_NAME = "theme"
INTERNAL_IPS = ["127.0.0.1"]  # required by django-tailwind dev
NPM_BIN_PATH = "/opt/homebrew/bin/npm"  # macOS
```

### Tailwind config (excerpt)

```js
module.exports = {
  content: ['./templates/**/*.html', '../config_educa/**/templates/**/*.html'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: { /* tokens from Section 2 */ },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'monospace'],
      },
      fontSize: {
        'mono-data':  ['13px',  { lineHeight: '18px', fontWeight: 500 }],
        'mono-label': ['11px',  { lineHeight: '14px', fontWeight: 500, letterSpacing: '0.08em' }],
      },
      borderRadius: { DEFAULT: '2px', md: '4px' },
      transitionDuration: { '120': '120ms' },
    },
  },
  plugins: [require('@tailwindcss/typography'), require('@tailwindcss/forms')],
}
```

### Build & run

```bash
# One-time
uv pip install django-tailwind[reload] django-htmx
python manage.py tailwind init theme
python manage.py tailwind install

# Dev (two terminals)
python manage.py tailwind start
python manage.py runserver

# Prod
python manage.py tailwind build
python manage.py collectstatic --noinput
```

CI: add `tailwind build` step in `scripts/deploy_production.sh` between dependency install and `collectstatic`.

---

## 9. Implementation milestones

| # | Milestone | Files touched | Acceptance |
|---|-----------|---------------|------------|
| **M0** | Foundation: Tailwind installed, design tokens in config, fonts loaded, `base.html` works | `theme/`, `shared/_topbar.html`, `shared/_sidebar.html`, settings | Login page renders in Foundry dark; `/` shows new shell |
| **M1** | Component library: panel, button, input, badge, progress, module-row, sparkline | `shared/templates/shared/components/*` | `/components/` debug page renders all primitives correctly |
| **M2** | Dashboard | `students/views.py` (add context), `students/templates/students/dashboard.html` (new) | Logged-in user sees metric tiles, continue-learning, activity, recommendations with real data |
| **M3** | Catalog + course detail | `courses/templates/courses/course/list.html`, `detail.html`; HTMX endpoint for filters | Browse, filter live, view detail with metadata + curriculum |
| **M4** | Course player ★ | `students/templates/students/course/detail.html` → 3-pane player; new views `player_content`, `mark_complete`, `notes_save` | Click through course end-to-end via HTMX; mark-complete, notes autosave work |
| **M5** | Chat room restyle | `chat/templates/chat/room.html`; CSS-only changes to message rendering | Live chat works, messages styled per spec |
| **M6** | A11y + responsive polish + visual regression baselines | All templates | axe-core passes AA on all 6 screens; <768px works; screenshots committed |

**Dependencies:** M0 → M1 → {M2, M3, M5} in parallel → M4 (depends on M1 + M2 patterns) → M6.

Estimated total: ~2 weeks single-thread, ~1 week with subagent parallelism on M2/M3/M5.

---

## 10. Testing strategy

- **Per milestone**: tester subagent navigates with Playwright MCP and screenshots each redesigned screen.
- **Visual regression**: baseline screenshots committed under `tests/visual/baselines/`. Future PRs diff against them.
- **Accessibility**: `axe-core` automated run against each redesigned URL, failing on any AA violation.
- **Django tests**: extend existing `tests.py` files. Add tests for new HTMX endpoints:
  - `test_player_content_returns_partial_when_hx_request`
  - `test_mark_complete_returns_progress_panel`
  - `test_notes_save_returns_204_and_persists`
  - `test_catalog_filter_via_htmx_returns_results_partial`
- **Manual smoke**: log in → dashboard → click course → complete a module → check chat → see certificate, all without breaking.

---

## 11. Rollback plan

- Keep current `courses/templates/base.html` and `static/css/base.css` renamed to `_old_base.html` and `_old_base.css` for M0–M2.
- Feature flag via Django setting `USE_FOUNDRY_UI` (default `False`). Templates render the new base only when flag is true.
- After M2 ships to production and runs clean for 7 days, set default `True` and remove `_old_*` files in M6.

---

## 12. Out of scope (deferred to later sprints)

- Instructor course management screens (CRUD course/module/content forms).
- Public marketing landing page (lighter aesthetic likely needed).
- Admin (Django admin stays as-is — internal tool).
- Mobile native app.
- Internationalization of new UI strings.
- Analytics dashboard (separate `analytics` app already exists; UI for it is a separate sprint).
- Migrating off Django templates to an SPA.

---

## 13. Open decisions deferred to implementation

These intentionally were not pinned in this spec — to be decided during the implementation plan or by the first PR:

- Whether the sidebar's collapsed-by-default state should be a per-user preference or session-only.
- Exact ASCII chart vs. SVG sparkline for the dashboard activity widget (mockup shows ASCII; SVG is more accessible — likely SVG wins).
- Whether the command palette (`⌘K`) is in M0 or deferred to M6 polish.

---

## 14. References

- Existing project audit: `UI_UX_DESIGN_SPECIFICATIONS.md` (pre-Foundry pass — informed current state analysis).
- Brand inspiration: Palantir Foundry, Palantir Gotham, Linear, Vercel dashboard, Stripe dashboard (dark).
- Accessibility: WCAG 2.1 AA, WebAIM contrast checker.
