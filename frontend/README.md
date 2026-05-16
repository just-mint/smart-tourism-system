# AEGIS O2O Frontend

The frontend is a Vite + React + TypeScript app for the AEGIS O2O dashboard and tourism-commerce workflows.

## Main Screens

- Dashboard: entry point for authenticated users.
- Spatial Operations: map-based discovery of places and stores.
- Smart Planner: multi-stop itinerary planner with route geometry and product enrichment.
- Culture & Heritage: place detail, story, and review interactions.
- Inventory & O2O: stores, products, price comparison, stock locks, and checkout handoff.
- Vision & Closet: image scan, closet upload, mix-and-match, and store selection.
- Items, Settings, Admin: baseline account and admin workflows.

## Stack

- React 19 and TypeScript.
- Vite for development and production builds.
- TanStack Router for file-based routes.
- TanStack Query for server state.
- Tailwind CSS and Radix UI components.
- Leaflet and React Leaflet for maps.
- Biome for linting/formatting.
- Playwright for end-to-end tests.

## Environment

Local API URL is controlled by `VITE_API_URL`.

```env
VITE_API_URL=http://localhost:8000
```

The local default is stored in `frontend/.env`. Docker builds pass the same value through build args.

## Development

Install dependencies:

```bash
bun install
```

Start the dev server:

```bash
bun run dev
```

Open http://localhost:5173.

Make sure the backend API is also running at the URL configured in `VITE_API_URL`.

## Scripts

```bash
# Development server
bun run dev

# TypeScript compile plus production build
bun run build

# Biome lint/check
bun run lint

# Generate OpenAPI client from frontend/openapi.json
bun run generate-client

# Playwright tests
bun run test

# Playwright UI
bun run test:ui
```

From the repository root, `npm run lint` delegates to the frontend workspace lint script.

## API Client

Generated client files live under `src/client/`. The custom `src/client/aegis-api.ts` wrapper contains ergonomic calls used by newer AEGIS pages.

After backend schema changes:

```bash
cd ..
bash scripts/generate-client.sh
```

That script exports OpenAPI from the backend, regenerates the frontend client, and runs frontend lint.

## Route And Source Layout

```text
frontend/src/
├── routes/                  # Pages
├── components/              # Feature and shared UI components
├── components/ui/           # Reusable primitives
├── client/                  # Generated SDK and AEGIS wrapper
├── hooks/                   # Auth, toast, mobile, copy helpers
├── lib/                     # Shared utilities
└── main.tsx                 # App entry
```

## Testing

For Playwright, run the backend stack first:

```bash
docker compose up -d --wait backend frontend
```

Then:

```bash
bun run test
```

Use UI mode when debugging:

```bash
bun run test:ui
```

Reports and test artifacts are ignored by Git.

## Production Build

```bash
bun run build
```

The output is written to `frontend/dist/`, which is ignored by Git and served by the frontend Docker image.
