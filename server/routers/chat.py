from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services import rag_service, document_service

router = APIRouter()


class MessageIn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str
    history: list[MessageIn] = []


@router.post("/chat")
async def chat(req: ChatRequest):
    try:
        result = await rag_service.answer_question(
            req.question,
            [m.model_dump() for m in req.history],
        )
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        msg = str(e)
        if "RESOURCE_EXHAUSTED" in msg or "429" in msg:
            msg = "Gemini API quota exceeded. Wait a moment and try again, or enable billing at console.cloud.google.com."
        raise HTTPException(status_code=500, detail=msg)


@router.get("/documents")
def get_documents():
    return {"documents": document_service.get_documents()}
