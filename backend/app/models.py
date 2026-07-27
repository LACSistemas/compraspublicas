from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    nome = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=False)
    is_owner = Column(Boolean, nullable=False, default=False)
    criado_em = Column(DateTime, server_default=func.now())

    pesquisas = relationship("Pesquisa", back_populates="usuario")
    uso_tokens = relationship("UsoTokens", back_populates="usuario")


class UsoTokens(Base):
    __tablename__ = "uso_tokens"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    tipo = Column(String, nullable=False)  # pesquisa | analise | etp | tr
    tokens_input = Column(Integer, nullable=True)
    tokens_output = Column(Integer, nullable=True)
    tokens_total = Column(Integer, nullable=True)
    modelo = Column(String, nullable=True)
    referencia_id = Column(Integer, nullable=True)
    criado_em = Column(DateTime, server_default=func.now())

    usuario = relationship("Usuario", back_populates="uso_tokens")


class Pesquisa(Base):
    __tablename__ = "pesquisas"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    termo_busca = Column(String, nullable=False)
    quantidade_desejada = Column(String, nullable=True)
    limite_processos = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="pendente")
    erro_mensagem = Column(Text, nullable=True)
    resultado_json = Column(Text, nullable=True)
    pasta_downloads = Column(String, nullable=True)
    criado_em = Column(DateTime, server_default=func.now())
    atualizado_em = Column(DateTime, server_default=func.now(), onupdate=func.now())

    usuario = relationship("Usuario", back_populates="pesquisas")
    analises = relationship(
        "Analise", back_populates="pesquisa", cascade="all, delete-orphan"
    )
    geracoes = relationship(
        "Geracao", back_populates="pesquisa", cascade="all, delete-orphan"
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


class Geracao(Base):
    __tablename__ = "geracoes"

    id = Column(Integer, primary_key=True, index=True)
    pesquisa_id = Column(Integer, ForeignKey("pesquisas.id"), nullable=False)
    tipo = Column(String, nullable=False, default="etp")
    status = Column(String, nullable=False, default="pendente")
    erro_mensagem = Column(Text, nullable=True)
    resultado_json = Column(Text, nullable=True)
    arquivo_gerado = Column(String, nullable=True)
    modelo_gemini = Column(String, nullable=True)
    criado_em = Column(DateTime, server_default=func.now())
    atualizado_em = Column(DateTime, server_default=func.now(), onupdate=func.now())

    pesquisa = relationship("Pesquisa", back_populates="geracoes")
