#!/usr/bin/env bash
set -e

echo "======================================"
echo " AEGIS Seed Test"
echo "======================================"

python app/initial_data.py

python - <<'PYEOF'
from sqlalchemy import create_engine, text
import os

url = (
    f"postgresql+psycopg://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
    f"@{os.environ['POSTGRES_SERVER']}:{os.environ.get('POSTGRES_PORT','5432')}/{os.environ['POSTGRES_DB']}"
)

engine = create_engine(url)
expected = {
    "places": 3,
    "stores": 3,
    "products": 4,
    "inventory": 12,
}

with engine.connect() as conn:
    for table, minimum in expected.items():
        count = conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
        print(f"  {table}: {count}")
        if count < minimum:
            raise SystemExit(f"FAIL - expected at least {minimum} rows in {table}")

    stores = conn.execute(
        text("SELECT count(*) FROM stores WHERE category = 'shopping' AND geom IS NOT NULL")
    ).scalar_one()
    if stores < expected["stores"]:
        raise SystemExit("FAIL - demo stores must be shopping stores with geometry")

print("PASS - seed data is present and queryable.")
PYEOF
