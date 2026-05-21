# AEGIS O2O Backend

The backend contains the main FastAPI API, database models and migrations, the optimization microservice, and Celery workers.

## Main Responsibilities

- Authentication, users, admin operations, and item CRUD.
- Spatial queries over places and stores with PostGIS.
- Culture and heritage APIs for place detail, generated stories, and reviews.
- Inventory APIs for products, stores, price comparison, soft locks, and order creation.
- Vision APIs for scan uploads, closet uploads, and mix-and-match recommendations.
- Planner APIs that orchestrate spatial filtering, optimization, weather/context, and product enrichment.
- Worker processes for background AI, vision, inventory, and context jobs.

## Structure

```text
backend/
├── app/
│   ├── api/                     # Base auth/user/item/utils routers
│   ├── core/                    # Settings, security, DB bootstrap
│   ├── db/                      # SQLAlchemy session and Redis client
│   ├── domains/                 # AEGIS domain modules
│   ├── alembic/                 # Database migrations
│   ├── email-templates/         # Account/reset/test email templates
│   └── main.py                  # Main FastAPI app
├── optimization_service/        # Independent FastAPI optimization service
├── workers/                     # Celery workers and beat tasks
├── scripts/                     # Backend helper scripts
├── db/                          # Postgres image/init extension setup
└── tests/                       # Pytest suite
```

## Environment

The settings loader reads the repository-level `.env` file. Create it from the root template:

```bash
cp ../.env.example ../.env
```

Important local variables:

- `POSTGRES_SERVER`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `SECRET_KEY`
- `FIRST_SUPERUSER`, `FIRST_SUPERUSER_PASSWORD`
- `REDIS_URL`
- `RABBITMQ_URL`
- `OPTIMIZATION_SERVICE_URL`
- `OSRM_BASE_URL`
- `INTERNAL_SECRET_KEY`
- `GEMINI_API_KEY` for AI-backed features

## Local Development

Start database and infrastructure from the repository root:

```bash
docker compose up -d db redis rabbitmq
```

Install dependencies and migrate:

```bash
cd backend
uv sync
uv run alembic upgrade head
```

Run the main API:

```bash
uv run fastapi dev app/main.py
```

The API is available at:

- http://localhost:8000
- http://localhost:8000/docs
- http://localhost:8000/api/v1/openapi.json

Run the optimization service separately when testing planner flows outside Docker:

```bash
uv run uvicorn optimization_service.main:app --reload --port 8001
```

Run workers when background jobs are needed:

```bash
uv run celery -A workers.ai_worker.celery_app worker --loglevel=info
uv run celery -A workers.ai_worker.celery_app beat --loglevel=info
```

## Docker Compose

From the repository root:

```bash
docker compose up --build
```

The backend container runs migrations through the `prestart` service before the API starts. Local overrides expose:

- Main API: http://localhost:8000
- Optimization service: http://localhost:8002
- Adminer: http://localhost:8080
- MailCatcher: http://localhost:1080

## Migrations

Create a migration after model changes:

```bash
cd backend
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
```

Domain models live mainly under `app/domains/*/model.py`; base auth/item models live in `app/models.py`.

## Tests And Quality

```bash
# Full backend suite
uv run --project backend pytest

# Run through backend helper
cd backend && uv run bash scripts/tests-start.sh

# Ruff
uv run --project backend ruff check backend
```

The current test suite covers auth/users/items, pre-start checks, and the optimization service.

## Data Utilities

- `backend/scripts/seed_stores.py`: seed store data.
- `backend/scripts/fix_product_images.py`: repair product image URLs.
- `backend/scripts/upgrade_products.py`: product schema/data upgrade helper.
- `backend/scripts/test_migration.sh`: migration smoke test.
- `../scripts/seed_github_products.py`: import product/store data from the configured GitHub raw SQL source.
- `../scripts/sync_product_vectors.py`: generate CLIP embeddings for product image search.
- `../scripts/db_audit.py`: report embedding coverage.

## Uploads

Uploaded scan and closet images are stored in `backend/uploads/` at runtime. That directory is ignored by Git and should not contain committed user uploads.
