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


# ── Contratações ─────────────────────────────────────────────────────────────

class AlternativaSchema(BaseModel):
    letra: str
    texto: str


class ContratacaoCreate(BaseModel):
    objeto: str = Field(min_length=1)
    orgao_unidade: str = Field(min_length=1)
    numero_processo: str | None = None
    equipe_responsavel: str | None = None
    tipo_contratacao: str | None = None
    contexto_inicial: str | None = None


class PerguntaOut(BaseModel):
    id: int
    ordem: int
    texto: str
    alternativas: list[AlternativaSchema]
    resposta_escolhida: str | None = None
    respondida_em: datetime | None = None

    model_config = {"from_attributes": True}


class BaseConhecimentoOut(BaseModel):
    progresso_pct: int
    nivel_maturidade: str
    dados: dict
    atualizado_em: datetime | None = None

    model_config = {"from_attributes": True}


class ContratacaoListItemOut(BaseModel):
    id: int
    objeto: str
    orgao_unidade: str
    numero_processo: str | None = None
    tipo_contratacao: str | None = None
    status: str
    criado_em: datetime
    atualizado_em: datetime

    model_config = {"from_attributes": True}


class ContratacaoOut(BaseModel):
    id: int
    objeto: str
    orgao_unidade: str
    numero_processo: str | None = None
    equipe_responsavel: str | None = None
    tipo_contratacao: str | None = None
    contexto_inicial: str | None = None
    status: str
    erro_mensagem: str | None = None
    criado_em: datetime
    atualizado_em: datetime
    perguntas: list[PerguntaOut] = []
    base_conhecimento: BaseConhecimentoOut | None = None

    model_config = {"from_attributes": True}


class ResponderPerguntaIn(BaseModel):
    resposta: str = Field(min_length=1, max_length=1)


class ValidarEvidenciaIn(BaseModel):
    idx: int
    status_validacao: str
    responsavel: str | None = None


# ── Estatísticas de tokens ────────────────────────────────────────────────────

class EstatsFase(BaseModel):
    total_chamadas: int
    media: float
    mediana: float
    variancia: float
    minimo: int
    maximo: int


class TokensPorContratacao(BaseModel):
    contratacao_id: int
    objeto: str
    tokens_perguntas_input: int
    tokens_perguntas_output: int
    tokens_perguntas_total: int
    tokens_bcc_input: int
    tokens_bcc_output: int
    tokens_bcc_total: int
    total: int


class EstatisticasTokensOut(BaseModel):
    perguntas: EstatsFase
    bcc: EstatsFase
    por_contratacao: list[TokensPorContratacao]
