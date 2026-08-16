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
# نفضّل الـ venv داخل backend لو موجود، وإلا ننشئ واحداً
PY="python"
if [ -x "$BACKEND_DIR/venv/bin/python" ]; then
  PY="$BACKEND_DIR/venv/bin/python"
  echo "Using existing venv: $PY"
else
  echo "Creating venv..."
  python -m venv "$BACKEND_DIR/venv"
  PY="$BACKEND_DIR/venv/bin/python"
  echo "Using new venv: $PY"
fi
$PY -m pip install --no-cache-dir -r requirements.txt
$PY -c "import django; print('Django', django.get_version())"

SUDO=""
if command -v sudo >/dev/null 2>&1; then
  SUDO="sudo "
fi

# التأكد من أن PostgreSQL يعمل - بأكثر من طريقة (حسب نوع الحاوية)
echo "Starting PostgreSQL..."
if command -v service >/dev/null 2>&1; then
  ${SUDO}service postgresql start || true
elif command -v pg_ctlcluster >/dev/null 2>&1; then
  ${SUDO}pg_ctlcluster 15 main start || ${SUDO}pg_ctlcluster 14 main start || true
elif command -v pg_ctl >/dev/null 2>&1; then
  PGDATA=$(ls -d /var/lib/postgresql/*/main 2>/dev/null | head -1)
  if [ -n "$PGDATA" ]; then
    ${SUDO}pg_ctl -D "$PGDATA" -l /tmp/postgres.log start || true
  fi
fi

# الانتظار حتى يصبح PostgreSQL جاهزاً (بحد أقصى 20 ثانية)
for i in $(seq 1 20); do
  if ${SUDO}pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
    echo "PostgreSQL is ready."
    break
  fi
  sleep 1
done

# إنشاء قاعدة البيانات والمستخدم إن لم يكونا موجودين
POSTGRES="sudo -u postgres psql"
if ! command -v sudo >/dev/null 2>&1; then
  POSTGRES="psql -U postgres"
fi
$POSTGRES -tc "SELECT 1 FROM pg_roles WHERE rolname='chemflow_user'" | grep -q 1 || \
  $POSTGRES -c "CREATE USER chemflow_user WITH PASSWORD 'ChemFlowSecure2026!!';"
$POSTGRES -tc "SELECT 1 FROM pg_database WHERE datname='chemflow_db'" | grep -q 1 || \
  $POSTGRES -c "CREATE DATABASE chemflow_db OWNER chemflow_user;"

# التأكد من أن متغيرات البيئة موجودة (إن لم تكن، استخدم القيم الافتراضية من settings.py)
export DB_HOST="${DB_HOST:-localhost}"
export DB_NAME="${DB_NAME:-chemflow_db}"
export DB_USER="${DB_USER:-chemflow_user}"
export DB_PASSWORD="${DB_PASSWORD:-ChemFlowSecure2026!!}"

$PY manage.py migrate
$PY manage.py check

echo "=========================================="
echo "Setup complete. Run the server with:"
echo "  cd $BACKEND_DIR && $PY manage.py runserver 0.0.0.0:8000"
echo "=========================================="
