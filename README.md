# AEGIS O2O

AEGIS O2O is a smart tourism and online-to-offline commerce platform. It combines spatial search, route planning, culture/heritage content, inventory locking, checkout flows, and AI-assisted product discovery in one FastAPI + React codebase.

## What Is Inside

- Spatial discovery: nearby places and stores with PostGIS geometry queries.
- Smart itinerary planner: ranks stores, optimizes the route, and enriches each stop with products.
- Inventory and O2O checkout: stock by store, soft locks, store-specific pricing, and order creation.
- Vision and closet: upload images, detect/organize closet items, and mix-and-match products.
- Culture and heritage: place detail, AI story generation, reviews, and contextual tourism data.
- Optimization service: independent FastAPI service for ranking and TSP route optimization.
- Background workers: Celery workers for AI, vision, inventory, and context tasks.
- Admin/auth baseline: users, login, settings, admin table, and item CRUD from the original full-stack template.

## Stack

- Backend: FastAPI, SQLModel/SQLAlchemy, Alembic, PostgreSQL, PostGIS, pgvector, Redis, Celery.
- Frontend: React, Vite, TypeScript, TanStack Router, TanStack Query, Tailwind CSS, Radix UI, Leaflet, Playwright.
- Tooling: `uv` for Python, Bun for frontend dependencies, Docker Compose for local infrastructure.

## Repository Layout

```text
.
├── backend/
│   ├── app/                      # Main FastAPI API
│   ├── app/domains/              # Agent, culture, inventory, planner, spatial, vision
│   ├── app/alembic/              # Database migrations
│   ├── optimization_service/     # Ranking and route optimization microservice
│   ├── workers/                  # Celery workers and beat tasks
│   └── scripts/                  # Backend maintenance/test scripts
├── frontend/
│   ├── src/routes/               # App pages
│   ├── src/components/           # Shared UI and feature components
│   ├── src/client/               # OpenAPI/generated API client plus local wrapper
│   └── tests/                    # Playwright specs
├── scripts/                      # Cross-project data/vector/client utilities
├── compose.yml                   # Main local/prod-ish stack
├── compose.override.yml          # Local development overrides
└── .env.example                  # Environment template
```

## Prerequisites

- Docker and Docker Compose.
- Python 3.10+ and `uv`.
- Bun.

## Environment

Create the local environment file from the template:

```bash
cp .env.example .env
```

For local development, update at least these values:

- `SECRET_KEY`
- `FIRST_SUPERUSER`
- `FIRST_SUPERUSER_PASSWORD`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `INTERNAL_SECRET_KEY`
- `GEMINI_API_KEY` if the AI features need a real Gemini key

The backend reads the repository-level `.env` file, so commands can be run from either the repository root or `backend/`.

## Run With Docker Compose

Start the full stack:

```bash
docker compose up --build
```

Useful local URLs:

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Backend OpenAPI: http://localhost:8000/docs
- Optimization service: http://localhost:8002
- Adminer: http://localhost:8080
- Redis: `localhost:6380` from the override file

To run worker services too:

```bash
docker compose --profile worker up --build
```

## Run Locally For Development

Start infrastructure:

```bash
docker compose up -d db redis rabbitmq
```

Run the backend API:

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run fastapi dev app/main.py
```

Run the optimization service in another terminal:

```bash
cd backend
uv run uvicorn optimization_service.main:app --reload --port 8001
```

Run the frontend:

```bash
cd frontend
bun install
bun run dev
```

## Common Commands

```bash
# Backend tests
uv run --project backend pytest

# Backend lint for changed Python files or the full backend
uv run --project backend ruff check backend

# Frontend lint from repo root
npm run lint

# Frontend production build
cd frontend && bun run build

# Regenerate frontend API client after backend schema changes
bash scripts/generate-client.sh
```

## Data And Maintenance Scripts

- `backend/scripts/seed_stores.py`: seed store/place data.
- `backend/scripts/upgrade_products.py`: product maintenance helper.
- `scripts/seed_github_products.py`: import product/store SQL data from the configured GitHub source.
- `scripts/sync_product_vectors.py`: generate CLIP embeddings for products.
- `scripts/db_audit.py`: quick database audit for product embeddings.

Runtime uploads are stored under `backend/uploads/` and are intentionally ignored by Git.

## Documentation

- Backend guide: [backend/README.md](backend/README.md)
- Frontend guide: [frontend/README.md](frontend/README.md)
- Security notes: [SECURITY.md](SECURITY.md)
- Audit notes, if you need the historical review: [aegis_o2o_audit.md](aegis_o2o_audit.md)

## License

This project is licensed under the MIT license. See [LICENSE](LICENSE).
