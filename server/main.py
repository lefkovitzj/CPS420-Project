from contextlib import asynccontextmanager
from fastapi import FastAPI
from database import engine
from models import Base
from routers import auth

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables on startup
    models.Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(auth.router)

@app.get("/")
def read_root() -> dict[str, str]:
    return {"status": "ok"}
