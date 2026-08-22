import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.routers import analises, contratacoes, geracoes, pesquisas
from app.routers import auth as auth_router
from app.routers import admin as admin_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

logger = logging.getLogger("main")


def _seed_owner():
    if not settings.OWNER_EMAIL or not settings.OWNER_PASSWORD:
        return
    from app.auth import hash_password
    from app.models import Usuario
    db = SessionLocal()
    try:
        exists = db.query(Usuario).filter(Usuario.email == settings.OWNER_EMAIL).first()
        if exists:
            return
        owner = Usuario(
            email=settings.OWNER_EMAIL,
            nome="Owner",
            hashed_password=hash_password(settings.OWNER_PASSWORD),
            is_active=True,
            is_owner=True,
        )
        db.add(owner)
        db.commit()
        logger.info(f"Owner criado: {settings.OWNER_EMAIL}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _seed_owner()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(admin_router.router)
app.include_router(pesquisas.router)
app.include_router(analises.router)
app.include_router(geracoes.router)
app.include_router(contratacoes.router)
