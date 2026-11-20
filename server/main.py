from contextlib import asynccontextmanager
from fastapi import FastAPI
from database import SessionLocal, engine
from admin_access import initialize_schema
from routes.admin import router as admin_router
from routes.auth import router as auth_router
from routes.catalog_imports import recover_interrupted_imports, router as imports_router
from routes.courses import router as courses_router
from fastapi.middleware.cors import CORSMiddleware
import os
@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_schema(engine)
    with SessionLocal() as db:
        recover_interrupted_imports(db)
    yield

app = FastAPI(lifespan=lifespan)

host = os.environ.get("HOST", "127.0.0.1")
backend_port = os.environ.get("PORT", "5000")
frontend_port = os.environ.get("FRONTEND_PORT", "3000")

origins=[
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
app.include_router(courses_router)
app.include_router(admin_router)
app.include_router(imports_router)

@app.get("/")
def read_root() -> dict[str, str]:
    return {"status": "ok"}
