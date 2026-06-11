import os
import re
from groq import AsyncGroq
from services.db_service import get_schema, validate_sql, add_limit, execute_query

_client: AsyncGroq | None = None


def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
    return _client


def _extract_sql(raw: str) -> str:
    match = re.search(r"```(?:sql)?\s*([\s\S]+?)```", raw, re.IGNORECASE)
    return match.group(1).strip() if match else raw.strip()


async def answer_sql_question(question: str, history: list[dict]) -> dict:
    schema = get_schema()

    system_prompt = (
        "You are a SQL expert working with DuckDB.\n"
        "Generate a single valid SELECT query that answers the user's question.\n"
        "Return ONLY the SQL — no explanation, no markdown, no extra text.\n"
        "If the question cannot be answered with the available data, return exactly: CANNOT_ANSWER\n\n"
        f"Schema:\n{schema}"
    )

    messages = [{"role": "system", "content": system_prompt}]
    for m in history[-4:]:
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": question})

    gen_response = await _get_client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=512,
        temperature=0.1,
        messages=messages,
    )

    raw = gen_response.choices[0].message.content.strip()
    sql = _extract_sql(raw)

    if sql.upper() == "CANNOT_ANSWER":
        return {
            "answer": "This question can't be answered from the database tables. Try asking about documents instead.",
            "mode": "sql",
            "sql_query": None,
            "results": [],
            "sources": [],
        }

    is_safe, err = validate_sql(sql)
    if not is_safe:
        return {
            "answer": f"The generated query was blocked by the security layer: {err}",
            "mode": "sql",
            "sql_query": sql,
            "results": [],
            "sources": [],
        }

    sql = add_limit(sql)
    rows, error = execute_query(sql)

    if error:
        return {
            "answer": f"Query execution error: {error}",
            "mode": "sql",
            "sql_query": sql,
            "results": [],
            "sources": [],
        }

    # Natural-language summary of results
    summary_msg = (
        f'The user asked: "{question}"\n'
        f"The query returned {len(rows)} row(s).\n"
        f"First rows: {rows[:5]}\n\n"
        "Write a concise natural-language answer based on these results."
    )
    summary_response = await _get_client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=256,
        messages=[
            {"role": "system", "content": "Summarize SQL results clearly and concisely."},
            {"role": "user", "content": summary_msg},
        ],
    )

    return {
        "answer": summary_response.choices[0].message.content.strip(),
        "mode": "sql",
        "sql_query": sql,
        "results": rows,
        "sources": [],
    }
