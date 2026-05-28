#!/usr/bin/env bash
# Bootstrap the Foundry UI (M0 + M1) end-to-end.
# Run this once from the repo root after pulling the feature/foundry-foundation branch.
#
# What it does:
#  1. Install Python deps (django-tailwind, django-htmx) into the active venv
#  2. Install npm deps for the theme app
#  3. Build the Tailwind CSS bundle
#  4. Run the test suite to verify nothing broke
#  5. Print next-step instructions

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# --- Python venv detection ---------------------------------------------------
PYTHON_BIN=""
for candidate in \
  ../educto-cv-venv-LOCAL-ONLY/bin/python \
  ../educto-venv-LOCAL-ONLY/bin/python \
  config_educa/venv/bin/python \
  venv/bin/python \
  ; do
  if [[ -x "$candidate" ]]; then PYTHON_BIN="$candidate"; break; fi
done
if [[ -z "$PYTHON_BIN" ]]; then PYTHON_BIN="$(command -v python3)"; fi
echo "→ Using Python: $PYTHON_BIN"
"$PYTHON_BIN" --version

# --- 1. Python deps ----------------------------------------------------------
echo ""
echo "=== [1/4] Install Python deps =============================================="
"$PYTHON_BIN" -m pip install --quiet django-tailwind==3.8.0 django-htmx==1.19.0
"$PYTHON_BIN" -c "import tailwind, django_htmx; print('  ✓ tailwind + django_htmx import OK')"

# --- 2. npm deps -------------------------------------------------------------
echo ""
echo "=== [2/4] Install npm deps (theme) ========================================="
if ! command -v npm >/dev/null 2>&1; then
  echo "  ✗ npm not found in PATH. Install Node.js first: https://nodejs.org/"
  exit 1
fi
pushd config_educa/theme/static_src >/dev/null
npm install --silent --no-audit --no-fund
echo "  ✓ npm install complete"
popd >/dev/null

# --- 3. Build Tailwind CSS ---------------------------------------------------
echo ""
echo "=== [3/4] Build Tailwind CSS bundle ========================================"
pushd config_educa/theme/static_src >/dev/null
npm run build
popd >/dev/null
CSS_OUT="config_educa/theme/static/css/dist/styles.css"
if [[ -f "$CSS_OUT" ]]; then
  echo "  ✓ Bundle written: $CSS_OUT ($(wc -c <"$CSS_OUT") bytes)"
else
  echo "  ✗ Bundle missing at $CSS_OUT"
  exit 1
fi

# --- 4. Django test suite ----------------------------------------------------
echo ""
echo "=== [4/4] Run Django test suite ============================================"
pushd config_educa >/dev/null
"$PYTHON_BIN" manage.py check
"$PYTHON_BIN" manage.py test shared courses students --keepdb || true
popd >/dev/null

# --- Done --------------------------------------------------------------------
cat <<'EOF'

============================================================================
  Foundry UI foundation bootstrap complete.
============================================================================

Next steps:

  1. Run the dev server with the Foundry flag ON:
       cd config_educa
       USE_FOUNDRY_UI=true python manage.py runserver

  2. Open http://127.0.0.1:8000/components/ to see all primitives rendered.

  3. Open http://127.0.0.1:8000/accounts/login/ to see the Foundry-styled login.

  4. (Optional) Download IBM Plex Mono fonts (Regular + Medium .woff2) into:
       config_educa/theme/static/fonts/
     Source: https://fonts.google.com/specimen/IBM+Plex+Mono
     Without them, the browser uses the next font in the mono stack.

  5. To toggle back to the old UI, leave USE_FOUNDRY_UI unset (or =false).

  6. For continuous CSS rebuilds during dev, in a second terminal:
       cd config_educa/theme/static_src && npm run start
EOF
