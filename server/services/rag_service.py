import os
from groq import AsyncGroq
from services.document_service import search, Chunk

_client: AsyncGroq | None = None


def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
    return _client


def _use_llm() -> bool:
    return os.getenv("USE_LLM", "true").lower() == "true"


def _build_context(chunks: list[Chunk]) -> str:
    parts = [
        f"[Source {i} — {c.doc_name}]\n{c.text}"
        for i, c in enumerate(chunks, 1)
    ]
    return "\n\n---\n\n".join(parts)


async def answer_question(question: str, history: list[dict]) -> dict:
    top_chunks = search(question)
    sources = [
        {"doc": c.doc_name, "excerpt": c.text[:250] + ("..." if len(c.text) > 250 else "")}
        for c in top_chunks
    ]

    if not _use_llm():
        answer = "\n\n".join(
            f"**{c.doc_name}:**\n{c.text}" for c in top_chunks
        )
        return {"answer": answer, "sources": sources, "mode": "retrieval"}

    context = _build_context(top_chunks)
    system_prompt = (
        "You are a helpful assistant that answers questions using the provided guide documents. "
        "Base your answers only on the sources below. "
        "If the answer is not covered by the sources, say so clearly. "
        "Keep answers concise and well-structured.\n\n"
        f"Sources:\n\n{context}"
    )

    messages = [{"role": "system", "content": system_prompt}]
    for m in history[-6:]:
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": question})

    response = await _get_client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=1024,
        messages=messages,
    )

    return {
        "answer": response.choices[0].message.content,
        "sources": sources,
        "mode": "groq",
    }
