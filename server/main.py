from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routers import chat as chat_router
from services import document_service, db_service

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading documents and embedding model (first run downloads ~90MB)...")
    document_service.load_documents()
    print("Loading relational tables into DuckDB...")
    db_service.load_tables()
    yield


app = FastAPI(title="Doc Chat API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router.router, prefix="/api")
