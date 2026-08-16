#!/usr/bin/env bash
set -e

# اكتشاف مسار workspace تلقائياً
for CAND in "$PWD" "$PWD/.." "$PWD/../.." /workspaces/* /workspaces/ERP-System-Test /workspaces/Default\ Project; do
  if [ -d "$CAND/backend" ]; then
    BACKEND_DIR="$CAND/backend"
    break
  fi
done
if [ -z "$BACKEND_DIR" ]; then
  echo "ERROR: could not locate backend directory" >&2
  exit 1
fi
echo "Backend dir: $BACKEND_DIR"
cd "$BACKEND_DIR"

# تثبيت المتطلبات (python -m pip يعمل حتى لو pip غير موجود في PATH)
# نفضّل الـ venv داخل backend لو موجود
PY="python"
if [ -x "$BACKEND_DIR/venv/bin/python" ]; then
  PY="$BACKEND_DIR/venv/bin/python"
  echo "Using venv: $PY"
fi
$PY -m pip install --no-cache-dir -r requirements.txt
$PY -c "import django; print('Django', django.get_version())"

SUDO=""
if command -v sudo >/dev/null 2>&1; then
  SUDO="sudo "
fi

# التأكد من أن PostgreSQL يعمل
${SUDO}service postgresql start || true

# إنشاء قاعدة البيانات والمستخدم إن لم يكونا موجودين
POSTGRES="sudo -u postgres psql"
if ! command -v sudo >/dev/null 2>&1; then
  POSTGRES="psql -U postgres"
fi
$POSTGRES -tc "SELECT 1 FROM pg_roles WHERE rolname='chemflow_user'" | grep -q 1 || \
  $POSTGRES -c "CREATE USER chemflow_user WITH PASSWORD 'ChemFlowSecure2026!!';"
$POSTGRES -tc "SELECT 1 FROM pg_database WHERE datname='chemflow_db'" | grep -q 1 || \
  $POSTGRES -c "CREATE DATABASE chemflow_db OWNER chemflow_user;"
$PY manage.py migrate
$PY manage.py check

echo "=========================================="
echo "Setup complete. Run the server with:"
echo "  $PY manage.py runserver 0.0.0.0:8000"
echo "=========================================="
