# Vector Database with Temporal

A minimal vector database with FastAPI and Temporal workflows.

## Quick Start

### 1. Install Dependencies

**Create virtual environment** (each user creates their own):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

### 2. Configure Environment

**Create `.env` file** (each user creates their own):
```bash
COHERE_API_KEY=your_api_key_here
```

> **Note:** `.env` and `venv/` are gitignored - each user must create their own.

### 3. Start Services

**Terminal 1: Start Temporal**
```bash
docker-compose up -d
```

**Terminal 2: Start Worker**
```bash
source venv/bin/activate
python -m app.temporal_workflows.worker
```

**Terminal 3: Start API**
```bash
source venv/bin/activate
uvicorn app.main:app --reload
```

### 4. Test the System

**Via API:**
```bash
# Create library
curl -X POST http://localhost:8000/vector_db/libraries \
  -H 'Content-Type: application/json' \
  -d '{"name":"My Library"}'

# Search (with Temporal)
curl -X POST http://localhost:8000/vector_db/libraries/{lib_id}/search?use_temporal=true \
  -H 'Content-Type: application/json' \
  -d '{"query_embedding":[1.0,0.0],"k":5,"index":"brute"}'
```

**Via Temporal Client:**
```python
from app.temporal_workflows.client import TemporalQueryClient
from app.temporal_workflows.query_workflow import QueryRequest

client = TemporalQueryClient()
result = await client.execute_query(QueryRequest(
    lib_id="your-lib-id",
    query_embedding=[1.0, 0.0],
    k=5,
    index="brute"
))
```

**Simple Test Script:**
```bash
python test_system.py
```

## Architecture

### What Uses What

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer                             │
│  FastAPI (app/main.py)                                  │
│    ↓                                                     │
│  Routers (app/api/routers/*)                           │
│    ↓                                                     │
│  Services (app/services/*)                              │
└─────────────────────────────────────────────────────────┘
                    │
                    ├─────────────────┬───────────────────┐
                    ▼                 ▼                   ▼
        ┌──────────────────┐           ┌──────────────────┐
        │  In-Memory       │           │   Temporal       │
        │  (default)       │           │  (workflows)     │
        │                  │           │                  │
        │ LibraryRepo      │           │ QueryWorkflow    │
        │ DocumentRepo     │           │   ↓              │
        │ ChunkRepo        │           │ Activities       │
        └──────────────────┘           │   ↓              │
                                       │ Services         │
                                       │   ↓              │
                                       │ In-Memory Repos  │
                                       └──────────────────┘
```

### Storage Mode

**In-Memory:**
- Fast, no persistence
- Data lost on restart
- Good for testing and demos

### Temporal Workflows

When `use_temporal=true` in API or using Temporal client:
- Workflow orchestrates: setup → validate → embed → search → rerank
- Activities run in worker process
- Uses in-memory repositories inside activities and services

## Key Components

### Services (`app/services/`)
- `LibraryService` - Manages libraries
- `DocumentService` - Manages documents
- `ChunkService` - Manages chunks
- `SearchService` - Vector search (brute force or LSH)

### Repositories (`app/repositories/`)
- `memory/` - In-memory storage

### Temporal (`app/temporal_workflows/`)
- `worker.py` - Worker process (runs activities)
- `client.py` - Client to start workflows
- `query_workflow.py` - Query workflow and activities

## Utilities

No additional utilities are required for storage.

## API Endpoints

- `POST /vector_db/libraries` - Create library
- `GET /vector_db/libraries/{id}` - Get library
- `POST /vector_db/libraries/{id}/documents` - Add document
- `POST /vector_db/libraries/{id}/documents/{doc_id}/chunks` - Add chunk
- `POST /vector_db/libraries/{id}/search?use_temporal=true` - Search

## Temporal UI

View workflow executions: http://localhost:8088

## Environment Variables

- `COHERE_API_KEY` - Cohere API key for embeddings

## Project Structure

```
app/
├── api/              # FastAPI routes
├── core/             # Configuration
├── models/           # Pydantic models
├── repositories/     # Data storage (memory)
├── services/         # Business logic
├── indexing/         # Vector indexes (brute/lsh)
├── temporal_workflows/ # Temporal workflows & activities
└── main.py           # FastAPI app
```
