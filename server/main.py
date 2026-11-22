import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine
from models import Base
from routes.auth import router as auth_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Create database tables on startup
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(lifespan=lifespan)

host = os.environ.get("HOST", "127.0.0.1")
backend_port = os.environ.get("PORT", "5000")
frontend_port = os.environ.get("FRONTEND_PORT", "3000")

origins = [
    f"http://{host}:{frontend_port}",
    f"http://localhost:{frontend_port}",
    f"http://{host}:{backend_port}",
    f"http://localhost:{backend_port}",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"status": "ok"}
