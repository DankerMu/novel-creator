from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.bible import router as bible_router
from app.api.export import router as export_router
from app.api.generation import router as generation_router
from app.api.kg import router as kg_router
from app.api.lorebook import router as lorebook_router
from app.api.projects import router as projects_router
from app.api.summary import router as summary_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    import os

    from app.core.database import Base, engine

    os.makedirs("data", exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="Novel Creator API",
    description="中文中长篇小说 AI 写作平台",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3100"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router)
app.include_router(bible_router)
app.include_router(lorebook_router)
app.include_router(generation_router)
app.include_router(summary_router)
app.include_router(export_router)
app.include_router(kg_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
