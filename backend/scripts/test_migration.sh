#!/usr/bin/env bash
set -e

echo "======================================"
echo " AEGIS Migration Test - Empty DB Check"
echo "======================================"

echo "[1/4] Waiting for DB..."
python app/backend_pre_start.py

echo "[2/4] Running: alembic upgrade head..."
alembic upgrade head
echo "      Migration complete."

echo "[3/4] Verifying tables and patched columns..."
python - <<'PYEOF'
from sqlalchemy import create_engine, inspect
import os

url = (
    f"postgresql+psycopg://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
    f"@{os.environ['POSTGRES_SERVER']}:{os.environ.get('POSTGRES_PORT','5432')}/{os.environ['POSTGRES_DB']}"
)
engine = create_engine(url)
inspector = inspect(engine)
tables = sorted(inspector.get_table_names())

expected_tables = [
    "user", "item",
    "places", "reviews",
    "stores", "products",
    "inventory", "inventory_locks", "orders",
    "vision_tasks", "virtual_closets",
]

print(f"  Tables found ({len(tables)}): {tables}")
missing = [table for table in expected_tables if table not in tables]
if missing:
    raise SystemExit(f"FAIL - missing tables: {missing}")
print(f"  PASS - all {len(expected_tables)} expected tables present.")

expected_columns = {
    "inventory_locks": {"store_id"},
    "inventory": {"price_override"},
}
for table, columns in expected_columns.items():
    found = {column["name"] for column in inspector.get_columns(table)}
    missing_columns = sorted(columns - found)
    if missing_columns:
        raise SystemExit(f"FAIL - missing columns on {table}: {missing_columns}")
print("  PASS - expected schema patch columns present.")
PYEOF

echo "[4/4] Verifying extensions..."
python - <<'PYEOF'
from sqlalchemy import create_engine, text
import os

url = (
    f"postgresql+psycopg://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
    f"@{os.environ['POSTGRES_SERVER']}:{os.environ.get('POSTGRES_PORT','5432')}/{os.environ['POSTGRES_DB']}"
)
engine = create_engine(url)
with engine.connect() as conn:
    rows = conn.execute(text("SELECT extname FROM pg_extension ORDER BY extname")).fetchall()
    extensions = [row[0] for row in rows]

expected_extensions = ["pg_trgm", "postgis", "uuid-ossp", "vector"]
print(f"  Extensions found: {extensions}")
missing = [extension for extension in expected_extensions if extension not in extensions]
if missing:
    raise SystemExit(f"FAIL - missing extensions: {missing}")
print("  PASS - all required extensions present.")
PYEOF

echo ""
echo "======================================"
echo " ALL CHECKS PASSED"
echo "======================================"
