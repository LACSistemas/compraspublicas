from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Pesquisa(Base):
    __tablename__ = "pesquisas"

    id = Column(Integer, primary_key=True, index=True)
    termo_busca = Column(String, nullable=False)
    quantidade_desejada = Column(String, nullable=True)
    limite_processos = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="pendente")
    erro_mensagem = Column(Text, nullable=True)
    resultado_json = Column(Text, nullable=True)
    pasta_downloads = Column(String, nullable=True)
    criado_em = Column(DateTime, server_default=func.now())
    atualizado_em = Column(DateTime, server_default=func.now(), onupdate=func.now())

    analises = relationship(
        "Analise", back_populates="pesquisa", cascade="all, delete-orphan"
    )


class Analise(Base):
    __tablename__ = "analises"

    id = Column(Integer, primary_key=True, index=True)
    pesquisa_id = Column(Integer, ForeignKey("pesquisas.id"), nullable=False)
    status = Column(String, nullable=False, default="pendente")
    erro_mensagem = Column(Text, nullable=True)
    resultado_json = Column(Text, nullable=True)
    modelo_gemini = Column(String, nullable=True)
    criado_em = Column(DateTime, server_default=func.now())
    atualizado_em = Column(DateTime, server_default=func.now(), onupdate=func.now())

    pesquisa = relationship("Pesquisa", back_populates="analises")
