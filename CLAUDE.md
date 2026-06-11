# doc-chat-app — Project Design

## Overview

A full-stack application that loads 5 topic-specific guide files and exposes a chat interface for users to ask questions about them. The server uses RAG (Retrieval-Augmented Generation): it chunks the files, finds the most relevant chunks for each question, and passes them to Claude to generate a natural-language answer.

---

## LLM Strategy Note

**Recommended: Claude API (`anthropic` Python SDK)**
The app uses `anthropic` (Claude claude-haiku-4-5 model — cheap and fast) for answer generation.
- No GPU, no local model download, no quantization hassle
- Haiku is extremely cheap (~$0.00025 / 1K input tokens) — a full demo session costs fractions of a cent
- Requires one env var: `ANTHROPIC_API_KEY`

**No-API fallback (pure retrieval):**
If an API key is unavailable, the server falls back to returning the top-3 relevant text chunks verbatim. The chat UI labels this mode clearly ("Retrieval only — no LLM"). This is implemented with a feature flag (`USE_LLM=false` env var).

---

## Project Structure

```
doc-chat-app/
├── CLAUDE.md
├── server/                          # FastAPI backend
│   ├── main.py                      # App entry point, CORS, router registration
│   ├── routers/
│   │   └── chat.py                  # POST /chat  GET /documents
│   ├── services/
│   │   ├── document_service.py      # Load, chunk, and index documents
│   │   └── rag_service.py           # Retrieve relevant chunks + call Claude
│   ├── data/                        # The 5 guide files
│   │   ├── guide_python.txt
│   │   ├── guide_cooking.txt
│   │   ├── guide_travel.txt
│   │   ├── guide_fitness.txt
│   │   └── guide_personal_finance.txt
│   ├── requirements.txt
│   └── .env.example
└── client/                          # Angular 17+ standalone app
    ├── src/
    │   ├── app/
    │   │   ├── app.component.ts/html/scss
    │   │   ├── components/
    │   │   │   ├── chat/            # ChatComponent — message list + input
    │   │   │   └── document-list/   # DocumentListComponent — sidebar with file cards
    │   │   ├── services/
    │   │   │   └── chat.service.ts  # HTTP calls to FastAPI
    │   │   └── models/
    │   │       └── chat.models.ts   # Message, Document interfaces
    │   ├── environments/
    │   └── styles.scss
    ├── angular.json
    └── package.json
```

---

## Guide Files (5 topics)

Each file is ~400–600 words of mock but coherent content:

| File | Topic |
|---|---|
| `guide_python.txt` | Python programming — data types, functions, OOP basics |
| `guide_cooking.txt` | Healthy cooking — meal prep, nutrition tips, recipes |
| `guide_travel.txt` | Travel planning — packing, budgeting, itinerary advice |
| `guide_fitness.txt` | Fitness & exercise — workout plans, recovery, warm-up routines |
| `guide_personal_finance.txt` | Personal finance — budgeting, saving, investing basics |

---

## Backend Design (FastAPI)

### Dependencies (`requirements.txt`)
```
fastapi
uvicorn[standard]
sentence-transformers       # local embeddings (no API key needed)
numpy
anthropic                   # Claude API for answer generation
python-dotenv
pydantic
```

### Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/documents` | Returns list of loaded document names and metadata |
| `POST` | `/chat` | Accepts `{ question: string, history: Message[] }`, returns `{ answer: string, sources: Source[] }` |

### RAG Pipeline

1. **Startup** — `document_service.py` reads all files in `data/`, splits each into ~200-word chunks with 50-word overlap, embeds them using `sentence-transformers` (`all-MiniLM-L6-v2` — 80 MB, CPU-only, fast).
2. **On each `/chat` request:**
   - Embed the question
   - Cosine-similarity search over all chunks → top 4 chunks
   - Build a prompt: system instructions + file chunks as context + chat history + user question
   - Call `anthropic.messages.create(model="claude-haiku-4-5-20251001", ...)` (or return chunks if `USE_LLM=false`)
3. **Response** includes the answer text + source references (filename + chunk excerpt)

### Environment Variables (`.env`)
```
ANTHROPIC_API_KEY=sk-ant-...
USE_LLM=true           # set false for pure-retrieval mode
```

---

## Frontend Design (Angular 17+)

### Key Features
- **Two-panel layout**: left sidebar lists the 5 documents with topic chips; right panel is the chat window
- **Chat window**: scrollable message list (user bubbles right, assistant left), input bar at bottom with Send button and Enter-to-submit
- **Source citations**: each assistant message shows collapsible "Sources" section with the file name and excerpt
- **Mode badge**: small badge in header shows "Claude AI" or "Retrieval Only" depending on server mode
- **Loading state**: typing indicator (animated dots) while waiting for response

### Tech choices
- Angular 17 standalone components (no NgModules)
- Angular Material for UI components (mat-card, mat-chip, mat-button, mat-progress-bar)
- `HttpClient` with typed responses via interfaces in `chat.models.ts`
- No state management library — simple component state + service BehaviorSubject for message history

---

## Data Flow Diagram

```
User types question
        │
        ▼
  ChatComponent (Angular)
        │  POST /chat { question, history }
        ▼
  FastAPI /chat endpoint
        │
        ├─► document_service: embed question → cosine search → top 4 chunks
        │
        └─► rag_service:
              if USE_LLM=true  → anthropic.messages.create() → answer text
              if USE_LLM=false → format top chunks as answer
        │
        ▼
  { answer, sources[] }
        │
        ▼
  ChatComponent renders assistant message + sources
```

---

## Development Setup

```bash
# Server
cd server
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env          # add ANTHROPIC_API_KEY
uvicorn main:app --reload --port 8000

# Client
cd client
npm install
ng serve                      # runs on http://localhost:4200
```

CORS is configured on the server to allow `http://localhost:4200`.

---

## Out of Scope (v1)

- User authentication
- Persistent chat history (stored in DB)
- File upload via UI (files are baked into `data/`)
- PDF parsing (plain `.txt` only in v1; PDF support is a one-line swap with `pypdf`)
- Streaming responses (can be added later with SSE)
