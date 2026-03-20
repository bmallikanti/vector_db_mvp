# Vector DB MVP

`Vector DB MVP` is a lightweight vector search service built with FastAPI and Temporal. It models content as libraries, documents, and chunks, supports embedding-based retrieval, and exposes both direct and workflow-backed query execution.

The project is intentionally simple in storage and infrastructure, but structured like a real backend system: API routers, service layer, repositories, indexing strategies, workflow orchestration, and tests are separated into clear modules.

## Core Capabilities

- CRUD APIs for libraries, documents, and chunks
- Semantic search over chunk embeddings
- Direct API execution for fast local queries
- Temporal-backed execution for durable query workflows
- Brute-force and LSH-based search strategies
- Metadata filters on search results
- Interactive CLI for workflow-driven demos

## Stack

- Python 3.11+
- FastAPI
- Pydantic
- NumPy
- Temporal
- Docker Compose
- Pytest
- Optional Cohere-based embedding generation

## System Design

### Data Model

The system uses a three-level hierarchy:

- `Library`
- `Document`
- `Chunk`

Chunks store text, optional metadata, and optional embeddings. Search operates at the chunk level.

### Execution Paths

The application supports two query paths:

1. Direct execution through the API and service layer
2. Durable execution through Temporal workflows and workers

This makes it useful both as a simple search API and as an example of workflow-based backend orchestration.

### Search Strategies

Two indexing strategies are available:

- `brute`: exact search over all indexed chunks
- `lsh`: approximate nearest-neighbor search using locality-sensitive hashing

Search requests can include:

- `query_embedding`
- `query_text`
- `k`
- `index`
- metadata `filters`

## Architecture

```text
Client / CLI
    |
FastAPI Routers
    |
Services
    |
Repositories
    |
Indexes (Brute Force / LSH)
```

Temporal-backed flow:

```text
FastAPI -> Temporal Client -> Workflow -> Activities -> Services -> Repositories
```

## Project Layout

```text
app/
  api/                 FastAPI routers
  services/            business logic
  repositories/        in-memory repositories
  indexing/            vector search implementations
  temporal_workflows/  Temporal client, worker, workflows
  models/              domain models
tests/
  test_crud.py         CRUD API coverage
interactive_cli.py     interactive workflow demo
demo.py                demo script
```

## Quick Start

### Docker

Create a `.env` file:

```bash
echo "COHERE_API_KEY=your_api_key_here" > .env
```

Start the full stack:

```bash
docker compose up -d --build
```

Available services:

- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Temporal UI: `http://localhost:8080`

### Local Development

Install dependencies:

```bash
python -m venv venv
source venv/bin/activate
pip install -e .
```

Create a `.env` file:

```bash
echo "COHERE_API_KEY=your_api_key_here" > .env
echo "TEMPORAL_ADDRESS=localhost:7233" >> .env
```

Start Temporal infrastructure:

```bash
docker compose up -d postgres temporal ui
```

Start the worker:

```bash
python -m app.temporal_workflows.worker
```

Start the API:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## API Summary

Base path: `/vector_db/libraries`

Key endpoints:

- `POST /vector_db/libraries`
- `GET /vector_db/libraries`
- `GET /vector_db/libraries/{id}`
- `PUT /vector_db/libraries/{id}`
- `DELETE /vector_db/libraries/{id}`
- `POST /vector_db/libraries/{id}/documents`
- `GET /vector_db/libraries/{id}/documents`
- `POST /vector_db/libraries/{id}/documents/{doc_id}/chunks`
- `GET /vector_db/libraries/{id}/documents/{doc_id}/chunks`
- `POST /vector_db/libraries/{id}/search`

Interactive workflow endpoints are available under `/interactive`.

## Example Requests

Create a library:

```bash
curl -X POST http://localhost:8000/vector_db/libraries \
  -H "Content-Type: application/json" \
  -d '{"name":"Demo Library"}'
```

Run direct search:

```bash
curl -X POST http://localhost:8000/vector_db/libraries/{LIB_ID}/search \
  -H "Content-Type: application/json" \
  -d '{"query_embedding":[1.0,0.0],"k":3,"index":"brute"}'
```

Run Temporal-backed search:

```bash
curl -X POST "http://localhost:8000/vector_db/libraries/{LIB_ID}/search?use_temporal=true" \
  -H "Content-Type: application/json" \
  -d '{"query_text":"museum in paris","k":3,"index":"brute"}'
```

Start the interactive CLI:

```bash
python interactive_cli.py
```

## Testing

Run the CRUD test suite:

```bash
pytest tests/test_crud.py -v
```

The tests exercise the API layer directly with FastAPI's test client, so the server does not need to be started separately.

## Current Constraints

- Data is stored in memory and is lost on restart
- The project is an MVP, not a production-ready vector database
- Test coverage is strongest around CRUD behavior; Temporal workflow coverage is limited
