# Vector DB MVP

A lightweight vector database prototype built with FastAPI and Temporal.

This project lets you create libraries, documents, and chunks, attach embeddings to text, and run semantic search using either direct API execution or Temporal-backed durable workflows. It is designed as an MVP that demonstrates backend system design, workflow orchestration, and vector retrieval concepts without hiding the implementation behind a managed database.

## What This Project Does

- Stores content in a simple library -> document -> chunk hierarchy
- Supports CRUD APIs for libraries, documents, and chunks
- Runs semantic search over chunk embeddings
- Offers two search modes:
  - direct in-process execution
  - durable Temporal workflow execution
- Supports brute-force search and an LSH-based approximate search path
- Includes an interactive CLI for driving workflow-based sessions

## Why It Is Interesting

This is not just a CRUD app. It shows how to combine:

- FastAPI for API design
- in-memory repositories for a clean MVP data layer
- vector search over embeddings
- Temporal for durable orchestration of query flows
- automated tests for core API behavior

For a recruiter or reviewer, the value is in the system design:

- clear separation between routers, services, repositories, indexing, and workflows
- both synchronous and workflow-driven execution paths
- a practical example of search infrastructure without depending on a third-party vector database

## Tech Stack

- Python 3.11+
- FastAPI
- Pydantic
- NumPy
- Temporal
- Docker Compose
- Pytest
- Optional Cohere embeddings

## Architecture

```text
Client / CLI
    |
 FastAPI routers
    |
 Services
    |
 In-memory repositories
    |
 Vector indexes (brute force / LSH)

Optional search path:
FastAPI -> Temporal client -> Temporal workflow -> activities -> services
```

## Repository Structure

```text
app/
  api/                 FastAPI routers
  services/            business logic
  repositories/        in-memory data access
  indexing/            brute-force and LSH search
  temporal_workflows/  Temporal client, worker, workflows
  models/              domain models
tests/
  test_crud.py         API CRUD coverage
interactive_cli.py     workflow-driven CLI demo
demo.py                example/demo entry point
```

## Key Features

### 1. Content Model

- Libraries contain documents
- Documents contain chunks
- Chunks may include embeddings and metadata

### 2. Search

The API supports semantic search against chunk embeddings. You can:

- submit a `query_embedding` directly
- submit `query_text` and let the embedding provider generate the vector
- filter results by chunk metadata
- choose `brute` or `lsh` indexing

### 3. Durable Execution With Temporal

Search requests can run through Temporal when you want workflow-based execution instead of direct in-process handling. This makes the project useful as a demonstration of orchestration patterns, not just retrieval.

### 4. Interactive Workflow Demo

The CLI starts a Temporal session and lets you create data and run searches interactively, which makes the project easier to demo live.

## Quick Start

### Option 1: Docker Compose

1. Create a `.env` file:

```bash
echo "COHERE_API_KEY=your_api_key_here" > .env
```

2. Start the stack:

```bash
docker compose up -d --build
```

3. Open:

- API: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`
- Temporal UI: `http://localhost:8080`

### Option 2: Local Development

1. Install dependencies:

```bash
python -m venv venv
source venv/bin/activate
pip install -e .
```

2. Create `.env`:

```bash
echo "COHERE_API_KEY=your_api_key_here" > .env
echo "TEMPORAL_ADDRESS=localhost:7233" >> .env
```

3. Start Temporal infrastructure:

```bash
docker compose up -d postgres temporal ui
```

4. Start the worker:

```bash
python -m app.temporal_workflows.worker
```

5. Start the API:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## API Overview

Base path: `/vector_db/libraries`

Main endpoints:

- `POST /vector_db/libraries`
- `GET /vector_db/libraries`
- `GET /vector_db/libraries/{id}`
- `PUT /vector_db/libraries/{id}`
- `DELETE /vector_db/libraries/{id}`
- `POST /vector_db/libraries/{id}/documents`
- `POST /vector_db/libraries/{id}/documents/{doc_id}/chunks`
- `POST /vector_db/libraries/{id}/search`

Interactive workflow endpoints live under `/interactive`.

## Example Usage

Create a library:

```bash
curl -X POST http://localhost:8000/vector_db/libraries \
  -H "Content-Type: application/json" \
  -d '{"name":"Demo Library"}'
```

Search with a provided embedding:

```bash
curl -X POST http://localhost:8000/vector_db/libraries/{LIB_ID}/search \
  -H "Content-Type: application/json" \
  -d '{"query_embedding":[1.0,0.0],"k":3,"index":"brute"}'
```

Search through Temporal:

```bash
curl -X POST "http://localhost:8000/vector_db/libraries/{LIB_ID}/search?use_temporal=true" \
  -H "Content-Type: application/json" \
  -d '{"query_text":"museum in paris","k":3,"index":"brute"}'
```

Run the interactive CLI:

```bash
python interactive_cli.py
```

## Testing

Run the CRUD test suite:

```bash
pytest tests/test_crud.py -v
```

These tests cover the core API lifecycle for libraries, documents, and chunks without needing the FastAPI server to be started separately.

## Current Limitations

- storage is in memory only, so data does not persist across restarts
- the project is an MVP, not a production-ready vector database
- tests currently focus on CRUD behavior more than Temporal workflow coverage

## Resume-Friendly Summary

If you want a one-line description for a portfolio, resume, or recruiter screen:

> Built a vector database MVP in Python using FastAPI and Temporal, supporting semantic search, workflow-based query orchestration, and a hierarchical content model for libraries, documents, and chunks.
