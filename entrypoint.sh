#!/bin/bash
set -e

echo "=== Warhammer Fantasy Professions Manager ==="
echo "Waiting for MySQL to be ready..."

until python -c "
import sys, os, re, pymysql
url = os.environ.get('DATABASE_URL', '')
m = re.match(r'mysql\+pymysql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', url)
if not m:
    sys.exit(1)
try:
    conn = pymysql.connect(host=m.group(3), user=m.group(1), password=m.group(2),
                           database=m.group(5), port=int(m.group(4)))
    conn.close()
except Exception:
    sys.exit(1)
"; do
    echo "Database not ready yet, retrying in 2s..."
    sleep 2
done

echo "Database is ready!"

echo "Creating/updating database tables..."
flask init-db

echo "Creating default admin user if needed..."
flask create-admin

echo "Starting application..."
exec gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 600 --access-logfile - --error-logfile - run:app
