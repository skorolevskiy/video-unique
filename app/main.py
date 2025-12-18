from fastapi import FastAPI
from app.api.routes import router
from app.db.session import engine
from app.db.base import Base

app = FastAPI(title="Video Unique Service")

@app.on_event("startup")
async def startup():
    # Create tables for MVP
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(router, prefix="/api/v1")

@app.get("/health")
def health():
    return {"status": "ok"}
