"""
=============================================================================
NGHIEM THU: P2-26 (Embedding Pipeline) & P3-01 (ORM Unification)
=============================================================================
Chay: d:\aegis-o2o\.venv\Scripts\python.exe scripts/test_p226_p301_acceptance.py
Yeu cau: DB dang chay va da migrate xong (alembic upgrade head)

NOTE: Script nay chi kiem tra file-system + DB truc tiep.
      Khong import Celery worker de tranh load CLIP model (ton ~400MB + 30s).
=============================================================================
"""
import sys
import os
import ast
import traceback

# Fix encoding on Windows terminal (cp1252 -> utf-8)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Them backend vao PYTHONPATH
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

# Set env truoc khi import bat ky app module nao
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

PASS = "[PASS]"
FAIL = "[FAIL]"
INFO = "[INFO]"

results = {}
_total = 0
_passed = 0


def print_header(title: str):
    print(f"\n{'='*65}")
    print(f"  {title}")
    print(f"{'='*65}")


def record(name: str, ok: bool, detail: str = ""):
    global _total, _passed
    _total += 1
    if ok:
        _passed += 1
    status = PASS if ok else FAIL
    print(f"  {status}  {name}")
    if detail:
        print(f"           => {detail}")
    return ok


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS: Doc file nhu AST hoac text — KHONG import Celery/workers
# ─────────────────────────────────────────────────────────────────────────────

def read_file(rel_path: str) -> str:
    path = os.path.join(BACKEND_DIR, rel_path)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def file_exists(rel_path: str) -> bool:
    return os.path.exists(os.path.join(BACKEND_DIR, rel_path))


# ─────────────────────────────────────────────────────────────────────────────
# P3-01: ORM UNIFICATION
# ─────────────────────────────────────────────────────────────────────────────

def test_p301():
    print_header("P3-01: ORM Unification (SQLModel + SQLAlchemy Base)")

    # 1. Alembic env.py dung dual metadata
    env = read_file("app/alembic/env.py")
    ok = "target_metadata = [SQLModel.metadata, Base.metadata]" in env
    results["p301_alembic_dual_metadata"] = record(
        "Alembic env.py dung target_metadata = [SQLModel.metadata, Base.metadata]",
        ok,
        "OK" if ok else "THIEU! Them vao env.py"
    )

    # 2. env.py import ca SQLModel lan Base
    ok = ("from app.models import SQLModel" in env and
          "from app.db.session import Base" in env)
    results["p301_alembic_imports"] = record(
        "Alembic env.py import ca SQLModel va Base",
        ok,
        "OK" if ok else "THIEU import"
    )

    # 3. env.py import tat ca domain models
    ok = ("from app.domains.culture import model" in env and
          "from app.domains.inventory import model" in env and
          "from app.domains.vision import model" in env)
    results["p301_domain_imports"] = record(
        "Alembic env.py import tat ca domain models (culture, inventory, vision)",
        ok,
        "OK" if ok else "Co domain chua duoc import"
    )

    # 4. models.py co doc Architecture Decision
    models = read_file("app/models.py")
    ok = "ARCHITECTURE DECISION" in models and "SQLAlchemy Base" in models
    results["p301_architecture_doc"] = record(
        "models.py co khoi tai lieu Architecture Decision",
        ok,
        "Developer guide documented" if ok else "THIEU tai lieu!"
    )

    # 5. Domain moi dung SQLAlchemy Base, KHONG dung SQLModel
    domain_checks = {
        "app/domains/inventory/model.py": "inventory",
        "app/domains/vision/model.py":    "vision",
        "app/domains/culture/model.py":   "culture",
    }
    all_ok = True
    for rel_path, name in domain_checks.items():
        content = read_file(rel_path)
        uses_sqlmodel = ("from sqlmodel" in content or "import sqlmodel" in content.lower())
        uses_base = "from app.db.session import Base" in content
        ok = (not uses_sqlmodel) and uses_base
        all_ok = all_ok and ok
        results[f"p301_domain_{name}"] = record(
            f"  {name}/model.py: SQLAlchemy Base (khong SQLModel)",
            ok,
            "OK" if ok else "SAI pattern!"
        )

    # 6. db/session.py dinh nghia Base dung cach
    session = read_file("app/db/session.py")
    ok = ("declarative_base()" in session and
          "Base = declarative_base()" in session and
          "SessionLocal = sessionmaker(" in session)
    results["p301_session_base"] = record(
        "app/db/session.py dinh nghia Base va SessionLocal dung cach",
        ok,
        "OK" if ok else "THIEU Base hoac SessionLocal"
    )


# ─────────────────────────────────────────────────────────────────────────────
# P2-26: EMBEDDING PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def test_p226_static():
    print_header("P2-26: Embedding Pipeline — Kiem tra File (static)")

    # 1. Product model co cot embedding_status
    inv_model = read_file("app/domains/inventory/model.py")
    ok = ('embedding_status' in inv_model and
          'Vector(512)' in inv_model and
          '"pending"' in inv_model)
    results["p226_model_embedding_status"] = record(
        "Product model co cot embedding (Vector512) va embedding_status",
        ok,
        "embedding_status = mapped_column(String(50), default='pending') found" if ok else "THIEU!"
    )

    # 2. ProductResponse schema co embedding_status
    schema = read_file("app/domains/inventory/schema.py")
    ok = "embedding_status" in schema and "Optional[str]" in schema
    results["p226_schema_field"] = record(
        "ProductResponse schema expose truong embedding_status",
        ok,
        "OK" if ok else "THIEU trong schema.py!"
    )

    # 3. Migration file ton tai va dung noi dung
    mig_path = "app/alembic/versions/e3d8f2a1b5c6_add_embedding_status_to_product.py"
    exists = file_exists(mig_path)
    results["p226_migration_exists"] = record(
        "Migration file e3d8f2a1b5c6 ton tai",
        exists,
        mig_path if exists else "KHONG TIM THAY file!"
    )
    if exists:
        mig = read_file(mig_path)
        ok = ("add_column" in mig and
              "embedding_status" in mig and
              "down_revision = '1a2b3c4d5e6f'" in mig)  # End of existing chain
        results["p226_migration_content"] = record(
            "  Migration: add_column embedding_status + down_revision dung",
            ok,
            "OK" if ok else "Noi dung sai!"
        )

    # 4. generate_product_embedding task
    vt = read_file("workers/ai_worker/vision_tasks.py")
    ok = ('name="workers.ai_worker.vision_tasks.generate_product_embedding"' in vt and
          "def generate_product_embedding(product_id: int):" in vt and
          "requests.get(product.image_url" in vt and
          'embedding_status = "completed"' in vt and
          'embedding_status = "failed"' in vt)
    results["p226_generate_task"] = record(
        "Task generate_product_embedding: dinh nghia + http fetch + status update",
        ok,
        "All logic present" if ok else "THIEU logic!"
    )

    # 5. sync_missing_product_embeddings task
    ok = ('name="workers.ai_worker.vision_tasks.sync_missing_product_embeddings"' in vt and
          "def sync_missing_product_embeddings():" in vt and
          'embedding_status == "pending"' in vt and
          "generate_product_embedding.delay(p.product_id)" in vt)
    results["p226_sync_task"] = record(
        "Task sync_missing_product_embeddings: quet pending/failed va enqueue",
        ok,
        "OK" if ok else "THIEU logic!"
    )

    # 6. Celery Beat Schedule co cronjob moi 5 phut
    ca = read_file("workers/ai_worker/celery_app.py")
    ok = ("sync-missing-product-embeddings-every-5-minutes" in ca and
          "workers.ai_worker.vision_tasks.sync_missing_product_embeddings" in ca and
          "crontab(minute='*/5')" in ca)
    results["p226_celery_beat"] = record(
        "Celery Beat Schedule: sync embedding moi 5 phut (crontab minute='*/5')",
        ok,
        "OK" if ok else "THIEU hoac sai schedule!"
    )

    # 7. celery_app.py include vision_tasks
    ok = "'workers.ai_worker.vision_tasks'" in ca
    results["p226_celery_include"] = record(
        "celery_app.py include 'workers.ai_worker.vision_tasks'",
        ok,
        "OK" if ok else "THIEU include!"
    )

    # 8. compose.yml co ai_beat service
    compose = read_file("../compose.yml")
    ok = "ai_beat:" in compose and "celery.*beat" in compose or "celery" in compose and "beat" in compose
    results["p226_compose_beat"] = record(
        "compose.yml co service ai_beat (Celery Beat scheduler)",
        ok,
        "ai_beat service found" if ok else "KHONG co ai_beat trong compose!"
    )


def test_p226_live_db():
    print_header("P2-26: LIVE DATABASE CHECKS (can DB dang chay)")

    try:
        # Import nhe — chi dung sqlalchemy core, tranh import Celery
        from sqlalchemy import create_engine, text, inspect
        # Import config truc tiep
        from app.core.config import settings
        engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI),
                               pool_pre_ping=True, connect_args={"connect_timeout": 5})

        with engine.connect() as conn:
            # 1. Column embedding_status ton tai
            row = conn.execute(text("""
                SELECT column_name, data_type, character_maximum_length
                FROM information_schema.columns
                WHERE table_name = 'products' AND column_name = 'embedding_status'
            """)).fetchone()
            ok = row is not None
            results["p226_db_column"] = record(
                "LIVE DB: Cot 'embedding_status' trong table products",
                ok,
                f"Type: {row[1]}, MaxLen: {row[2]}" if ok else "CHUA TON TAI — Chay: alembic upgrade head"
            )

            # 2. Vector column ton tai
            vrow = conn.execute(text("""
                SELECT column_name, udt_name
                FROM information_schema.columns
                WHERE table_name = 'products' AND column_name = 'embedding'
            """)).fetchone()
            ok = vrow is not None
            results["p226_db_vector"] = record(
                "LIVE DB: Cot 'embedding' (vector) trong table products",
                ok,
                f"UDT: {vrow[1]}" if ok else "CHUA TON TAI!"
            )

            # 3. Thong ke embedding_status
            rows = conn.execute(text("""
                SELECT COALESCE(embedding_status, 'NULL') as status,
                       COUNT(*) as cnt
                FROM products
                GROUP BY embedding_status
                ORDER BY cnt DESC
            """)).fetchall()
            print(f"\n  {INFO}  Thong ke embedding_status trong DB:")
            total_prod = 0
            for r in rows:
                tag = "[OK]" if r[0] == "completed" else ("[ERR]" if r[0] == "failed" else "[WAIT]")
                print(f"           {tag} {r[0]}: {r[1]} san pham")
                total_prod += r[1]
            if not rows:
                print(f"           (Table products trong — chua co du lieu)")

            # 4. Backlog: san pham co anh nhung chua co vector
            count = conn.execute(text("""
                SELECT COUNT(*) FROM products
                WHERE image_url IS NOT NULL
                  AND (embedding IS NULL OR embedding_status != 'completed')
            """)).scalar()
            ok = count is not None
            results["p226_db_backlog"] = record(
                f"LIVE DB: San pham cho pipeline xu ly",
                ok,
                f"{count} san pham co anh nhung chua co embedding (pipeline se xu ly tu dong)"
                if ok else "Loi query"
            )

            # 5. Migration da chay (kiem tra alembic_version)
            mig_rows = conn.execute(text(
                "SELECT version_num FROM alembic_version"
            )).fetchall()
            versions = [r[0] for r in mig_rows]
            has_embed_migration = "e3d8f2a1b5c6" in versions
            # Head migration can be any of the latest ones
            print(f"\n  {INFO}  Alembic version hien tai: {versions}")
            results["p226_db_migration_head"] = record(
                "LIVE DB: Migration e3d8f2a1b5c6 (embedding_status) da chay",
                has_embed_migration,
                "OK — column da duoc apply" if has_embed_migration
                else "CHUA — Chay: alembic upgrade head"
            )

    except Exception as e:
        err = str(e)
        print(f"\n  {INFO}  Khong ket duoc DB: {err}")
        for key in ["p226_db_column", "p226_db_vector", "p226_db_backlog", "p226_db_migration_head"]:
            results[key] = record(
                f"LIVE DB ({key}): Khong ket duoc DB",
                False,
                err[:120]
            )


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def print_summary():
    print_header("TONG KET NGHIEM THU")

    p301_keys = [k for k in results if k.startswith("p301")]
    p226_keys = [k for k in results if k.startswith("p226")]

    p301_pass = sum(1 for k in p301_keys if results[k])
    p226_pass = sum(1 for k in p226_keys if results[k])

    print(f"\n  P3-01 ORM Unification  :  {p301_pass}/{len(p301_keys)} tests passed")
    print(f"  P2-26 Embedding Pipeline:  {p226_pass}/{len(p226_keys)} tests passed")
    print(f"\n  TONG: {_passed}/{_total} tests passed", end="  ")

    failed = _total - _passed
    if failed == 0:
        print("=> NGHIEM THU DAT!")
    else:
        print(f"=> {failed} FAILED")
        print("\n  Tests FAILED:")
        for k, v in results.items():
            if not v:
                print(f"    [FAIL] {k}")
    print()
    return failed == 0


if __name__ == "__main__":
    test_p301()
    test_p226_static()
    test_p226_live_db()
    ok = print_summary()
    sys.exit(0 if ok else 1)
