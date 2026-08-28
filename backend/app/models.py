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
    contratacoes = relationship("Contratacao", back_populates="usuario")


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
    contratacao_id = Column(Integer, ForeignKey("contratacoes.id"), nullable=True)
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


class Contratacao(Base):
    __tablename__ = "contratacoes"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    objeto = Column(Text, nullable=False)
    orgao_unidade = Column(String(500), nullable=False)
    numero_processo = Column(String(200))
    equipe_responsavel = Column(Text)
    tipo_contratacao = Column(String(100))
    contexto_inicial = Column(Text)
    status = Column(String(50), nullable=False, server_default="cadastro")
    erro_mensagem = Column(Text)
    criado_em = Column(DateTime, server_default=func.now())
    atualizado_em = Column(DateTime, server_default=func.now(), onupdate=func.now())

    usuario = relationship("Usuario", back_populates="contratacoes")
    perguntas = relationship(
        "PerguntaContratacao", back_populates="contratacao", cascade="all, delete-orphan",
        order_by="PerguntaContratacao.ordem",
    )
    base_conhecimento = relationship(
        "BaseConhecimento", back_populates="contratacao", uselist=False, cascade="all, delete-orphan"
    )
    historico = relationship(
        "HistoricoContratacao", back_populates="contratacao", cascade="all, delete-orphan",
        order_by="HistoricoContratacao.criado_em",
    )


class PerguntaContratacao(Base):
    __tablename__ = "perguntas_contratacao"

    id = Column(Integer, primary_key=True, index=True)
    contratacao_id = Column(Integer, ForeignKey("contratacoes.id"), nullable=False)
    ordem = Column(Integer, nullable=False)
    texto = Column(Text, nullable=False)
    alternativas_json = Column(Text, nullable=False)
    resposta_escolhida = Column(String(1))
    respondida_em = Column(DateTime)
    plano_informacao_id = Column(Integer, ForeignKey("plano_informacoes.id"), nullable=True)

    contratacao = relationship("Contratacao", back_populates="perguntas")

    @property
    def alternativas(self):
        import json as _json
        return _json.loads(self.alternativas_json)


class BaseConhecimento(Base):
    __tablename__ = "bases_conhecimento"

    id = Column(Integer, primary_key=True, index=True)
    contratacao_id = Column(Integer, ForeignKey("contratacoes.id"), nullable=False, unique=True)
    dados_json = Column(Text, nullable=False)
    progresso_pct = Column(Integer, server_default="0")
    nivel_maturidade = Column(String(20), server_default="Insuficiente")
    modelo_gemini = Column(String(100))
    criado_em = Column(DateTime, server_default=func.now())
    atualizado_em = Column(DateTime, server_default=func.now(), onupdate=func.now())

    contratacao = relationship("Contratacao", back_populates="base_conhecimento")

    @property
    def dados(self):
        import json as _json
        return _json.loads(self.dados_json)


class HistoricoContratacao(Base):
    __tablename__ = "historico_contratacao"

    id = Column(Integer, primary_key=True, index=True)
    contratacao_id = Column(Integer, ForeignKey("contratacoes.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    acao = Column(String(500), nullable=False)
    detalhe = Column(Text)
    criado_em = Column(DateTime, server_default=func.now())

    contratacao = relationship("Contratacao", back_populates="historico")


class CardDecisaoCatalogo(Base):
    __tablename__ = "cards_decisao_catalogo"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(20), nullable=False, unique=True, index=True)
    versao = Column(Integer, nullable=False, default=1)
    nome = Column(String(300), nullable=False)
    pergunta_controle = Column(Text, nullable=False)
    base_legal_json = Column(Text, nullable=False, default="[]")
    criterios_json = Column(Text, nullable=False, default="[]")
    evidencias_aceitas_json = Column(Text, nullable=False, default="[]")
    artefatos_impactados_json = Column(Text, nullable=False, default="[]")
    ativo = Column(Boolean, nullable=False, default=True)
    criado_em = Column(DateTime, server_default=func.now())


class InformacaoCatalogo(Base):
    __tablename__ = "informacoes_catalogo"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(30), nullable=False, unique=True, index=True)
    nome = Column(String(300), nullable=False)
    objetivo = Column(Text, nullable=False)
    tipo = Column(String(50), nullable=False)
    obrigatoriedade = Column(String(20), nullable=False)
    estrategia_preferencial = Column(String(30), nullable=False)
    dominio_json = Column(Text, nullable=False, default="[]")
    ativo = Column(Boolean, nullable=False, default=True)


class CardInformacao(Base):
    __tablename__ = "cards_informacoes"

    id = Column(Integer, primary_key=True)
    card_id = Column(Integer, ForeignKey("cards_decisao_catalogo.id"), nullable=False)
    informacao_id = Column(Integer, ForeignKey("informacoes_catalogo.id"), nullable=False)
    ordem = Column(Integer, nullable=False, default=1)
    obrigatoria = Column(Boolean, nullable=False, default=True)


class CardDependencia(Base):
    __tablename__ = "cards_dependencias"

    id = Column(Integer, primary_key=True)
    card_id = Column(Integer, ForeignKey("cards_decisao_catalogo.id"), nullable=False)
    depende_de_card_id = Column(Integer, ForeignKey("cards_decisao_catalogo.id"), nullable=False)


class CriterioCardCatalogo(Base):
    __tablename__ = "criterios_cards_catalogo"

    id = Column(Integer, primary_key=True, index=True)
    card_id = Column(Integer, ForeignKey("cards_decisao_catalogo.id"), nullable=False)
    codigo = Column(String(30), nullable=False, unique=True)
    descricao = Column(Text, nullable=False)
    peso = Column(Integer, nullable=False, default=1)


class PlanoInvestigacao(Base):
    __tablename__ = "planos_investigacao"

    id = Column(Integer, primary_key=True, index=True)
    contratacao_id = Column(Integer, ForeignKey("contratacoes.id"), nullable=False)
    versao = Column(Integer, nullable=False, default=1)
    status = Column(String(30), nullable=False, default="rascunho")
    criado_em = Column(DateTime, server_default=func.now())
    atualizado_em = Column(DateTime, server_default=func.now(), onupdate=func.now())


class PlanoCardDecisao(Base):
    __tablename__ = "plano_cards_decisao"

    id = Column(Integer, primary_key=True, index=True)
    plano_id = Column(Integer, ForeignKey("planos_investigacao.id"), nullable=False)
    card_id = Column(Integer, ForeignKey("cards_decisao_catalogo.id"), nullable=False)
    ordem = Column(Integer, nullable=False)
    status = Column(String(30), nullable=False, default="pendente")
    aplicavel = Column(Boolean, nullable=False, default=True)
    justificativa_dispensa = Column(Text)
    robustez_pct = Column(Integer, nullable=False, default=0)
    dispensa_status = Column(String(30))
    dispensa_revisada_por_usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    dispensa_revisada_em = Column(DateTime)


class PlanoInformacao(Base):
    __tablename__ = "plano_informacoes"

    id = Column(Integer, primary_key=True, index=True)
    plano_card_id = Column(Integer, ForeignKey("plano_cards_decisao.id"), nullable=False)
    informacao_id = Column(Integer, ForeignKey("informacoes_catalogo.id"), nullable=False)
    estrategia = Column(String(30), nullable=False)
    status = Column(String(30), nullable=False, default="pendente")
    justificativa_estrategia = Column(Text)
    valor_json = Column(Text)
    origem = Column(String(50))
    confianca = Column(String(20))
    estado_semantico = Column(String(30), nullable=False, default="nao_informado")


class EvidenciaPlano(Base):
    __tablename__ = "evidencias_plano"

    id = Column(Integer, primary_key=True, index=True)
    plano_informacao_id = Column(Integer, ForeignKey("plano_informacoes.id"), nullable=False)
    tipo = Column(String(30), nullable=False)
    descricao = Column(Text, nullable=False)
    conteudo_json = Column(Text, nullable=False)
    origem = Column(String(100), nullable=False)
    metodo_obtencao = Column(String(50), nullable=False)
    confianca = Column(String(20), nullable=False)
    hash_conteudo = Column(String(64), nullable=False)
    status_validacao = Column(String(30), nullable=False, default="pendente")
    estado = Column(String(30), nullable=False, default="vigente")
    substitui_evidencia_id = Column(Integer, ForeignKey("evidencias_plano.id"), nullable=True)
    criado_em = Column(DateTime, server_default=func.now())


class EvidenciaCriterio(Base):
    __tablename__ = "evidencias_criterios"

    id = Column(Integer, primary_key=True)
    evidencia_id = Column(Integer, ForeignKey("evidencias_plano.id"), nullable=False)
    criterio_id = Column(Integer, ForeignKey("criterios_cards_catalogo.id"), nullable=False)


class ConhecimentoCard(Base):
    __tablename__ = "conhecimentos_cards"

    id = Column(Integer, primary_key=True, index=True)
    plano_card_id = Column(Integer, ForeignKey("plano_cards_decisao.id"), nullable=False)
    versao = Column(Integer, nullable=False, default=1)
    conclusao = Column(Text, nullable=False)
    motivacao = Column(Text, nullable=False)
    fundamentacao_json = Column(Text, nullable=False, default="[]")
    riscos_json = Column(Text, nullable=False, default="[]")
    recomendacoes_json = Column(Text, nullable=False, default="[]")
    evidencias_json = Column(Text, nullable=False, default="[]")
    cobertura_criterios_json = Column(Text, nullable=False, default="[]")
    dimensoes_robustez_json = Column(Text, nullable=False, default="{}")
    fontes_confirmadas_json = Column(Text, nullable=False, default="[]")
    robustez_pct = Column(Integer, nullable=False, default=0)
    status = Column(String(30), nullable=False, default="rascunho")
    aprovado_por_usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    aprovado_em = Column(DateTime, nullable=True)
    criado_em = Column(DateTime, server_default=func.now())


class SnapshotBCC(Base):
    __tablename__ = "snapshots_bcc"

    id = Column(Integer, primary_key=True, index=True)
    contratacao_id = Column(Integer, ForeignKey("contratacoes.id"), nullable=False)
    versao = Column(Integer, nullable=False)
    dados_json = Column(Text, nullable=False)
    hash_conteudo = Column(String(64), nullable=False)
    criado_em = Column(DateTime, server_default=func.now())


class ExecucaoIA(Base):
    __tablename__ = "execucoes_ia"

    id = Column(Integer, primary_key=True, index=True)
    contratacao_id = Column(Integer, ForeignKey("contratacoes.id"), nullable=False)
    plano_id = Column(Integer, ForeignKey("planos_investigacao.id"), nullable=True)
    fase = Column(String(50), nullable=False)
    hash_entrada = Column(String(64), nullable=False, index=True)
    modelo = Column(String(100))
    prompt_versao = Column(String(50), nullable=False)
    prompt_texto = Column(Text, nullable=False)
    entrada_json = Column(Text, nullable=False)
    catalogo_json = Column(Text)
    saida_json = Column(Text)
    tokens_input = Column(Integer)
    tokens_output = Column(Integer)
    tokens_total = Column(Integer)
    status = Column(String(30), nullable=False, default="pendente")
    erro_mensagem = Column(Text)
    criado_em = Column(DateTime, server_default=func.now())


class JobExecucao(Base):
    __tablename__ = "jobs_execucao"

    id = Column(Integer, primary_key=True, index=True)
    contratacao_id = Column(Integer, ForeignKey("contratacoes.id"), nullable=True)
    tipo = Column(String(50), nullable=False)
    referencia_id = Column(Integer, nullable=True)
    status = Column(String(30), nullable=False, default="pendente")
    etapa = Column(String(100), nullable=False, default="criado")
    tentativa = Column(Integer, nullable=False, default=0)
    max_tentativas = Column(Integer, nullable=False, default=2)
    checkpoint_json = Column(Text, nullable=False, default="{}")
    erro_mensagem = Column(Text)
    criado_em = Column(DateTime, server_default=func.now())
    atualizado_em = Column(DateTime, server_default=func.now(), onupdate=func.now())


class FonteJuridica(Base):
    __tablename__ = "fontes_juridicas"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), nullable=False, unique=True, index=True)
    tipo = Column(String(50), nullable=False)
    titulo = Column(String(500), nullable=False)
    referencia = Column(String(300), nullable=False)
    url_oficial = Column(Text, nullable=False)
    orgao_emissor = Column(String(200), nullable=False)
    confirmada = Column(Boolean, nullable=False, default=False)
    metadados_json = Column(Text, nullable=False, default="{}")
    verificada_em = Column(DateTime)


class CardFonteJuridica(Base):
    __tablename__ = "cards_fontes_juridicas"

    id = Column(Integer, primary_key=True)
    card_id = Column(Integer, ForeignKey("cards_decisao_catalogo.id"), nullable=False)
    fonte_id = Column(Integer, ForeignKey("fontes_juridicas.id"), nullable=False)
    dispositivo = Column(String(200), nullable=False)


class CampanhaPesquisaPrecos(Base):
    __tablename__ = "campanhas_pesquisa_precos"

    id = Column(Integer, primary_key=True, index=True)
    contratacao_id = Column(Integer, ForeignKey("contratacoes.id"), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="planejada")
    objeto_canonico_json = Column(Text, nullable=False)
    max_consultas = Column(Integer, nullable=False, default=10)
    resultado_json = Column(Text, nullable=False, default="{}")
    erro_mensagem = Column(Text)
    aprovado_por_usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    aprovado_em = Column(DateTime)
    criado_em = Column(DateTime, server_default=func.now())
    atualizado_em = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ConsultaPesquisaPrecos(Base):
    __tablename__ = "consultas_pesquisa_precos"

    id = Column(Integer, primary_key=True, index=True)
    campanha_id = Column(Integer, ForeignKey("campanhas_pesquisa_precos.id"), nullable=False, index=True)
    pesquisa_id = Column(Integer, ForeignKey("pesquisas.id"), nullable=True)
    ordem = Column(Integer, nullable=False)
    termo = Column(String(500), nullable=False)
    status = Column(String(30), nullable=False, default="pendente")
    processos_encontrados = Column(Integer, nullable=False, default=0)
    processos_novos = Column(Integer, nullable=False, default=0)
    erro_mensagem = Column(Text)
    criado_em = Column(DateTime, server_default=func.now())


class ObservacaoPreco(Base):
    __tablename__ = "observacoes_precos"

    id = Column(Integer, primary_key=True, index=True)
    campanha_id = Column(Integer, ForeignKey("campanhas_pesquisa_precos.id"), nullable=False, index=True)
    consulta_id = Column(Integer, ForeignKey("consultas_pesquisa_precos.id"), nullable=False)
    chave_fonte = Column(String(64), nullable=False, unique=True, index=True)
    processo_url = Column(Text, nullable=False)
    numero_processo = Column(String(200))
    comprador = Column(String(500))
    descricao_item = Column(Text, nullable=False)
    quantidade = Column(String(100))
    unidade = Column(String(100))
    valor_unitario = Column(String(80), nullable=False)
    tipo_valor = Column(String(30), nullable=False, default="referencia")
    aderencia_pct = Column(Integer, nullable=False, default=0)
    comparavel = Column(Boolean, nullable=False, default=True)
    motivo_exclusao = Column(Text)
    documento_origem = Column(Text)
    status_validacao = Column(String(30), nullable=False, default="pendente")
    criado_em = Column(DateTime, server_default=func.now())
