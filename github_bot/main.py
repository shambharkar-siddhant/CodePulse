# github_bot/main.py

from fastapi import FastAPI
from contextlib import asynccontextmanager
from github_bot.routes import webhook_router
from db.connection import init_db_pool
from fastapi.middleware.cors import CORSMiddleware
from config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db_pool()
    yield

app = FastAPI(
    title="GitHub Bot Webhook Server",
    lifespan=lifespan
)
app.add_middleware(
  CORSMiddleware,
  allow_origins=[settings.FRONTEND_URL],
  allow_methods=["*"],
  allow_headers=["*"],
)

# Mount the webhook route
app.include_router(webhook_router)


# Optional root for health check
@app.get("/health")
def read_root():
    return {"status": "ok", "message": "GitHub Bot is running"}
