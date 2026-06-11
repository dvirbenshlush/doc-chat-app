# Server Architecture

FastAPI backend that answers natural-language questions using two pipelines: **RAG** (documents) and **Text-to-SQL** (relational tables). An LLM-based orchestrator routes each question to the right pipeline automatically.

---

## Project Structure

```
server/
├── main.py                  # FastAPI app entry point
├── requirements.txt
├── .env.example
├── routers/
│   └── chat.py              # HTTP endpoints
├── services/
│   ├── orchestrator.py      # Routes questions → sql or docs
│   ├── rag_service.py       # RAG pipeline (docs)
│   ├── sql_service.py       # Text-to-SQL pipeline
│   ├── document_service.py  # Chunking + embedding index
│   └── db_service.py        # DuckDB loader + SQL security
└── data/
    ├── guide_python.txt
    ├── guide_cooking.txt
    ├── guide_travel.txt
    ├── guide_fitness.txt
    ├── guide_personal_finance.txt
    └── tables/
        ├── students.csv     # 25 rows
        ├── courses.csv      # 12 rows
        └── enrollments.csv  # 65 rows
```

---

## Architecture Overview

```
User question
      │
      ▼
┌─────────────────────────────────┐
│         orchestrator.py         │
│  LLM classifies: "sql" / "docs" │
└────────┬──────────────┬─────────┘
         │              │
    "sql"│         "docs"│
         ▼              ▼
┌──────────────┐  ┌──────────────────┐
│  sql_service │  │   rag_service    │
└──────┬───────┘  └────────┬─────────┘
       │                   │
       ▼                   ▼
┌──────────────┐  ┌──────────────────┐
│  db_service  │  │ document_service │
│  (DuckDB)    │  │ (embeddings)     │
└──────────────┘  └──────────────────┘
       │                   │
       └─────────┬─────────┘
                 ▼
        { answer, route, sources,
          sql_query, results }
```

---

## Startup (lifespan)

`main.py` runs two initialization steps before accepting requests:

1. **`document_service.load_documents()`** — reads all `.txt` files from `data/`, splits them into chunks, and encodes each chunk with `all-MiniLM-L6-v2` (sentence-transformers). The embedding index is held in memory.
2. **`db_service.load_tables()`** — reads all `.csv` files from `data/tables/` and loads them into an in-memory DuckDB instance.

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/chat` | Main chat endpoint. Accepts `{ question, history[] }`, returns `{ answer, route, sources, sql_query, results }` |
| `GET` | `/api/documents` | Returns list of loaded guide files |
| `GET` | `/api/tables` | Returns table names, row counts, and column lists |

### Request / Response

**POST `/api/chat`**
```json
// Request
{
  "question": "Which students scored above 90?",
  "history": [
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ]
}

// Response
{
  "answer": "Three students scored above 90: ...",
  "route": "sql",
  "sql_query": "SELECT s.first_name, e.score FROM students s JOIN enrollments e ON ...",
  "results": [{ "first_name": "Alice", "score": 95 }],
  "sources": []
}
```

---

## Services

### orchestrator.py

Sends the question to the LLM with a one-shot classification prompt. The LLM replies with a single word — `sql` or `docs`. The call uses `max_tokens=5` and `temperature=0` for speed and determinism.

```
classify_prompt → Groq (llama-3.3-70b-versatile)
                       │
              "sql" or "docs"
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
   sql_service                rag_service
```

Adds a `route` field (`"sql"` or `"docs"`) to every response.

---

### rag_service.py — RAG Pipeline

Answers questions about the guide documents.

```
question
   │
   ├─► document_service.search()    cosine similarity → top 4 chunks
   │
   ├─► build system prompt with chunks as context
   │
   └─► Groq (llama-3.3-70b-versatile, max_tokens=1024)
              │
              ▼
   { answer, sources, mode: "groq" }
```

Last 6 messages from `history` are included for multi-turn context.

---

### sql_service.py — Text-to-SQL Pipeline

Answers questions about the relational tables.

```
question
   │
   ├─► db_service.get_schema()       table definitions + 3-row samples + FK hints
   │
   ├─► Groq (temp=0.1)               generates a SQL SELECT query
   │
   ├─► db_service.validate_sql()     security layer (see below)
   │
   ├─► db_service.add_limit()        injects LIMIT 50 if absent
   │
   ├─► db_service.execute_query()    runs on DuckDB, returns list[dict]
   │
   └─► Groq (summarize)              turns rows into a natural-language answer
              │
              ▼
   { answer, sql_query, results, sources: [], mode: "sql" }
```

---

### db_service.py — DuckDB + SQL Security

**Loading**

```python
duckdb.connect(":memory:")
# For each CSV: CREATE TABLE <name> AS SELECT * FROM read_csv_auto(...)
```

**Schema introspection**

`get_schema()` returns a string containing column names and types, a 3-row sample per table, and the foreign-key relationships between tables. This string becomes the SQL generation system prompt.

**Security layer — `validate_sql()`**

Three checks run before any query reaches DuckDB:

| Check | Rule |
|-------|------|
| Statement type | Must start with `SELECT` |
| Blocked keywords | Rejects `DROP`, `INSERT`, `UPDATE`, `DELETE`, `ALTER`, `CREATE`, `TRUNCATE`, and 12 more |
| Table allowlist | `FROM` / `JOIN` targets must be in `{students, courses, enrollments}` |

`add_limit()` appends `LIMIT 50` to any query that does not already contain a `LIMIT` clause.

---

### document_service.py — Embedding Index

| Parameter | Value |
|-----------|-------|
| Model | `all-MiniLM-L6-v2` (sentence-transformers, ~90 MB, CPU) |
| Chunk size | 200 words |
| Overlap | 50 words |
| Similarity | Cosine (dot product on normalized vectors) |
| Top-k returned | 4 chunks |

Documents are chunked at startup and never re-indexed at runtime. Embeddings are stored as NumPy arrays in memory.

---

## Data Model

```
students          courses           enrollments
─────────────     ────────────────  ──────────────────────────
student_id (PK)   course_id (PK)    enrollment_id (PK)
first_name        title             student_id → students
last_name         category          course_id  → courses
email             instructor        enrolled_date
age               price             completed_date
city              duration_hours    score
country           difficulty        status
join_date         rating
```

---

## Environment Variables

```env
GROQ_API_KEY=gsk_...      # Required — get a free key at console.groq.com
USE_LLM=true              # Set false to skip LLM and return raw chunks (docs mode only)
```

---

## Running Locally

```bash
cd server
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env          # fill in GROQ_API_KEY
uvicorn main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs` (Swagger UI).

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework |
| `uvicorn[standard]` | ASGI server |
| `groq` | LLM API client (Groq Cloud) |
| `sentence-transformers` | Local embeddings (`all-MiniLM-L6-v2`) |
| `duckdb` | In-memory analytical SQL engine |
| `pandas` | DataFrame ↔ dict conversion for query results |
| `numpy` | Cosine similarity computation |
| `python-dotenv` | `.env` loading |
| `pydantic` | Request/response validation |
