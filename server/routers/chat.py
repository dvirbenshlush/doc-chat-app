import traceback
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services import document_service, db_service
from services.orchestrator import route

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
        result = await route(
            req.question,
            [m.model_dump() for m in req.history],
        )
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents")
def get_documents():
    return {"documents": document_service.get_documents()}


@router.get("/tables")
def get_tables():
    return {"tables": db_service.get_table_info()}
