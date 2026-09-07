from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

<<<<<<< Updated upstream
from .api import events, summary
=======
from .api import events, summary, assistant
>>>>>>> Stashed changes
from .database import initialize_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Warehouse Risk API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(events.router)
app.include_router(summary.router)
<<<<<<< Updated upstream
=======
app.include_router(assistant.router)
>>>>>>> Stashed changes


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
