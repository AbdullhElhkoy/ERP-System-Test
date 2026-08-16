#!/usr/bin/env bash
set -e

# اكتشاف مسار workspace تلقائياً
WS_DIR="$(pwd)"
if [ -d "$WS_DIR/backend" ]; then
  BACKEND_DIR="$WS_DIR/backend"
else
  BACKEND_DIR="$WS_DIR/workspaces/ERP-System-Test/backend"
fi
cd "$BACKEND_DIR"

# تثبيت المتطلبات
pip install --no-cache-dir -r requirements.txt

# التأكد من أن PostgreSQL يعمل
sudo service postgresql start

# إنشاء قاعدة البيانات والمستخدم إن لم يكونا موجودين
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='chemflow_user'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE USER chemflow_user WITH PASSWORD 'ChemFlowSecure2026!!';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='chemflow_db'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE DATABASE chemflow_db OWNER chemflow_user;"
python manage.py migrate
python manage.py check

echo "=========================================="
echo "Setup complete. Run the server with:"
echo "  python manage.py runserver 0.0.0.0:8000"
echo "=========================================="
