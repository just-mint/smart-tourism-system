#!/usr/bin/env bash
set -e

echo "======================================"
echo " AEGIS Migration Test — P0-03 Check"
echo "======================================"

# 1. Wait for DB
echo "[1/4] Waiting for DB..."
python app/backend_pre_start.py

# 2. Run migrations
echo "[2/4] Running: alembic upgrade head..."
alembic upgrade head
echo "      Migration complete."

# 3. Check all expected tables exist
echo "[3/4] Verifying tables..."
python - <<'PYEOF'
from sqlalchemy import create_engine, inspect, text
import os

url = (
    f"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
    f"@{os.environ['POSTGRES_SERVER']}:{os.environ.get('POSTGRES_PORT','5432')}/{os.environ['POSTGRES_DB']}"
)
engine = create_engine(url)
tables = sorted(inspect(engine).get_table_names())

EXPECTED = [
    "user", "item",
    "places", "reviews",
    "stores", "products",
    "inventory", "inventory_locks", "orders",
    "vision_tasks", "virtual_closets",
]

print(f"  Tables found ({len(tables)}): {tables}")
missing = [t for t in EXPECTED if t not in tables]
if missing:
    print(f"  FAIL — Missing tables: {missing}")
    exit(1)
else:
    print(f"  PASS — All {len(EXPECTED)} expected tables present.")
PYEOF

# 4. Check extensions
echo "[4/4] Verifying extensions..."
python - <<'PYEOF'
from sqlalchemy import create_engine, text
import os

url = (
    f"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
    f"@{os.environ['POSTGRES_SERVER']}:{os.environ.get('POSTGRES_PORT','5432')}/{os.environ['POSTGRES_DB']}"
)
engine = create_engine(url)
with engine.connect() as conn:
    rows = conn.execute(text("SELECT extname FROM pg_extension ORDER BY extname")).fetchall()
    exts = [r[0] for r in rows]

EXPECTED_EXT = ["pg_trgm", "postgis", "uuid-ossp", "vector"]
print(f"  Extensions found: {exts}")
missing = [e for e in EXPECTED_EXT if e not in exts]
if missing:
    print(f"  FAIL — Missing extensions: {missing}")
    exit(1)
else:
    print(f"  PASS — All required extensions present.")
PYEOF

echo ""
echo "======================================"
echo " ALL CHECKS PASSED"
echo "======================================"
