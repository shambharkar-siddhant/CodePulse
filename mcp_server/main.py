# mcp_server/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mcp_server.routes import mcp_router
from db.connection import init_db_pool
from config import settings


app = FastAPI(title="Model Context Protocol (MCP) Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mcp_router)


@app.on_event("startup")
async def startup_event():
    """Initialize database pool on startup"""
    print("[INFO] Initializing database pool...")
    await init_db_pool()
    print("[INFO] Database pool initialized successfully")


@app.get("/")
def health_check():
    return {"status": "ok", "message": "MCP server is running"}
