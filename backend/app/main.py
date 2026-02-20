from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.projects import router as projects_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    import os
    os.makedirs("data", exist_ok=True)
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


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
