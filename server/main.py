from contextlib import asynccontextmanager
from fastapi import FastAPI
from database import engine
from models import Base
from routes.auth import router as auth_router
from fastapi.middleware.cors import CORSMiddleware
import os
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables on startup
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(lifespan=lifespan)

origins=[
    f"http://{os.environ['HOST']}:{os.environ['FRONTEND_PORT']}",
    f"http://localhost:{os.environ['FRONTEND_PORT']}",
    f"http://{os.environ['HOST']}:{os.environ['PORT']}",
    f"http://localhost:{os.environ['PORT']}",
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
