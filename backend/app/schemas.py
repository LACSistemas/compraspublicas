from datetime import datetime

from pydantic import BaseModel, Field


class PesquisaCreate(BaseModel):
    termo_busca: str = Field(min_length=1)
    quantidade_desejada: str | None = None


class PesquisaStatusOut(BaseModel):
    id: int
    status: str
    erro_mensagem: str | None = None

    model_config = {"from_attributes": True}


class PesquisaListItemOut(BaseModel):
    id: int
    termo_busca: str
    quantidade_desejada: str | None = None
    status: str
    criado_em: datetime

    model_config = {"from_attributes": True}


class PesquisaDetailOut(BaseModel):
    id: int
    termo_busca: str
    quantidade_desejada: str | None = None
    limite_processos: int
    status: str
    erro_mensagem: str | None = None
    resultado: dict | None = None
    pasta_downloads: str | None = None
    criado_em: datetime
    atualizado_em: datetime

    model_config = {"from_attributes": True}


class AnaliseStatusOut(BaseModel):
    id: int
    status: str
    erro_mensagem: str | None = None
    resultado: dict | None = None
    modelo_gemini: str | None = None

    model_config = {"from_attributes": True}


class GeracaoCreate(BaseModel):
    tipo: str = "etp"
    un_gestora: str
    responsaveis: str
    objeto_resumido: str | None = None


class GeracaoStatusOut(BaseModel):
    id: int
    tipo: str
    status: str
    erro_mensagem: str | None = None
    pendencias: list[str] | None = None
    arquivo_disponivel: bool = False

    model_config = {"from_attributes": True}


class GeracaoDetailOut(GeracaoStatusOut):
    resultado: dict | None = None
    modelo_gemini: str | None = None
    criado_em: datetime
    atualizado_em: datetime
