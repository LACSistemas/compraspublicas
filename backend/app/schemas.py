from datetime import datetime

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    tipo: Literal["dfd", "etp", "mapa_riscos", "tr"] = "etp"
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


class RevisarRecomendacaoIn(BaseModel):
    idx: int = Field(ge=0)
    decisao: Literal["executar", "dispensar"]


class PlanoCardOut(BaseModel):
    id: int
    codigo: str
    nome: str
    pergunta_controle: str
    ordem: int
    status: str
    aplicavel: bool
    justificativa_dispensa: str | None = None
    robustez_pct: int
    informacoes: list[dict] = []
    dependencias: list[str] = []
    dispensa_status: str | None = None
    dispensa_revisada_em: datetime | None = None


class PlanoInvestigacaoOut(BaseModel):
    id: int
    contratacao_id: int
    versao: int
    status: str
    cards: list[PlanoCardOut]
    criado_em: datetime
    atualizado_em: datetime


class LacunaPlanoOut(BaseModel):
    plano_informacao_id: int
    plano_card_id: int
    codigo_card: str
    codigo_informacao: str
    nome_informacao: str
    estrategia: Literal["consulta", "integracao", "inferencia", "pergunta", "upload"]
    prioridade: int
    status: str
    obrigatoria: bool
    bloqueia_conhecimento: bool


class ResumoLacunasPlanoOut(BaseModel):
    plano_id: int
    total: int
    bloqueantes: int
    opcionais: int
    pronto_para_conhecimento: bool
    proxima_estrategia: str | None = None
    lacunas: list[LacunaPlanoOut]


class PerguntaPlanejamento(BaseModel):
    model_config = ConfigDict(extra="forbid")
    texto: str = Field(min_length=5)
    alternativas: list[AlternativaSchema] = Field(min_length=5, max_length=5)

    @model_validator(mode="after")
    def validar_letras(self):
        if [a.letra for a in self.alternativas] != list("abcde"):
            raise ValueError("Alternativas devem estar na ordem a, b, c, d, e")
        return self


class InformacaoPlanejamento(BaseModel):
    model_config = ConfigDict(extra="forbid")
    codigo: str
    estrategia: Literal["consulta", "integracao", "inferencia", "pergunta", "upload"]
    justificativa: str | None = None
    pergunta: PerguntaPlanejamento | None = None

    @model_validator(mode="after")
    def exigir_pergunta_quando_necessaria(self):
        if self.estrategia == "pergunta" and self.pergunta is None:
            raise ValueError("Estratégia pergunta exige pergunta estruturada")
        if self.estrategia != "pergunta" and self.pergunta is not None:
            raise ValueError("Pergunta só é permitida para estratégia pergunta")
        return self


class CardPlanejamento(BaseModel):
    model_config = ConfigDict(extra="forbid")
    codigo: str
    aplicavel: bool
    justificativa: str = Field(min_length=3)
    informacoes: list[InformacaoPlanejamento]


class PropostaPlanoInvestigacao(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cards: list[CardPlanejamento]


class EvidenciaPlanoOut(BaseModel):
    id: int
    plano_informacao_id: int
    tipo: str
    descricao: str
    conteudo: dict | list | str | int | float | bool | None
    origem: str
    metodo_obtencao: str
    confianca: str
    hash_conteudo: str
    status_validacao: str
    estado: str
    substitui_evidencia_id: int | None = None
    criterios_atendidos: list[str] = []
    criado_em: datetime


class ValidarEvidenciaPlanoIn(BaseModel):
    status_validacao: Literal["pendente", "confirmada", "rejeitada"]


class SubstituirEvidenciaIn(BaseModel):
    evidencia_anterior_id: int


class VincularCriteriosIn(BaseModel):
    criterios: list[str]


class ConhecimentoCardOut(BaseModel):
    id: int
    plano_card_id: int
    codigo_card: str
    versao: int
    conclusao: str
    motivacao: str
    fundamentacao: list
    riscos: list
    recomendacoes: list
    evidencias: list[int]
    robustez_pct: int
    status: str
    aprovado_em: datetime | None = None
    cobertura_criterios: list[dict] = []
    dimensoes_robustez: dict[str, int] = {}
    fontes_confirmadas: list[dict] = []


class RevisarConhecimentoIn(BaseModel):
    status: Literal["aprovado", "rejeitado"]


class RevisarDispensaIn(BaseModel):
    decisao: Literal["aprovar", "rejeitar"]


class ExpandirPesquisaPrecosIn(BaseModel):
    quantidade: int = Field(default=3, ge=1, le=5)


class RevisarObservacaoPrecoIn(BaseModel):
    comparavel: bool
    motivo_exclusao: str | None = None
    status_validacao: Literal["pendente", "confirmada", "rejeitada"] = "confirmada"


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
