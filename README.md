# Momentum

A personal operating system for daily focus — not a task manager. Organize life into **streams**, queue **items**, and see what to do **today**.

## Stack

| Layer | Tech |
|-------|------|
| Frontend | React, TypeScript, Vite, Tailwind CSS, TanStack Query, Zustand, Framer Motion |
| Backend | FastAPI, SQLAlchemy, SQLite (dev) |
| Data | `backend/momentum.db` (SQLite, local dev) |

## Project structure

```
Momentum/
├── backend/          # FastAPI API + momentum engine
│   ├── app/
│   │   ├── api/routes/   # streams, items, focus, capture
│   │   ├── models/
│   │   └── services/     # momentum_engine, capture
│   ├── .env.example
│   └── requirements.txt
├── frontend/         # React SPA
│   └── src/
└── docker-compose.yml   # Optional Postgres + Redis (not required for local dev)
```

## Quick start

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API: http://127.0.0.1:8000  
Health: http://127.0.0.1:8000/health

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://127.0.0.1:5173

The Vite dev server proxies `/api` and `/health` to the backend on port 8000.

## Configuration

Copy `backend/.env.example` to `backend/.env`.

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./momentum.db` | SQLite database path (relative to `backend/`) |
| `SEED_DEMO_DATA` | `false` | Load sample streams/items on first startup |
| `DEBUG` | `true` | Debug mode |
| `REDIS_URL` | `redis://localhost:6379/0` | Reserved for future background jobs |

## Features

- **Today** — daily focus list picked by the momentum engine (weekday / weekend / everyday streams)
- **Capture** (`⌘J`) — add items to a stream manually
- **All Items** — view queue by stream, move items between streams/sub-streams, delete
- **Streams** — create and manage streams and sub-streams
- **Focus mode** — open an item, add notes, log done

## API overview

All routes are prefixed with `/api`.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/dashboard` | Today's focus |
| `GET` | `/streams` | List streams |
| `POST` | `/streams` | Create stream |
| `PATCH` | `/streams/{id}` | Update stream |
| `DELETE` | `/streams/{id}` | Delete stream (cascades) |
| `GET` | `/items` | List items |
| `PATCH` | `/items/{id}` | Update item (status, stream, notes, …) |
| `DELETE` | `/items/{id}` | Delete item |
| `POST` | `/capture` | Capture content into a stream |

## Data & reset

Items and streams are stored in `backend/momentum.db`.

To wipe everything and start fresh:

```bash
# Stop the backend first, then:
rm backend/momentum.db
# Restart backend — tables are recreated on startup
```

## Optional: Docker services

Postgres and Redis are scaffolded but **not required** for local dev (SQLite is used by default).

```bash
docker compose up -d
```

## Scripts

**Frontend**

```bash
npm run dev      # dev server
npm run build    # production build
npm run preview  # preview production build
```

**Backend**

```bash
uvicorn app.main:app --reload --port 8000
```
