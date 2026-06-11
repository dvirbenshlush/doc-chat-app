import numpy as np
from pathlib import Path
from dataclasses import dataclass, field
from sentence_transformers import SentenceTransformer

DATA_DIR = Path(__file__).parent.parent / "data"
CHUNK_SIZE = 200
CHUNK_OVERLAP = 50

_model: SentenceTransformer | None = None
_chunks: list["Chunk"] = []


@dataclass
class Chunk:
    doc_name: str
    text: str
    embedding: np.ndarray = field(default=None, repr=False)


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _chunk_text(text: str) -> list[str]:
    words = text.split()
    result = []
    start = 0
    while start < len(words):
        end = min(start + CHUNK_SIZE, len(words))
        result.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return result


def load_documents():
    global _chunks
    _chunks = []
    model = _get_model()
    paths = sorted(DATA_DIR.glob("*.txt"))
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for chunk_text in _chunk_text(text):
            emb = model.encode(chunk_text, convert_to_numpy=True, normalize_embeddings=True)
            _chunks.append(Chunk(doc_name=path.name, text=chunk_text, embedding=emb))
    print(f"Indexed {len(_chunks)} chunks from {len(paths)} documents.")


def search(query: str, top_k: int = 4) -> list[Chunk]:
    if not _chunks:
        return []
    model = _get_model()
    query_emb = model.encode(query, convert_to_numpy=True, normalize_embeddings=True)
    scores = np.array([np.dot(query_emb, c.embedding) for c in _chunks])
    top_indices = np.argsort(scores)[::-1][:top_k]
    return [_chunks[i] for i in top_indices]


def get_documents() -> list[dict]:
    seen: set[str] = set()
    docs = []
    for chunk in _chunks:
        if chunk.doc_name not in seen:
            seen.add(chunk.doc_name)
            display = (
                chunk.doc_name.replace(".txt", "")
                .replace("guide_", "")
                .replace("_", " ")
                .title()
                + " Guide"
            )
            docs.append({"name": chunk.doc_name, "display_name": display})
    return docs
