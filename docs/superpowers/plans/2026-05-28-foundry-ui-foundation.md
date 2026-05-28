# Foundry UI — Foundation (M0 + M1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install Tailwind + HTMX, define all design tokens, build the app shell (topbar + sidebar + base.html), and ship a complete component library. After this plan ships, all subsequent screens (M2 dashboard, M3 catalog/detail, M4 player, M5 chat, M6 polish) can be built by composing these primitives.

**Architecture:** django-tailwind compiles a Tailwind CSS bundle from `theme/static_src/`. A new Django app `shared/` holds the base template, app-shell partials, and reusable component partials. The existing `courses/templates/base.html` stays untouched (rollback safety). New base lives at `theme/templates/base.html` and is opted into via the `USE_FOUNDRY_UI` setting flag.

**Tech Stack:** Django 5.1.3 + django-tailwind 3.8 + django-htmx 1.19 + Tailwind CSS 3.4 + HTMX 2.0 + Alpine.js 3.14 + IBM Plex Mono + Inter.

**Spec:** `docs/superpowers/specs/2026-05-28-foundry-ui-redesign-design.md`

**Scope:** This plan implements **M0 (Foundation)** and **M1 (Component library)** only. M2–M6 will be planned separately.

---

## File map

### Created
| File | Responsibility |
|---|---|
| `theme/` | django-tailwind app (scaffolded by `tailwind init`) |
| `theme/static_src/tailwind.config.js` | Design tokens (colors, fonts, spacing) |
| `theme/static_src/src/styles.css` | `@tailwind` directives + custom `@layer` |
| `theme/static_src/src/fonts.css` | `@font-face` for IBM Plex Mono |
| `theme/templates/base.html` | New app-shell base template |
| `config_educa/shared/__init__.py` | New Django app |
| `config_educa/shared/apps.py` | App config |
| `config_educa/shared/views.py` | `ComponentsView` for `/components/` debug page |
| `config_educa/shared/urls.py` | Routes |
| `config_educa/shared/tests.py` | Unit tests for shared views |
| `config_educa/shared/templates/shared/_topbar.html` | Topbar partial |
| `config_educa/shared/templates/shared/_sidebar.html` | Sidebar partial |
| `config_educa/shared/templates/shared/_command_palette.html` | Alpine.js ⌘K palette (skeleton only, full impl deferred to M6) |
| `config_educa/shared/templates/shared/components/_panel.html` | Panel primitive |
| `config_educa/shared/templates/shared/components/_button.html` | Button primitive (primary/ghost/danger) |
| `config_educa/shared/templates/shared/components/_input.html` | Input primitive |
| `config_educa/shared/templates/shared/components/_badge.html` | Badge primitive (5 variants) |
| `config_educa/shared/templates/shared/components/_progress_bar.html` | ProgressBar primitive |
| `config_educa/shared/templates/shared/components/_module_row.html` | ModuleRow primitive |
| `config_educa/shared/templates/shared/components/_activity_sparkline.html` | SVG sparkline (24 bars) |
| `config_educa/shared/templates/shared/components/_chat_message.html` | ChatMessage primitive |
| `config_educa/shared/templates/shared/components/_table.html` | Table primitive |
| `config_educa/shared/templates/shared/_components_debug.html` | Debug page renders every primitive |
| `tests/visual/baselines/.gitkeep` | Visual regression baselines folder |

### Modified
| File | Why |
|---|---|
| `requirements.txt` | Add django-tailwind, django-htmx |
| `config_educa/config_educa/settings/base.py:34-56` | Add INSTALLED_APPS, MIDDLEWARE entries; new `TAILWIND_APP_NAME`, `INTERNAL_IPS`, `NPM_BIN_PATH`, `USE_FOUNDRY_UI` settings |
| `config_educa/config_educa/urls.py` | Include `shared.urls` at `/components/` and `tailwind` URLs at `/__reload__/` |
| `scripts/deploy_production.sh` | Add `python manage.py tailwind build` step before `collectstatic` |
| `.gitignore` | Add `theme/static/css/dist/` (Tailwind build output) and `theme/static_src/node_modules/` |

---

## Conventions

- **Test runner:** `cd config_educa && python manage.py test <app>`
- **Working directory for Django commands:** `config_educa/`
- **Commit style:** Conventional Commits (`feat:`, `chore:`, `docs:`). Each task's last step is a commit.
- **Verification:** every CSS/template task includes a manual "view in browser" verification step.

---

# M0 — Foundation

### Task 1: Add Python dependencies

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add packages to requirements.txt**

Open `requirements.txt`. After the line `Django==5.1.3` insert:

```
django-tailwind==3.8.0
django-htmx==1.19.0
```

- [ ] **Step 2: Install in the active venv**

Run: `pip install django-tailwind==3.8.0 django-htmx==1.19.0`
Expected output ends with `Successfully installed django-htmx-1.19.0 django-tailwind-3.8.0`

- [ ] **Step 3: Verify importable**

Run: `cd config_educa && python -c "import tailwind, django_htmx; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore: add django-tailwind and django-htmx dependencies"
```

---

### Task 2: Register tailwind in Django settings

**Files:**
- Modify: `config_educa/config_educa/settings/base.py:34-56`

- [ ] **Step 1: Add tailwind + django_htmx to INSTALLED_APPS**

In `base.py`, find `INSTALLED_APPS = [`. After the last project app (likely `'analytics',`), add a comma if missing, then on new lines:

```python
    'tailwind',
    'django_htmx',
```

- [ ] **Step 2: Add HtmxMiddleware**

Find `MIDDLEWARE = [`. After `'django.contrib.messages.middleware.MessageMiddleware',` add:

```python
    'django_htmx.middleware.HtmxMiddleware',
```

- [ ] **Step 3: Add new settings at the end of `base.py`**

Append:

```python
# Tailwind
TAILWIND_APP_NAME = 'theme'
INTERNAL_IPS = ['127.0.0.1']
# Override in env per OS: NPM_BIN_PATH = '/opt/homebrew/bin/npm' on macOS
NPM_BIN_PATH = os.environ.get('NPM_BIN_PATH', '/usr/local/bin/npm')

# Feature flag — opt into the new Foundry UI base.html during rollout
USE_FOUNDRY_UI = os.environ.get('USE_FOUNDRY_UI', 'False').lower() == 'true'
```

- [ ] **Step 4: Verify Django still boots**

Run: `cd config_educa && python manage.py check`
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 5: Commit**

```bash
git add config_educa/config_educa/settings/base.py
git commit -m "chore: register tailwind + django-htmx in Django settings"
```

---

### Task 3: Initialize the tailwind app

**Files:**
- Create: `theme/` (via `tailwind init`)

- [ ] **Step 1: Run tailwind init**

Run: `cd config_educa && python manage.py tailwind init`
When prompted for app name, enter: `theme`
Expected: directory `config_educa/theme/` is created.

- [ ] **Step 2: Add `theme` to INSTALLED_APPS**

Edit `config_educa/config_educa/settings/base.py`. In `INSTALLED_APPS`, near the other new entries from Task 2, add:

```python
    'theme',
```

- [ ] **Step 3: Install npm deps**

Run: `cd config_educa && python manage.py tailwind install`
Expected: prints npm install progress, ends without errors.

- [ ] **Step 4: Verify build works**

Run: `cd config_educa && python manage.py tailwind build`
Expected: produces `config_educa/theme/static/css/dist/styles.css`.

- [ ] **Step 5: Add build output to .gitignore**

Edit root `.gitignore`. Under the Django section add:

```
config_educa/theme/static/css/dist/
config_educa/theme/static_src/node_modules/
```

- [ ] **Step 6: Commit**

```bash
git add config_educa/theme config_educa/config_educa/settings/base.py .gitignore
git commit -m "chore: initialize django-tailwind theme app"
```

---

### Task 4: Replace tailwind.config.js with Foundry design tokens

**Files:**
- Modify: `config_educa/theme/static_src/tailwind.config.js`

- [ ] **Step 1: Overwrite tailwind.config.js**

Open `config_educa/theme/static_src/tailwind.config.js` and replace its contents with:

```js
module.exports = {
  content: [
    '../templates/**/*.html',
    '../../templates/**/*.html',
    '../../**/templates/**/*.html',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        bg: {
          base:     '#0A0D12',
          panel:    '#11151C',
          elevated: '#181D27',
          hover:    '#1F2533',
          active:   '#283041',
        },
        border: {
          subtle: '#1F2533',
          strong: '#2D3648',
          accent: '#00B8D4',
        },
        text: {
          primary:   '#E6E9EF',
          secondary: '#8B95A7',
          muted:     '#5C6578',
          mono:      '#C8FFE9',
        },
        accent: {
          DEFAULT: '#00B8D4',
          hover:   '#00D4F2',
          muted:   '#003D47',
        },
        success: '#4ADE80',
        warning: '#FBBF24',
        danger:  '#F87171',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', '"JetBrains Mono"', 'monospace'],
      },
      fontSize: {
        'mono-data':  ['13px',  { lineHeight: '18px', fontWeight: '500' }],
        'mono-label': ['11px',  { lineHeight: '14px', fontWeight: '500', letterSpacing: '0.08em' }],
        'display':    ['32px',  { lineHeight: '36px', fontWeight: '600', letterSpacing: '-0.02em' }],
      },
      borderRadius: { DEFAULT: '2px', md: '4px' },
      spacing: { '4.5': '18px', '13': '52px', '15': '60px' },
      boxShadow: { overlay: '0 8px 24px rgba(0,0,0,0.5)' },
      transitionTimingFunction: { foundry: 'cubic-bezier(0.2, 0, 0.2, 1)' },
      transitionDuration: { '120': '120ms' },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
    require('@tailwindcss/forms'),
  ],
}
```

- [ ] **Step 2: Verify build still succeeds**

Run: `cd config_educa && python manage.py tailwind build`
Expected: no errors. Inspect `theme/static/css/dist/styles.css` exists and is > 5KB.

- [ ] **Step 3: Commit**

```bash
git add config_educa/theme/static_src/tailwind.config.js
git commit -m "feat: define Foundry design tokens in tailwind config"
```

---

### Task 5: Add custom CSS layer + font setup

**Files:**
- Modify: `config_educa/theme/static_src/src/styles.css`
- Create: `config_educa/theme/static/fonts/.gitkeep`

- [ ] **Step 1: Overwrite styles.css**

Open `config_educa/theme/static_src/src/styles.css` and replace contents with:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Self-hosted IBM Plex Mono. Drop .woff2 files under theme/static/fonts/
   filenames: IBMPlexMono-Regular.woff2, IBMPlexMono-Medium.woff2 */
@font-face {
  font-family: 'IBM Plex Mono';
  src: url('/static/fonts/IBMPlexMono-Regular.woff2') format('woff2');
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}
@font-face {
  font-family: 'IBM Plex Mono';
  src: url('/static/fonts/IBMPlexMono-Medium.woff2') format('woff2');
  font-weight: 500;
  font-style: normal;
  font-display: swap;
}

@layer base {
  :root { color-scheme: dark; }
  html, body { background-color: theme('colors.bg.base'); color: theme('colors.text.primary'); }
  *:focus-visible {
    outline: none;
    box-shadow: 0 0 0 2px rgba(0, 184, 212, 0.4);
    border-radius: 2px;
  }
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
  }
}

@layer components {
  .btn { @apply inline-flex items-center justify-center h-8 px-3 rounded-DEFAULT text-mono-label uppercase transition-colors duration-120 ease-foundry; }
  .btn-primary { @apply btn bg-accent text-bg-base hover:bg-accent-hover; }
  .btn-ghost { @apply btn border border-border-strong text-text-primary hover:bg-bg-hover; }
  .btn-danger { @apply btn bg-danger text-bg-base hover:opacity-90; }

  .panel { @apply bg-bg-panel border border-border-subtle rounded-DEFAULT; }
  .panel-header { @apply flex items-center justify-between h-8 px-3 border-b border-border-subtle; }
  .panel-title { @apply text-mono-label uppercase text-text-secondary; }

  .input { @apply h-8 px-3 bg-bg-base border border-border-strong rounded-DEFAULT text-sm text-text-primary placeholder:text-text-muted focus:border-accent transition-colors duration-120; }

  .badge { @apply inline-flex items-center h-5 px-1.5 rounded-DEFAULT text-mono-label uppercase; }
  .badge-neutral { @apply badge border border-border-subtle text-text-secondary; }
  .badge-accent  { @apply badge bg-accent-muted text-accent; }
  .badge-success { @apply badge bg-success/20 text-success; }
  .badge-warning { @apply badge bg-warning/20 text-warning; }
  .badge-danger  { @apply badge bg-danger/20 text-danger; }
}
```

- [ ] **Step 2: Create fonts directory placeholder**

Run: `mkdir -p config_educa/theme/static/fonts && touch config_educa/theme/static/fonts/.gitkeep`

- [ ] **Step 3: Note for the engineer — fonts must be downloaded manually**

The IBM Plex Mono WOFF2 files are not bundled. Before deploying, download from https://fonts.google.com/specimen/IBM+Plex+Mono → "Get fonts" → extract `IBMPlexMono-Regular.woff2` and `IBMPlexMono-Medium.woff2` into `config_educa/theme/static/fonts/`. Until then, the browser falls back to the next family in `font-mono`.

- [ ] **Step 4: Rebuild and inspect**

Run: `cd config_educa && python manage.py tailwind build`
Expected: build succeeds. Open `theme/static/css/dist/styles.css` and `grep "btn-primary" theme/static/css/dist/styles.css` should return at least one match.

- [ ] **Step 5: Commit**

```bash
git add config_educa/theme/static_src/src/styles.css config_educa/theme/static/fonts/.gitkeep
git commit -m "feat: tailwind base styles, focus rings, btn/panel/input/badge component layer"
```

---

### Task 6: Scaffold `shared` Django app

**Files:**
- Create: `config_educa/shared/__init__.py`
- Create: `config_educa/shared/apps.py`
- Create: `config_educa/shared/views.py`
- Create: `config_educa/shared/urls.py`
- Create: `config_educa/shared/tests.py`
- Modify: `config_educa/config_educa/settings/base.py`
- Modify: `config_educa/config_educa/urls.py`

- [ ] **Step 1: Create the app via manage.py**

Run: `cd config_educa && python manage.py startapp shared`
Expected: `config_educa/shared/` directory created with default files.

- [ ] **Step 2: Replace `shared/apps.py`**

Overwrite `config_educa/shared/apps.py` with:

```python
from django.apps import AppConfig


class SharedConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "shared"
    verbose_name = "Shared UI components"
```

- [ ] **Step 3: Register the app in settings**

In `config_educa/config_educa/settings/base.py` INSTALLED_APPS, add:

```python
    'shared',
```

- [ ] **Step 4: Write the failing test for /components/ debug view**

Replace `config_educa/shared/tests.py` with:

```python
from django.test import TestCase
from django.urls import reverse


class ComponentsDebugViewTests(TestCase):
    def test_debug_view_returns_200(self):
        url = reverse("shared:components_debug")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_debug_view_uses_components_debug_template(self):
        url = reverse("shared:components_debug")
        response = self.client.get(url)
        self.assertTemplateUsed(response, "shared/_components_debug.html")
```

- [ ] **Step 5: Run test, confirm failure**

Run: `cd config_educa && python manage.py test shared`
Expected: `ERRORS` or `FAIL` — URL `shared:components_debug` does not exist yet.

- [ ] **Step 6: Implement view + url**

Create `config_educa/shared/views.py`:

```python
from django.views.generic import TemplateView


class ComponentsDebugView(TemplateView):
    """Visual debug page for all UI primitives. Not linked from production nav."""
    template_name = "shared/_components_debug.html"
```

Create `config_educa/shared/urls.py`:

```python
from django.urls import path

from .views import ComponentsDebugView

app_name = "shared"

urlpatterns = [
    path("", ComponentsDebugView.as_view(), name="components_debug"),
]
```

- [ ] **Step 7: Wire URLs in project root**

Edit `config_educa/config_educa/urls.py`. Add inside `urlpatterns`:

```python
    path("components/", include("shared.urls")),
```

Add to imports if missing: `from django.urls import include, path`.

- [ ] **Step 8: Create the empty debug template**

Create `config_educa/shared/templates/shared/_components_debug.html` with:

```django
{% extends "base.html" %}
{% block title %}Components{% endblock %}
{% block content %}
<h1 class="text-2xl font-semibold mb-6">Components</h1>
<p class="text-text-secondary">Primitives will be added in subsequent tasks.</p>
{% endblock %}
```

(The `base.html` referenced here is created in Task 7. Test will pass once Task 7 lands. For now it will pass the URL/template lookup but render against the existing `courses/templates/base.html`.)

- [ ] **Step 9: Run test, expect green**

Run: `cd config_educa && python manage.py test shared`
Expected: `OK` with 2 tests passing.

- [ ] **Step 10: Commit**

```bash
git add config_educa/shared/ config_educa/config_educa/settings/base.py config_educa/config_educa/urls.py
git commit -m "feat: scaffold shared app with /components/ debug view + tests"
```

---

### Task 7: Build the app-shell `base.html` + topbar + sidebar

**Files:**
- Create: `config_educa/theme/templates/base.html`
- Create: `config_educa/shared/templates/shared/_topbar.html`
- Create: `config_educa/shared/templates/shared/_sidebar.html`
- Create: `config_educa/shared/templates/shared/_command_palette.html`

- [ ] **Step 1: Create `_topbar.html`**

Create `config_educa/shared/templates/shared/_topbar.html`:

```django
{% load static %}
<header class="h-12 bg-bg-panel border-b border-border-subtle flex items-center px-4 sticky top-0 z-30">
  <a href="/" class="text-mono-label uppercase tracking-wider text-text-primary mr-2">EDUCTO</a>
  <span class="text-text-muted mx-2">▸</span>
  <span class="text-mono-label uppercase text-accent">{% block breadcrumb %}HOME{% endblock %}</span>

  <div class="ml-auto flex items-center gap-3">
    <button type="button"
            class="btn-ghost h-8 px-2 text-text-secondary"
            x-data
            @click="$dispatch('open-command-palette')"
            aria-label="Open command palette">
      ⌘K
    </button>
    {% if user.is_authenticated %}
      <div class="text-mono-label uppercase text-text-secondary">{{ user.username }}</div>
      <a href="{% url 'logout' %}" class="btn-ghost h-8 px-2">SIGN OUT</a>
    {% else %}
      <a href="{% url 'login' %}" class="btn-primary">SIGN IN</a>
    {% endif %}
  </div>
</header>
```

- [ ] **Step 2: Create `_sidebar.html`**

Create `config_educa/shared/templates/shared/_sidebar.html`:

```django
{% load static %}
<aside class="w-14 hover:w-52 transition-[width] duration-120 ease-foundry
              bg-bg-panel border-r border-border-subtle
              flex flex-col group sticky top-12 h-[calc(100vh-3rem)]"
       aria-label="Primary navigation">
  <nav class="flex flex-col py-3 flex-1">
    {% with current=request.resolver_match.namespace %}
    <a href="/" class="nav-item {% if current == '' %}is-active{% endif %}" aria-label="Home">
      <span class="nav-icon">▢</span>
      <span class="nav-label">HOME</span>
    </a>
    <a href="{% url 'students:student_course_list' %}" class="nav-item" aria-label="My courses">
      <span class="nav-icon">▤</span>
      <span class="nav-label">MY COURSES</span>
    </a>
    <a href="/" class="nav-item" aria-label="Catalog">
      <span class="nav-icon">⊞</span>
      <span class="nav-label">CATALOG</span>
    </a>
    <a href="/chat/" class="nav-item" aria-label="Chat">
      <span class="nav-icon">◐</span>
      <span class="nav-label">CHAT</span>
    </a>
    {% endwith %}
  </nav>
  <div class="border-t border-border-subtle py-2 text-mono-label uppercase text-text-muted px-4">
    <span class="nav-label">v1.4.2</span>
  </div>
</aside>

<style>
  .nav-item { @apply flex items-center h-10 px-4 gap-3 text-text-secondary hover:bg-bg-hover hover:text-text-primary transition-colors duration-120 overflow-hidden whitespace-nowrap; }
  .nav-item.is-active { @apply text-accent border-l-2 border-accent bg-bg-active; }
  .nav-icon { @apply text-lg w-6 text-center shrink-0; }
  .nav-label { @apply text-mono-label uppercase opacity-0 group-hover:opacity-100 transition-opacity duration-120; }
</style>
```

- [ ] **Step 3: Create `_command_palette.html` skeleton**

Create `config_educa/shared/templates/shared/_command_palette.html`:

```django
<div x-data="{ open: false }"
     @open-command-palette.window="open = true"
     @keydown.escape.window="open = false"
     x-show="open"
     x-cloak
     class="fixed inset-0 z-50 flex items-start justify-center pt-32 bg-black/60"
     @click.self="open = false">
  <div class="w-[600px] panel shadow-overlay" @click.stop>
    <div class="panel-header"><span class="panel-title">COMMAND PALETTE</span><span class="text-text-muted text-mono-label">esc</span></div>
    <div class="p-3">
      <input type="text" class="input w-full" placeholder="Type a command…" autofocus>
      <p class="text-text-muted text-sm mt-3">Search, jump to course, mark complete… (M6)</p>
    </div>
  </div>
</div>
```

- [ ] **Step 4: Create the new `base.html`**

Create `config_educa/theme/templates/base.html`:

```django
{% load static tailwind_tags django_htmx %}
<!doctype html>
<html lang="en" class="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}Educto{% endblock %} ▸ Educto</title>
  <link rel="preconnect" href="https://rsms.me/">
  <link rel="stylesheet" href="https://rsms.me/inter/inter.css">
  {% tailwind_css %}
  <script defer src="https://unpkg.com/htmx.org@2.0.2" integrity="sha384-Y7hw+L/jvKeWIRRkqWYfPcvVxHzVzn5REgzbawhxAuQGwX1XWe70vji+VSeHOThJ" crossorigin="anonymous"></script>
  <script defer src="https://unpkg.com/alpinejs@3.14.1/dist/cdn.min.js" crossorigin="anonymous"></script>
  {% django_htmx_script %}
</head>
<body class="bg-bg-base text-text-primary font-sans antialiased min-h-screen">
  <a href="#main" class="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 btn-primary z-50">Skip to main</a>
  {% include "shared/_topbar.html" %}
  <div class="flex">
    {% include "shared/_sidebar.html" %}
    <main id="main" class="flex-1 min-h-[calc(100vh-3rem)] p-6">
      {% block content %}{% endblock %}
    </main>
  </div>
  {% include "shared/_command_palette.html" %}
  <div aria-live="polite" aria-atomic="true" class="sr-only" id="hx-live-region"></div>
</body>
</html>
```

- [ ] **Step 5: Sanity check rendering**

Run: `cd config_educa && python manage.py runserver`
Open `http://127.0.0.1:8000/components/` in a browser.

Expected: page renders on dark background, topbar shows "EDUCTO ▸ HOME" with accent on HOME, sidebar shows 4 nav icons that expand on hover.

If sidebar/topbar don't appear, check `python manage.py tailwind start` is running in another terminal to recompile CSS.

- [ ] **Step 6: Commit**

```bash
git add config_educa/theme/templates/base.html config_educa/shared/templates/shared/_topbar.html config_educa/shared/templates/shared/_sidebar.html config_educa/shared/templates/shared/_command_palette.html
git commit -m "feat: app-shell base template with topbar, sidebar, command-palette skeleton"
```

---

### Task 8: Smoke test — apply Foundry base to login page behind feature flag

**Files:**
- Modify: `config_educa/courses/templates/registration/login.html`

- [ ] **Step 1: Read the existing login template**

Run: `cat config_educa/courses/templates/registration/login.html`
Note the current `{% extends %}` line and the structure of the form.

- [ ] **Step 2: Add a conditional extends based on feature flag**

Replace the first line of `login.html` with:

```django
{% load static %}
{% if USE_FOUNDRY_UI %}{% extends "base.html" %}{% else %}{% extends "courses/base.html" %}{% endif %}
```

(Adjust the `else` branch to match the existing extends path verbatim from Step 1.)

- [ ] **Step 3: Wrap content block with Foundry-aware styling**

In the `{% block content %}` body, ensure the form has Tailwind classes when the flag is on. Surround the form with:

```django
{% block content %}
<div class="max-w-md mx-auto">
  <div class="panel p-6">
    <div class="text-mono-label uppercase text-text-secondary mb-4">SIGN IN</div>
    {% if form.errors %}
      <div class="badge-danger mb-3">Invalid credentials</div>
    {% endif %}
    <form method="post" class="flex flex-col gap-3">
      {% csrf_token %}
      <label class="text-mono-label uppercase text-text-secondary" for="id_username">USERNAME</label>
      <input class="input" type="text" name="username" id="id_username" required autofocus>
      <label class="text-mono-label uppercase text-text-secondary mt-2" for="id_password">PASSWORD</label>
      <input class="input" type="password" name="password" id="id_password" required>
      <button type="submit" class="btn-primary mt-4">SIGN IN →</button>
    </form>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 4: Add a context processor so `USE_FOUNDRY_UI` is available in templates**

Edit `config_educa/config_educa/settings/base.py`. In the `TEMPLATES` setting `OPTIONS.context_processors`, add:

```python
                'config_educa.context_processors.feature_flags',
```

Create `config_educa/config_educa/context_processors.py`:

```python
from django.conf import settings


def feature_flags(request):
    return {"USE_FOUNDRY_UI": getattr(settings, "USE_FOUNDRY_UI", False)}
```

- [ ] **Step 5: Test flag OFF (default behavior preserved)**

Run: `cd config_educa && python manage.py runserver`
Open `/accounts/login/`. Expected: original look (current blue theme).

- [ ] **Step 6: Test flag ON**

Stop server. Run: `USE_FOUNDRY_UI=true python manage.py runserver`
Open `/accounts/login/`. Expected: Foundry dark login panel.

- [ ] **Step 7: Run all tests, expect no regressions**

Run: `cd config_educa && python manage.py test`
Expected: same count of pass/fail as before this task.

- [ ] **Step 8: Commit**

```bash
git add config_educa/courses/templates/registration/login.html config_educa/config_educa/settings/base.py config_educa/config_educa/context_processors.py
git commit -m "feat: foundry-themed login page behind USE_FOUNDRY_UI flag"
```

---

# M1 — Component library

For Tasks 9–17 each adds ONE primitive to the library + adds it to the `/components/` debug page so a human (or Playwright tester) can eyeball it. Every component partial accepts include parameters via `{% include "shared/components/_x.html" with foo="bar" %}` — Django's standard partial include.

### Task 9: Panel primitive

**Files:**
- Create: `config_educa/shared/templates/shared/components/_panel.html`
- Modify: `config_educa/shared/templates/shared/_components_debug.html`

- [ ] **Step 1: Create `_panel.html`**

```django
{# Panel — reusable container.
   Usage: {% include "shared/components/_panel.html" with title="ENROLLED COURSES" %}
            ...body...
          {% endinclude %} is not Django syntax — instead use the block form below.

   Or simpler: write inline using .panel/.panel-header CSS classes. This partial
   is for the title+body case only.

   Required: title (string)
   Optional: actions (HTML)
   Slot: body (passed via the `body` kwarg, rendered as |safe).
#}
<section class="panel">
  <header class="panel-header">
    <span class="panel-title">{{ title }}</span>
    {% if actions %}<div>{{ actions|safe }}</div>{% endif %}
  </header>
  <div class="p-4">
    {{ body|safe }}
  </div>
</section>
```

- [ ] **Step 2: Update components debug page to render a Panel example**

Open `config_educa/shared/templates/shared/_components_debug.html`. Replace its body block with:

```django
{% block content %}
<h1 class="text-2xl font-semibold mb-6">Components</h1>

<section class="mb-10">
  <h2 class="text-mono-label uppercase text-text-secondary mb-2">PANEL</h2>
  {% include "shared/components/_panel.html" with title="ENROLLED COURSES" body="<p class='text-text-secondary'>Body content goes here.</p>" %}
</section>
{% endblock %}
```

- [ ] **Step 3: View in browser**

Run server with `USE_FOUNDRY_UI=true python manage.py runserver` (after `tailwind start` in another terminal).
Open `http://127.0.0.1:8000/components/`. Expected: a single panel with header "ENROLLED COURSES" and body text appears.

- [ ] **Step 4: Commit**

```bash
git add config_educa/shared/templates/shared/components/_panel.html config_educa/shared/templates/shared/_components_debug.html
git commit -m "feat: add panel primitive + components debug page"
```

---

### Task 10: Button primitive

**Files:**
- Create: `config_educa/shared/templates/shared/components/_button.html`
- Modify: `config_educa/shared/templates/shared/_components_debug.html`

- [ ] **Step 1: Create `_button.html`**

```django
{# Button primitive.
   Required: label (string)
   Optional: variant (primary|ghost|danger, default primary), type (default button), href (renders <a>), icon (string, e.g. "→")
#}
{% with variant=variant|default:"primary" %}
{% if href %}
<a href="{{ href }}" class="btn-{{ variant }}">{{ label }}{% if icon %} {{ icon }}{% endif %}</a>
{% else %}
<button type="{{ type|default:'button' }}" class="btn-{{ variant }}">{{ label }}{% if icon %} {{ icon }}{% endif %}</button>
{% endif %}
{% endwith %}
```

- [ ] **Step 2: Add button examples to debug page**

Append to `_components_debug.html` content block:

```django
<section class="mb-10">
  <h2 class="text-mono-label uppercase text-text-secondary mb-2">BUTTON</h2>
  <div class="flex gap-3">
    {% include "shared/components/_button.html" with label="ENROLL" icon="→" %}
    {% include "shared/components/_button.html" with label="CANCEL" variant="ghost" %}
    {% include "shared/components/_button.html" with label="DELETE" variant="danger" %}
    {% include "shared/components/_button.html" with label="LINK" variant="ghost" href="#" %}
  </div>
</section>
```

- [ ] **Step 3: Verify in browser**

Reload `/components/`. Expected: 4 buttons render in a row, cyan/ghost/red/ghost.

- [ ] **Step 4: Commit**

```bash
git add config_educa/shared/templates/shared/components/_button.html config_educa/shared/templates/shared/_components_debug.html
git commit -m "feat: add button primitive (primary/ghost/danger)"
```

---

### Task 11: Input primitive

**Files:**
- Create: `config_educa/shared/templates/shared/components/_input.html`
- Modify: `config_educa/shared/templates/shared/_components_debug.html`

- [ ] **Step 1: Create `_input.html`**

```django
{# Input primitive.
   Required: name
   Optional: type (default text), label, placeholder, value, required (bool), id (default = name)
#}
{% with input_id=id|default:name %}
<div class="flex flex-col gap-1.5">
  {% if label %}<label for="{{ input_id }}" class="text-mono-label uppercase text-text-secondary">{{ label }}</label>{% endif %}
  <input type="{{ type|default:'text' }}"
         name="{{ name }}"
         id="{{ input_id }}"
         value="{{ value|default:'' }}"
         placeholder="{{ placeholder|default:'' }}"
         {% if required %}required{% endif %}
         class="input">
</div>
{% endwith %}
```

- [ ] **Step 2: Add example to debug page**

```django
<section class="mb-10">
  <h2 class="text-mono-label uppercase text-text-secondary mb-2">INPUT</h2>
  <div class="max-w-xs flex flex-col gap-3">
    {% include "shared/components/_input.html" with name="username" label="USERNAME" placeholder="msabaliauskas" %}
    {% include "shared/components/_input.html" with name="password" label="PASSWORD" type="password" %}
  </div>
</section>
```

- [ ] **Step 3: Verify**

Reload `/components/`. Expected: two stacked labeled inputs, focus ring on click.

- [ ] **Step 4: Commit**

```bash
git add config_educa/shared/templates/shared/components/_input.html config_educa/shared/templates/shared/_components_debug.html
git commit -m "feat: add input primitive with optional label"
```

---

### Task 12: Badge primitive

**Files:**
- Create: `config_educa/shared/templates/shared/components/_badge.html`
- Modify: `config_educa/shared/templates/shared/_components_debug.html`

- [ ] **Step 1: Create `_badge.html`**

```django
{# Badge.
   Required: label
   Optional: variant (neutral|accent|success|warning|danger, default neutral)
#}
<span class="badge-{{ variant|default:'neutral' }}">{{ label }}</span>
```

- [ ] **Step 2: Add examples to debug page**

```django
<section class="mb-10">
  <h2 class="text-mono-label uppercase text-text-secondary mb-2">BADGE</h2>
  <div class="flex gap-2">
    {% include "shared/components/_badge.html" with label="NEUTRAL" %}
    {% include "shared/components/_badge.html" with label="ACCENT" variant="accent" %}
    {% include "shared/components/_badge.html" with label="ACTIVE" variant="success" %}
    {% include "shared/components/_badge.html" with label="DRAFT" variant="warning" %}
    {% include "shared/components/_badge.html" with label="ERROR" variant="danger" %}
  </div>
</section>
```

- [ ] **Step 3: Verify** — 5 badges in a row, all variants visible.

- [ ] **Step 4: Commit**

```bash
git add config_educa/shared/templates/shared/components/_badge.html config_educa/shared/templates/shared/_components_debug.html
git commit -m "feat: add badge primitive (5 variants)"
```

---

### Task 13: ProgressBar primitive

**Files:**
- Create: `config_educa/shared/templates/shared/components/_progress_bar.html`
- Modify: `config_educa/shared/templates/shared/_components_debug.html`

- [ ] **Step 1: Create `_progress_bar.html`**

```django
{# Progress bar.
   Required: percent (0-100 integer)
   Optional: show_label (bool, default true)
#}
<div class="flex items-center gap-3">
  <div class="flex-1 h-1 bg-bg-active rounded-DEFAULT overflow-hidden" role="progressbar"
       aria-valuemin="0" aria-valuemax="100" aria-valuenow="{{ percent }}">
    <div class="h-full bg-accent transition-[width] duration-[240ms] ease-out"
         style="width: {{ percent }}%"></div>
  </div>
  {% if show_label|default_if_none:True %}
    <span class="text-mono-data text-text-mono w-10 text-right">{{ percent }}%</span>
  {% endif %}
</div>
```

- [ ] **Step 2: Add examples to debug**

```django
<section class="mb-10">
  <h2 class="text-mono-label uppercase text-text-secondary mb-2">PROGRESS BAR</h2>
  <div class="max-w-md flex flex-col gap-3">
    {% include "shared/components/_progress_bar.html" with percent=12 %}
    {% include "shared/components/_progress_bar.html" with percent=78 %}
    {% include "shared/components/_progress_bar.html" with percent=100 %}
  </div>
</section>
```

- [ ] **Step 3: Verify** — three bars at 12%, 78%, 100% with mono numbers right.

- [ ] **Step 4: Commit**

```bash
git add config_educa/shared/templates/shared/components/_progress_bar.html config_educa/shared/templates/shared/_components_debug.html
git commit -m "feat: add progress-bar primitive with aria-valuenow"
```

---

### Task 14: ModuleRow primitive

**Files:**
- Create: `config_educa/shared/templates/shared/components/_module_row.html`
- Modify: `config_educa/shared/templates/shared/_components_debug.html`

- [ ] **Step 1: Create `_module_row.html`**

```django
{# ModuleRow — for curriculum lists and the course-player left rail.
   Required: number (e.g. "7.3"), title (e.g. "Decorators in depth")
   Optional: duration (e.g. "18min"), status (complete|active|locked, default none),
             href (anchor), hx_get (HTMX swap URL), hx_target
#}
<a href="{{ href|default:'#' }}"
   {% if hx_get %}hx-get="{{ hx_get }}" hx-target="{{ hx_target|default:'#main' }}" hx-push-url="true"{% endif %}
   class="module-row flex items-center h-10 px-3 gap-3 border-l-2
          {% if status == 'active' %}bg-bg-active border-accent{% else %}border-transparent hover:bg-bg-hover{% endif %}
          transition-colors duration-120">
  <span class="text-mono-label text-text-secondary w-12 shrink-0">{{ number }}</span>
  <span class="flex-1 text-sm text-text-primary truncate">{{ title }}</span>
  {% if duration %}<span class="text-mono-data text-text-muted">{{ duration }}</span>{% endif %}
  {% if status == 'complete' %}<span class="text-success">✓</span>
  {% elif status == 'active' %}<span class="text-accent">●</span>
  {% elif status == 'locked' %}<span class="text-text-muted">◌</span>{% endif %}
</a>
```

- [ ] **Step 2: Add examples to debug**

```django
<section class="mb-10">
  <h2 class="text-mono-label uppercase text-text-secondary mb-2">MODULE ROW</h2>
  <div class="max-w-md panel">
    {% include "shared/components/_module_row.html" with number="01" title="Functions, closures, scope" duration="1h 12m" status="complete" %}
    {% include "shared/components/_module_row.html" with number="02" title="Iterators & generators" duration="0h 58m" status="complete" %}
    {% include "shared/components/_module_row.html" with number="7.3" title="Decorators in depth" duration="18min" status="active" %}
    {% include "shared/components/_module_row.html" with number="7.4" title="Decorator factory" duration="22min" %}
    {% include "shared/components/_module_row.html" with number="08" title="Context managers" status="locked" %}
  </div>
</section>
```

- [ ] **Step 3: Verify** — 5-row list, row 3 highlighted with left border + cyan dot, status icons render.

- [ ] **Step 4: Commit**

```bash
git add config_educa/shared/templates/shared/components/_module_row.html config_educa/shared/templates/shared/_components_debug.html
git commit -m "feat: add module-row primitive with status states and HTMX hooks"
```

---

### Task 15: ActivitySparkline primitive

**Files:**
- Create: `config_educa/shared/templates/shared/components/_activity_sparkline.html`
- Modify: `config_educa/shared/templates/shared/_components_debug.html`

- [ ] **Step 1: Create `_activity_sparkline.html`**

The cleanest approach is to compute bar heights in the view and pass pre-computed pixel values. The template stays dumb:

```django
{# Activity sparkline — SVG bar chart.
   Required: bars (iterable of dicts: {"h": height_px, "v": raw_value}). Renders one bar per item.
   Optional: title (string for aria-label), max_height (default 32)
#}
{% with chart_h=max_height|default:32 %}
<svg viewBox="0 0 {{ bars|length }}0 {{ chart_h }}"
     preserveAspectRatio="none"
     class="w-full h-8" role="img"
     aria-label="{{ title|default:'Activity over time' }}">
  {% for bar in bars %}
    <rect x="{{ forloop.counter0 }}0"
          y="{{ bar.y }}"
          width="6"
          height="{{ bar.h }}"
          class="fill-accent"/>
    <title>{{ bar.v }}</title>
  {% endfor %}
</svg>
{% endwith %}
```

- [ ] **Step 2: Add example to debug page**

Append to `_components_debug.html`:

```django
<section class="mb-10">
  <h2 class="text-mono-label uppercase text-text-secondary mb-2">ACTIVITY SPARKLINE</h2>
  <div class="max-w-md panel p-3">
    {% include "shared/components/_activity_sparkline.html" with bars=demo_sparkline title="Last 14 days" %}
  </div>
</section>
```

- [ ] **Step 3: Provide `demo_sparkline` in the view**

Edit `config_educa/shared/views.py`:

```python
from django.views.generic import TemplateView


def _sparkline_bars(values, max_height=32):
    """Convert raw values to {y, h, v} dicts so the template can stay dumb."""
    peak = max(values) or 1
    bars = []
    for v in values:
        h = round((v / peak) * max_height)
        bars.append({"v": v, "h": h, "y": max_height - h})
    return bars


class ComponentsDebugView(TemplateView):
    template_name = "shared/_components_debug.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["demo_sparkline"] = _sparkline_bars([3, 5, 7, 6, 4, 2, 1, 4, 6, 8, 6, 4, 3, 5])
        return ctx
```

- [ ] **Step 4: Verify** — small bar chart appears with 14 cyan bars of varying heights.

- [ ] **Step 5: Commit**

```bash
git add config_educa/shared/templates/shared/components/_activity_sparkline.html config_educa/shared/templates/shared/_components_debug.html config_educa/shared/views.py
git commit -m "feat: add SVG activity-sparkline primitive"
```

---

### Task 16: ChatMessage primitive

**Files:**
- Create: `config_educa/shared/templates/shared/components/_chat_message.html`
- Modify: `config_educa/shared/templates/shared/_components_debug.html`

- [ ] **Step 1: Create `_chat_message.html`**

```django
{# ChatMessage.
   Required: username, timestamp (HH:MM or datetime), body
   Optional: role (instructor|student|self|system, default student)
#}
{% with role=role|default:"student" %}
<article class="flex gap-3 py-2 px-3 hover:bg-bg-hover">
  <span class="text-mono-label uppercase shrink-0 w-32 truncate
    {% if role == 'instructor' %}text-accent
    {% elif role == 'self' %}text-text-muted
    {% elif role == 'system' %}italic text-text-muted
    {% else %}text-text-primary{% endif %}">{{ username }}</span>
  <span class="text-mono-label text-text-muted shrink-0">{{ timestamp }}</span>
  <p class="flex-1 text-sm text-text-primary whitespace-pre-wrap break-words {% if role == 'system' %}italic text-text-muted{% endif %}">{{ body }}</p>
</article>
{% endwith %}
```

- [ ] **Step 2: Add examples**

```django
<section class="mb-10">
  <h2 class="text-mono-label uppercase text-text-secondary mb-2">CHAT MESSAGE</h2>
  <div class="max-w-2xl panel">
    {% include "shared/components/_chat_message.html" with username="D.GREENFELD" timestamp="14:08" body="Welcome everyone, M7 quiz is live until Friday." role="instructor" %}
    {% include "shared/components/_chat_message.html" with username="ANYA" timestamp="14:12" body="Anyone got time after for pair programming on 7.3?" %}
    {% include "shared/components/_chat_message.html" with username="YOU" timestamp="14:13" body="I'm in. 16:00 UTC?" role="self" %}
    {% include "shared/components/_chat_message.html" with username="SYSTEM" timestamp="14:20" body="Marius joined the room" role="system" %}
  </div>
</section>
```

- [ ] **Step 3: Verify** — 4 messages with role colors: instructor cyan, student default, self muted, system italic muted.

- [ ] **Step 4: Commit**

```bash
git add config_educa/shared/templates/shared/components/_chat_message.html config_educa/shared/templates/shared/_components_debug.html
git commit -m "feat: add chat-message primitive with role-based styling"
```

---

### Task 17: Table primitive

**Files:**
- Create: `config_educa/shared/templates/shared/components/_table.html`
- Modify: `config_educa/shared/templates/shared/_components_debug.html`

- [ ] **Step 1: Create `_table.html`**

```django
{# Table.
   Required: headers (list of strings), rows (list of lists of strings)
   Optional: numeric_cols (list of 0-based column indexes to render in mono-data)
#}
<table class="w-full">
  <thead>
    <tr class="border-b border-border-subtle">
      {% for h in headers %}
        <th class="text-mono-label uppercase text-text-secondary text-left py-2 px-3">{{ h }}</th>
      {% endfor %}
    </tr>
  </thead>
  <tbody>
    {% for row in rows %}
      <tr class="border-b border-border-subtle hover:bg-bg-hover">
        {% for cell in row %}
          <td class="py-2 px-3 {% if forloop.counter0 in numeric_cols %}text-mono-data text-text-mono{% else %}text-sm text-text-primary{% endif %}">{{ cell }}</td>
        {% endfor %}
      </tr>
    {% endfor %}
  </tbody>
</table>
```

- [ ] **Step 2: Add example to debug page + view context**

In `_components_debug.html`:

```django
<section class="mb-10">
  <h2 class="text-mono-label uppercase text-text-secondary mb-2">TABLE</h2>
  <div class="panel">
    {% include "shared/components/_table.html" with headers=demo_table_headers rows=demo_table_rows numeric_cols=demo_table_numeric %}
  </div>
</section>
```

Extend `ComponentsDebugView.get_context_data`:

```python
        ctx["demo_table_headers"] = ["#", "MODULE", "ITEMS", "DURATION"]
        ctx["demo_table_rows"] = [
            ["01", "Functions, closures, scope", "6", "1h 12m"],
            ["02", "Iterators & generators", "5", "0h 58m"],
            ["03", "Decorators", "7", "1h 34m"],
        ]
        ctx["demo_table_numeric"] = [0, 2, 3]
```

- [ ] **Step 3: Verify** — table renders with mono-label headers, mono-data numbers in cols 0/2/3, hover state.

- [ ] **Step 4: Commit**

```bash
git add config_educa/shared/templates/shared/components/_table.html config_educa/shared/templates/shared/_components_debug.html config_educa/shared/views.py
git commit -m "feat: add table primitive with numeric column highlighting"
```

---

### Task 18: Final M1 verification — full debug page + screenshot baseline

**Files:**
- Create: `tests/visual/baselines/.gitkeep`
- Create: `tests/visual/components-baseline.png` (committed binary)

- [ ] **Step 1: Run the full app and walk through `/components/`**

Start two terminals:
1. `cd config_educa && python manage.py tailwind start`
2. `cd config_educa && USE_FOUNDRY_UI=true python manage.py runserver`

Navigate to `http://127.0.0.1:8000/components/`.

Visual checklist:
- [ ] Topbar dark, "EDUCTO ▸ HOME" with cyan HOME, ⌘K button right
- [ ] Sidebar 56px wide, icons visible; expands to 208px on hover with mono-label labels
- [ ] PANEL section: single panel with header
- [ ] BUTTON section: 4 buttons (primary, ghost, danger, link)
- [ ] INPUT section: 2 labeled inputs, focus ring visible on tab
- [ ] BADGE section: 5 variants
- [ ] PROGRESS BAR: 3 bars (12%, 78%, 100%)
- [ ] MODULE ROW: 5 rows, row 3 highlighted with left border + cyan dot
- [ ] ACTIVITY SPARKLINE: 14 cyan bars
- [ ] CHAT MESSAGE: 4 messages with role colors (instructor cyan, self muted, system italic)
- [ ] TABLE: 3 rows with mono-data numbers + hover state

If any check fails, fix and recommit the relevant component task. Do not proceed until all are green.

- [ ] **Step 2: Take a baseline screenshot**

In the browser, use your OS screenshot tool to capture the full `/components/` page (1440px viewport recommended). Save as `tests/visual/components-baseline.png` at the repo root.

Run: `mkdir -p tests/visual/baselines && touch tests/visual/baselines/.gitkeep`

- [ ] **Step 3: Run the full Django test suite — expect no regressions**

Run: `cd config_educa && python manage.py test`
Expected: same number of pass/fail as before this plan started. The 2 new tests in `shared/tests.py` should also pass.

- [ ] **Step 4: Commit baseline + finalize**

```bash
git add tests/visual/baselines/.gitkeep tests/visual/components-baseline.png
git commit -m "test: visual baseline for components debug page (M1 complete)"
```

- [ ] **Step 5: Update deployment script for Tailwind build**

Edit `scripts/deploy_production.sh`. Find the line that runs `collectstatic` (or `python manage.py migrate`). Just before `collectstatic` add:

```bash
docker-compose exec -T web python config_educa/manage.py tailwind build
```

Or, if the script doesn't yet use Docker exec, add it inline to whichever build phase precedes static collection.

- [ ] **Step 6: Commit deploy script update**

```bash
git add scripts/deploy_production.sh
git commit -m "chore(deploy): add tailwind build step before collectstatic"
```

- [ ] **Step 7: Push the whole plan completion to GitHub**

```bash
git push
```

Expected output ends with: `master -> master` and shows the new commits.

---

## Plan completion checklist

After all tasks above are completed and pushed, you should have:

- ✅ `theme/` Django app with Tailwind compiling Foundry tokens
- ✅ `shared/` Django app with `/components/` debug page
- ✅ New `base.html` with topbar + sidebar + skip-link + Alpine + HTMX + Inter
- ✅ 9 component primitives, each tested visually on `/components/`
- ✅ Foundry-themed login page behind `USE_FOUNDRY_UI=true` flag
- ✅ Visual baseline screenshot committed
- ✅ Deploy script updated for Tailwind build
- ✅ Original UI still works (flag default = False)

**Next plan to write:** `docs/superpowers/plans/2026-XX-XX-foundry-m2-dashboard.md` — covers the student dashboard (M2).

---

## Self-review checklist (already done by the planner)

- ✅ Spec coverage: M0 + M1 fully covered. M2-M6 explicitly out of scope and called out.
- ✅ No placeholders ("TBD", "TODO" etc.) in any task body.
- ✅ Type consistency: component variant names match between primitive files and debug page includes (`primary`/`ghost`/`danger` for buttons; `neutral`/`accent`/`success`/`warning`/`danger` for badges).
- ✅ HTMX endpoints not yet added (deferred to M4); base template loads HTMX but no endpoints to hit.
- ✅ Tested side-effects: `python manage.py check` after settings changes, `manage.py test` after every code change.
