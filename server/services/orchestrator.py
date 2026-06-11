import os
from groq import AsyncGroq
from services import rag_service, sql_service

_client: AsyncGroq | None = None


def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
    return _client


async def route(question: str, history: list[dict]) -> dict:
    classify_prompt = (
        "Classify the question below as either 'sql' or 'docs'.\n\n"
        "'sql'  — questions about students, courses, enrollments, counts, averages, rankings, "
        "who enrolled, scores, revenue, statistics from the database.\n"
        "'docs' — questions about knowledge topics: Python programming, healthy cooking, "
        "travel planning, fitness & exercise, personal finance concepts.\n\n"
        f"Question: {question}\n\n"
        "Reply with only one word: sql or docs"
    )

    response = await _get_client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=5,
        temperature=0,
        messages=[{"role": "user", "content": classify_prompt}],
    )

    route_decision = response.choices[0].message.content.strip().lower()
    use_sql = "sql" in route_decision

    if use_sql:
        result = await sql_service.answer_sql_question(question, history)
    else:
        result = await rag_service.answer_question(question, history)
        result.setdefault("sql_query", None)
        result.setdefault("results", [])

    result["route"] = "sql" if use_sql else "docs"
    return result
