import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import analises, geracoes, pesquisas

# Garante que logger.info(...) dos services (tokens gastos, progresso do scraping etc.)
# apareça no console do uvicorn — sem isso, só os loggers "uvicorn.*" têm handler.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.CORS_ORIGINS],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pesquisas.router)
app.include_router(analises.router)
app.include_router(geracoes.router)
