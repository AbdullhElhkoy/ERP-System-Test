#!/usr/bin/env bash
set -e

# منع أي استعلام تفاعلي من apt/debconf (سبب التجمد الشائع في Codespaces)
export DEBIAN_FRONTEND=noninteractive
export TZ=Etc/UTC

# === هل نحن root؟ ===
IS_ROOT=0
if [ "$(id -u)" = "0" ]; then
  IS_ROOT=1
fi

# نتجنّب شكوى git عن ملكية المجلد عند العمل كـ root
if [ "$IS_ROOT" = "1" ]; then
  git config --global --add safe.directory '*' || true
fi

# sudo -n فقط (لا يطلب كلمة مرور أبداً)
SUDO_N=""
if [ "$IS_ROOT" = "0" ] && command -v sudo >/dev/null 2>&1; then
  SUDO_N="sudo -n "
fi

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

# === PostgreSQL: التثبيت اليدوي (بديل عن feature الذي لا يعمل في Codespaces) ===
if ! command -v psql >/dev/null 2>&1; then
  echo "Installing PostgreSQL (apt)..."
  ${SUDO_N}apt-get update -y
  ${SUDO_N}apt-get install -y postgresql postgresql-contrib libpq-dev gcc python3-dev
else
  # psql موجود لكن قد ننقص libpq-dev للـ psycopg2
  ${SUDO_N}apt-get install -y libpq-dev gcc python3-dev
fi
# بدء PostgreSQL بأكثر من طريقة (حسب نوع الحاوية)
echo "Starting PostgreSQL..."
if command -v service >/dev/null 2>&1; then
  ${SUDO_N}service postgresql start || true
elif command -v pg_ctlcluster >/dev/null 2>&1; then
  ${SUDO_N}pg_ctlcluster 15 main start || ${SUDO_N}pg_ctlcluster 14 main start || true
elif command -v pg_ctl >/dev/null 2>&1; then
  PGDATA=$(ls -d /var/lib/postgresql/*/main 2>/dev/null | head -1)
  if [ -n "$PGDATA" ]; then
    ${SUDO_N}pg_ctl -D "$PGDATA" -l /tmp/postgres.log start || true
  fi
fi

# الانتظار حتى يصبح PostgreSQL جاهزاً (بحد أقصى 30 ثانية)
for i in $(seq 1 30); do
  if ${SUDO_N}pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
    echo "PostgreSQL is ready."
    break
  fi
  sleep 1
done

# إنشاء قاعدة البيانات والمستخدم إن لم يكونا موجودين
# بدون sudo: لو كنا root نستخدم runuser، وإلا نعتمد على أن pg_hba يسمح للمستخدم الحالي
POSTGRES="psql -U postgres -h localhost"
if [ "$IS_ROOT" = "1" ]; then
  POSTGRES="runuser -u postgres -- psql"
elif command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
  POSTGRES="sudo -n -u postgres psql"
fi
set +e
$POSTGRES -tc "SELECT 1 FROM pg_roles WHERE rolname='chemflow_user'" | grep -q 1 || \
  $POSTGRES -c "CREATE USER chemflow_user WITH PASSWORD 'ChemFlowSecure2026!!';"
$POSTGRES -tc "SELECT 1 FROM pg_database WHERE datname='chemflow_db'" | grep -q 1 || \
  $POSTGRES -c "CREATE DATABASE chemflow_db OWNER chemflow_user;"
set -e

# === تثبيت المتطلبات (نفضّل الـ venv داخل backend لو موجود، وإلا ننشئ واحداً) ===
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

# === تشغيل migrations ===
$PY manage.py migrate
$PY manage.py check

echo "=========================================="
echo "Setup complete. Run the server with:"
echo "  cd $BACKEND_DIR && $PY manage.py runserver 0.0.0.0:8000"
echo "=========================================="
