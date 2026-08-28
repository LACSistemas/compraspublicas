import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import get_active_user
from app.database import Base, get_db
from app.models import Analise, BaseConhecimento, Contratacao, EvidenciaPlano, Geracao, PerguntaContratacao, Pesquisa, PlanoInformacao, Usuario
from app.routers import analises, contratacoes, geracoes, pesquisas
from app.services.planejamento_service import (
    _catalogo, _executar_coleta_deterministica, _proposta_fallback,
    _validar_e_persistir, _validar_qualidade_perguntas,
)
from app.services.plano_investigacao_service import criar_plano_deterministico
from app.services import plano_investigacao_service
from app.services.coleta_plano_service import consolidar_resultado_coleta
from app.services.coleta_plano_service import listar_lacunas
from app.services.evidencia_plano_service import criar_evidencia
from app.services.gerador_etp_service import _montar_dados_processo
from app.services import planejamento_service
from app.schemas import GeracaoCreate
from app.services.job_checkpoint_service import atualizar_job, criar_job, executar_com_retry_idempotente
from app.services.politica_governanca_service import robustez_minima_aprovacao


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def users(db_session):
    owner = Usuario(
        email="owner@example.test",
        nome="Owner",
        hashed_password="unused",
        is_active=True,
        is_owner=True,
    )
    other = Usuario(
        email="other@example.test",
        nome="Other",
        hashed_password="unused",
        is_active=True,
        is_owner=False,
    )
    db_session.add_all([owner, other])
    db_session.commit()
    db_session.refresh(owner)
    db_session.refresh(other)
    return owner, other


@pytest.fixture()
def app_client(db_session, users, monkeypatch):
    owner, _ = users
    app = FastAPI()
    app.include_router(pesquisas.router)
    app.include_router(analises.router)
    app.include_router(geracoes.router)
    app.include_router(contratacoes.router)

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_active_user] = lambda: owner

    monkeypatch.setattr(pesquisas, "iniciar_job_scraping", lambda *args: None)
    monkeypatch.setattr(analises, "iniciar_job_analise", lambda *args: None)
    monkeypatch.setattr(geracoes, "iniciar_job_geracao", lambda *args: None)
    monkeypatch.setattr(contratacoes, "iniciar_planejamento", lambda *args: None)
    monkeypatch.setattr(contratacoes, "iniciar_geracao_perguntas", lambda *args: None)
    monkeypatch.setattr(contratacoes, "iniciar_coleta_plano", lambda *args: None)
    monkeypatch.setattr(contratacoes, "iniciar_job_geracao", lambda *args: None)

    return app, TestClient(app)


def test_recomendacao_e_documento_sao_operaveis_na_contratacao_legada(
    app_client, db_session, users,
):
    _, client = app_client
    owner, _ = users
    contratacao = Contratacao(
        usuario_id=owner.id,
        objeto="Câmeras urbanas",
        orgao_unidade="Prefeitura",
        status="bcc_ativa",
    )
    db_session.add(contratacao)
    db_session.flush()
    db_session.add(BaseConhecimento(
        contratacao_id=contratacao.id,
        dados_json=json.dumps({"recomendacoes": [{"descricao": "Exigir IK10", "status": "pendente"}]}),
        progresso_pct=80,
        nivel_maturidade="Maduro",
    ))
    db_session.commit()

    response = client.patch(
        f"/contratacoes/{contratacao.id}/bcc/recomendacoes",
        json={"idx": 0, "decisao": "executar"},
    )
    assert response.status_code == 200
    assert response.json()["dados"]["recomendacoes"][0]["status"] == "executada"

    response = client.post(
        f"/contratacoes/{contratacao.id}/documentos",
        json={"tipo": "tr", "un_gestora": "Prefeitura", "responsaveis": "Equipe"},
    )
    assert response.status_code == 202
    pesquisa = db_session.query(Pesquisa).filter_by(contratacao_id=contratacao.id).one()
    assert pesquisa.status == "completo"
    assert db_session.query(Geracao).filter_by(pesquisa_id=pesquisa.id, tipo="tr").count() == 1


def test_processamento_cria_rodada_complementar_para_lacunas_obrigatorias(
    app_client, db_session, users,
):
    _, client = app_client
    owner, _ = users
    contratacao = Contratacao(
        usuario_id=owner.id, objeto="Ambulância", orgao_unidade="Saúde",
        status="investigacao",
    )
    db_session.add(contratacao)
    db_session.flush()
    plano = criar_plano_deterministico(db_session, contratacao)
    catalogo = _catalogo(db_session, plano)
    _validar_e_persistir(db_session, contratacao, plano, _proposta_fallback(catalogo))
    db_session.commit()

    perguntas_iniciais = db_session.query(PerguntaContratacao).filter_by(
        contratacao_id=contratacao.id).all()
    for pergunta in perguntas_iniciais:
        pergunta.resposta_escolhida = "a"
        if pergunta.plano_informacao_id:
            execucao = db_session.query(PlanoInformacao).filter_by(
                id=pergunta.plano_informacao_id).one()
            execucao.estado_semantico = "informado"
            execucao.status = "coletada_resposta"
    db_session.commit()

    response = client.post(f"/contratacoes/{contratacao.id}/processar-base")
    assert response.status_code == 202
    assert response.json()["perguntas_adicionais"] > 0
    assert db_session.query(Contratacao).filter_by(id=contratacao.id).one().status == "investigacao"
    assert db_session.query(PerguntaContratacao).filter_by(
        contratacao_id=contratacao.id).count() > len(perguntas_iniciais)


def _fixture_resultado() -> str:
    fixture = Path(__file__).parent / "fixtures" / "pesquisa_completa.json"
    return fixture.read_text(encoding="utf-8")


def test_criar_e_listar_pesquisa_sem_disparar_integracoes(app_client, db_session, users):
    _, client = app_client
    owner, _ = users

    response = client.post(
        "/pesquisas",
        json={"termo_busca": "cafe", "quantidade_desejada": "100 kg"},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "pendente"
    pesquisa = db_session.query(Pesquisa).one()
    assert pesquisa.usuario_id == owner.id
    assert pesquisa.termo_busca == "cafe"

    response = client.get("/pesquisas")
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [pesquisa.id]


def test_usuario_nao_acessa_pesquisa_de_outro_usuario(app_client, db_session, users):
    app, client = app_client
    _, other = users
    pesquisa = Pesquisa(
        usuario_id=other.id,
        termo_busca="restrita",
        limite_processos=1,
        status="completo",
        resultado_json=_fixture_resultado(),
    )
    db_session.add(pesquisa)
    db_session.commit()

    assert client.get(f"/pesquisas/{pesquisa.id}").status_code == 404
    assert client.get(f"/pesquisas/{pesquisa.id}/status").status_code == 404


def test_analise_exige_pesquisa_completa_e_impede_job_duplicado(
    app_client, db_session, users
):
    _, client = app_client
    owner, _ = users
    pesquisa = Pesquisa(
        usuario_id=owner.id,
        termo_busca="cafe",
        limite_processos=1,
        status="pendente",
    )
    db_session.add(pesquisa)
    db_session.commit()

    response = client.post(f"/pesquisas/{pesquisa.id}/analise")
    assert response.status_code == 409

    pesquisa.status = "completo"
    pesquisa.resultado_json = _fixture_resultado()
    db_session.commit()
    response = client.post(f"/pesquisas/{pesquisa.id}/analise")
    assert response.status_code == 202

    response = client.post(f"/pesquisas/{pesquisa.id}/analise")
    assert response.status_code == 409
    assert db_session.query(Analise).count() == 1


def test_geracao_preserva_tipo_e_impede_job_duplicado(app_client, db_session, users):
    _, client = app_client
    owner, _ = users
    pesquisa = Pesquisa(
        usuario_id=owner.id,
        termo_busca="cafe",
        limite_processos=1,
        status="completo",
        resultado_json=_fixture_resultado(),
    )
    db_session.add(pesquisa)
    db_session.commit()

    payload = {
        "tipo": "etp",
        "un_gestora": "Unidade de Teste",
        "responsaveis": "Equipe de Teste",
    }
    response = client.post(f"/pesquisas/{pesquisa.id}/etp", json=payload)
    assert response.status_code == 202
    assert db_session.query(Geracao).one().tipo == "etp"

    response = client.post(f"/pesquisas/{pesquisa.id}/etp", json=payload)
    assert response.status_code == 409
    assert db_session.query(Geracao).count() == 1


def test_tipos_documentais_preparatorios_e_bloqueio_de_edital_contrato():
    for tipo in ("dfd", "etp", "mapa_riscos", "tr"):
        assert GeracaoCreate(tipo=tipo, un_gestora="UG", responsaveis="Equipe").tipo == tipo
    for tipo in ("edital", "contrato"):
        with pytest.raises(ValueError):
            GeracaoCreate(tipo=tipo, un_gestora="UG", responsaveis="Equipe")


def test_documento_bloqueia_path_traversal(app_client, db_session, users, tmp_path):
    _, client = app_client
    owner, _ = users
    pasta = tmp_path / "documentos"
    pasta.mkdir()
    (pasta / "edital.pdf").write_bytes(b"%PDF-fixture")
    segredo = tmp_path / "segredo.txt"
    segredo.write_text("nao deve ser servido", encoding="utf-8")
    pesquisa = Pesquisa(
        usuario_id=owner.id,
        termo_busca="cafe",
        limite_processos=1,
        status="completo",
        resultado_json=json.dumps({"processos": []}),
        pasta_downloads=str(pasta),
    )
    db_session.add(pesquisa)
    db_session.commit()

    assert (
        client.get(f"/pesquisas/{pesquisa.id}/documentos/edital.pdf").status_code
        == 200
    )
    assert (
        client.get(f"/pesquisas/{pesquisa.id}/documentos/%2E%2E/segredo.txt").status_code
        == 404
    )


def test_plano_piloto_e_idempotente_e_isolado(app_client, db_session, users, monkeypatch):
    _, client = app_client
    owner, other = users
    monkeypatch.setattr(contratacoes.settings, "INVESTIGACAO_HABILITADA", True)
    propria = Contratacao(usuario_id=owner.id, objeto="Café", orgao_unidade="Compras", status="cadastro")
    alheia = Contratacao(usuario_id=other.id, objeto="Veículo", orgao_unidade="Transportes", status="cadastro")
    db_session.add_all([propria, alheia])
    db_session.commit()

    response = client.post(f"/contratacoes/{propria.id}/plano")
    assert response.status_code == 201
    dados = response.json()
    assert [card["codigo"] for card in dados["cards"]] == [f"D{numero:03d}" for numero in range(1, 15)]
    assert all(card["informacoes"] for card in dados["cards"])
    assert dados["cards"][0]["dependencias"] == []
    assert dados["cards"][1]["dependencias"] == ["D001"]
    assert dados["cards"][2]["dependencias"] == ["D001"]
    assert set(dados["cards"][-1]["dependencias"]) == {
        "D006", "D007", "D008", "D009", "D010", "D011", "D012", "D013"
    }

    repetido = client.post(f"/contratacoes/{propria.id}/plano")
    assert repetido.status_code == 201
    assert repetido.json()["id"] == dados["id"]
    assert client.get(f"/contratacoes/{propria.id}/plano").status_code == 200
    assert client.get(f"/contratacoes/{alheia.id}/plano").status_code == 404


def test_catalogo_valida_referencias_tipos_estrategias_e_ciclos(monkeypatch):
    plano_investigacao_service.validar_catalogo()
    dependencias = dict(plano_investigacao_service.DEPENDENCIAS)
    dependencias["D001"] = ("D014",)
    monkeypatch.setattr(plano_investigacao_service, "DEPENDENCIAS", dependencias)
    with pytest.raises(ValueError, match="Ciclo detectado"):
        plano_investigacao_service.validar_catalogo()
    assert robustez_minima_aprovacao("D001") == 75
    assert robustez_minima_aprovacao("D005") == 60


def test_plano_fica_oculto_com_feature_flag_desligada(app_client, db_session, users, monkeypatch):
    _, client = app_client
    owner, _ = users
    monkeypatch.setattr(contratacoes.settings, "INVESTIGACAO_HABILITADA", False)
    c = Contratacao(usuario_id=owner.id, objeto="Café", orgao_unidade="Compras", status="cadastro")
    db_session.add(c)
    db_session.commit()
    assert client.post(f"/contratacoes/{c.id}/plano").status_code == 404


def test_iniciar_investigacao_escolhe_fluxo_por_feature_flag(app_client, db_session, users, monkeypatch):
    _, client = app_client
    owner, _ = users
    chamadas = []
    monkeypatch.setattr(contratacoes, "iniciar_planejamento", lambda cid: chamadas.append(("plano", cid)))
    monkeypatch.setattr(contratacoes, "iniciar_geracao_perguntas", lambda cid: chamadas.append(("perguntas", cid)))
    c1 = Contratacao(usuario_id=owner.id, objeto="Café", orgao_unidade="Compras", status="cadastro")
    c2 = Contratacao(usuario_id=owner.id, objeto="Papel", orgao_unidade="Compras", status="cadastro")
    db_session.add_all([c1, c2])
    db_session.commit()

    monkeypatch.setattr(contratacoes.settings, "INVESTIGACAO_HABILITADA", True)
    assert client.post(f"/contratacoes/{c1.id}/iniciar-investigacao").status_code == 202
    assert c1.status == "gerando_plano"
    monkeypatch.setattr(contratacoes.settings, "INVESTIGACAO_HABILITADA", False)
    assert client.post(f"/contratacoes/{c2.id}/iniciar-investigacao").status_code == 202
    assert c2.status == "gerando_perguntas"
    assert chamadas == [("plano", c1.id), ("perguntas", c2.id)]


def test_planejamento_cria_perguntas_apenas_para_estrategia_pergunta(db_session, users):
    owner, _ = users
    c = Contratacao(usuario_id=owner.id, objeto="Café", orgao_unidade="Compras", status="gerando_plano")
    db_session.add(c)
    db_session.commit()
    plano = criar_plano_deterministico(db_session, c)
    alternativas = [{"letra": letra, "texto": f"Opção {letra}"} for letra in "abcde"]
    dados = _proposta_fallback(_catalogo(db_session, plano))
    for card in dados["cards"]:
        for info in card["informacoes"]:
            if info["codigo"] not in {"I001", "I004"} and info["estrategia"] == "pergunta":
                info["estrategia"], info["pergunta"] = "consulta", None
    por_info = {info["codigo"]: info for card in dados["cards"] for info in card["informacoes"]}
    por_info["I001"]["pergunta"] = {"texto": "Qual problema público será resolvido?", "alternativas": alternativas}
    por_info["I004"]["pergunta"] = {"texto": "Como medir o resultado?", "alternativas": alternativas}
    _validar_e_persistir(db_session, c, plano, dados)
    db_session.commit()
    perguntas = db_session.query(PerguntaContratacao).order_by(PerguntaContratacao.ordem).all()
    assert [p.texto for p in perguntas] == ["Qual problema público será resolvido?", "Como medir o resultado?"]


def test_fallback_deterministico_respeita_catalogo_e_quantidade_variavel(db_session, users):
    owner, _ = users
    c = Contratacao(usuario_id=owner.id, objeto="Café", orgao_unidade="Compras", status="gerando_plano")
    db_session.add(c)
    db_session.commit()
    plano = criar_plano_deterministico(db_session, c)
    proposta = _proposta_fallback(_catalogo(db_session, plano))
    _validar_e_persistir(db_session, c, plano, proposta)
    db_session.commit()
    perguntas = db_session.query(PerguntaContratacao).all()
    assert 0 < len(perguntas) < 25
    assert all(len(p.alternativas) == 5 for p in perguntas)


def test_planejamento_persiste_rastreabilidade_e_reutiliza_hash(db_session, users, monkeypatch):
    owner, _ = users
    c = Contratacao(usuario_id=owner.id, objeto="Café", orgao_unidade="Compras",
        contexto_inicial="Demanda documentada", status="gerando_plano")
    db_session.add(c)
    db_session.commit()
    contratacao_id = c.id
    chamadas = []

    def gemini_indisponivel(prompt):
        chamadas.append(prompt)
        raise RuntimeError("Gemini indisponível no teste")

    monkeypatch.setattr(planejamento_service, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(planejamento_service, "chamar_gemini", gemini_indisponivel)
    planejamento_service._job_planejar(contratacao_id)
    planejamento_service._job_planejar(contratacao_id)

    from app.models import ExecucaoIA
    execucoes = db_session.query(ExecucaoIA).all()
    assert len(chamadas) == 1
    assert len(execucoes) == 1
    assert execucoes[0].status == "fallback"
    assert execucoes[0].prompt_versao == planejamento_service.PROMPT_VERSAO
    assert len(execucoes[0].hash_entrada) == 64
    assert json.loads(execucoes[0].catalogo_json)[0]["codigo"] == "D001"
    assert json.loads(execucoes[0].saida_json)["cards"]


def test_metricas_e_orcamento_de_tokens_por_contratacao(app_client, db_session, users, monkeypatch):
    _, client = app_client
    owner, _ = users
    monkeypatch.setattr(contratacoes.settings, "INVESTIGACAO_HABILITADA", True)
    monkeypatch.setattr(contratacoes.settings, "TOKEN_BUDGET_CONTRATACAO", 100)
    c = Contratacao(usuario_id=owner.id, objeto="Café", orgao_unidade="Compras", status="investigacao")
    db_session.add(c)
    db_session.commit()
    from app.models import ExecucaoIA
    db_session.add(ExecucaoIA(contratacao_id=c.id, fase="plano_investigacao",
        hash_entrada="a" * 64, prompt_versao="v1", prompt_texto="prompt",
        entrada_json="{}", tokens_total=100, status="sucesso"))
    db_session.commit()
    resposta = client.get(f"/contratacoes/{c.id}/plano/metricas-ia")
    assert resposta.status_code == 200
    assert resposta.json()["por_fase"]["planejamento"] == 100
    assert resposta.json()["disponivel"] == 0
    assert resposta.json()["excedido"] is True


def test_job_persistente_registra_tentativa_etapa_e_checkpoint(app_client, db_session, users):
    _, client = app_client
    owner, _ = users
    c = Contratacao(usuario_id=owner.id, objeto="Café", orgao_unidade="Compras", status="investigacao")
    db_session.add(c)
    db_session.commit()
    job = criar_job(db_session, "planejamento", c.id, referencia_id=c.id)
    atualizar_job(db_session, job.id, status="em_andamento", etapa="planejando",
        checkpoint={"passo": 1}, incrementar_tentativa=True)
    resposta = client.get(f"/contratacoes/{c.id}/jobs")
    assert resposta.status_code == 200
    assert resposta.json()[0]["etapa"] == "planejando"
    assert resposta.json()[0]["tentativa"] == 1
    assert resposta.json()[0]["checkpoint"] == {"passo": 1}


def test_retry_idempotente_repete_mesmo_job_e_para_ao_concluir(db_session, users):
    owner, _ = users
    c = Contratacao(usuario_id=owner.id, objeto="Café", orgao_unidade="Compras", status="investigacao")
    db_session.add(c)
    db_session.commit()
    job = criar_job(db_session, "teste", c.id, referencia_id=77, max_tentativas=2)
    job_id = job.id
    chamadas, estado = [], {"concluido": False}

    def operacao():
        chamadas.append(1)
        if len(chamadas) == 1:
            raise RuntimeError("falha transitória")
        estado["concluido"] = True

    assert executar_com_retry_idempotente(lambda: db_session, job_id, operacao,
        lambda: estado["concluido"], etapa_execucao="executando", etapa_sucesso="salvo",
        checkpoint=lambda: dict(estado)) is True
    from app.models import JobExecucao
    persistido = db_session.query(JobExecucao).filter_by(id=job_id).one()
    assert len(chamadas) == 2
    assert persistido.status == "completo"
    assert persistido.tentativa == 2
    assert persistido.referencia_id == 77


def test_inferencia_e_candidata_rastreavel_e_nao_resposta_do_gestor(db_session, users):
    owner, _ = users
    c = Contratacao(usuario_id=owner.id, objeto="Café", orgao_unidade="Compras",
        contexto_inicial="Há aumento documentado de demanda nas unidades.", status="gerando_plano")
    db_session.add(c)
    db_session.commit()
    plano = criar_plano_deterministico(db_session, c)
    proposta = _proposta_fallback(_catalogo(db_session, plano))
    proposta["cards"][1]["informacoes"][0]["estrategia"] = "inferencia"
    proposta["cards"][1]["informacoes"][0]["pergunta"] = None
    _validar_e_persistir(db_session, c, plano, proposta)
    _executar_coleta_deterministica(db_session, c, plano)
    db_session.commit()
    from app.models import PlanoInformacao
    inferida = db_session.query(PlanoInformacao).filter_by(
        estrategia="inferencia", origem="inferencia_contexto_inicial").first()
    assert inferida.status == "coletada_inferida"
    assert inferida.origem == "inferencia_contexto_inicial"
    assert inferida.confianca == "baixa"
    assert "exige confirmação" in inferida.valor_json


def test_consulta_e_integracao_reutilizam_resultado_estruturado(db_session, users):
    owner, _ = users
    c = Contratacao(usuario_id=owner.id, objeto="Café", orgao_unidade="Compras", status="investigacao")
    db_session.add(c)
    db_session.commit()
    plano = criar_plano_deterministico(db_session, c)
    proposta = _proposta_fallback(_catalogo(db_session, plano))
    _validar_e_persistir(db_session, c, plano, proposta)
    resultado = {"processos": [{"url": "https://example.test/1", "comprador": "Órgão A",
        "numero_processo": "1/2026", "itens": [{"descricao": "Café", "quantidade": "100", "unidade": "kg"}]}]}
    quantidade = consolidar_resultado_coleta(db_session, plano.id, resultado)
    assert quantidade >= 2
    db_session.commit()
    from app.models import PlanoInformacao
    coletadas = db_session.query(PlanoInformacao).filter_by(status="coletada").all()
    assert {item.estrategia for item in coletadas} == {"consulta", "integracao"}
    assert all(item.origem == "portal_compras_http" for item in coletadas)
    assert db_session.query(EvidenciaPlano).count() == quantidade
    assert consolidar_resultado_coleta(db_session, plano.id, resultado) == 0
    assert db_session.query(EvidenciaPlano).count() == quantidade


def test_endpoint_coleta_exige_plano_e_evitar_duplicidade(app_client, db_session, users, monkeypatch):
    _, client = app_client
    owner, _ = users
    monkeypatch.setattr(contratacoes.settings, "INVESTIGACAO_HABILITADA", True)
    chamadas = []
    monkeypatch.setattr(contratacoes, "iniciar_coleta_plano", lambda *args: chamadas.append(args))
    c = Contratacao(usuario_id=owner.id, objeto="Café", orgao_unidade="Compras", status="investigacao")
    db_session.add(c)
    db_session.commit()
    assert client.post(f"/contratacoes/{c.id}/plano/coletar").status_code == 409
    plano = criar_plano_deterministico(db_session, c)
    _validar_e_persistir(db_session, c, plano, _proposta_fallback(_catalogo(db_session, plano)))
    db_session.commit()
    response = client.post(f"/contratacoes/{c.id}/plano/coletar")
    assert response.status_code == 202
    assert chamadas == [(c.id, owner.id)]


def test_lacunas_priorizam_automaticas_e_opcionais_nao_bloqueiam(
    app_client, db_session, users, monkeypatch
):
    _, client = app_client
    owner, other = users
    monkeypatch.setattr(contratacoes.settings, "INVESTIGACAO_HABILITADA", True)
    c = Contratacao(usuario_id=owner.id, objeto="Café", orgao_unidade="Compras", status="investigacao")
    db_session.add(c)
    db_session.commit()
    plano = criar_plano_deterministico(db_session, c)
    _validar_e_persistir(db_session, c, plano, _proposta_fallback(_catalogo(db_session, plano)))
    db_session.commit()

    resumo = listar_lacunas(db_session, plano.id)
    assert resumo["bloqueantes"] > 0
    assert resumo["opcionais"] > 0
    assert resumo["proxima_estrategia"] == "consulta"
    assert [l["prioridade"] for l in resumo["lacunas"] if l["obrigatoria"]] == sorted(
        l["prioridade"] for l in resumo["lacunas"] if l["obrigatoria"])

    bloqueantes = [l["plano_informacao_id"] for l in resumo["lacunas"] if l["obrigatoria"]]
    db_session.query(contratacoes.PlanoInformacao).filter(
        contratacoes.PlanoInformacao.id.in_(bloqueantes)).update(
            {"status": "coletada"}, synchronize_session=False)
    db_session.commit()
    resposta = client.get(f"/contratacoes/{c.id}/plano/lacunas")
    assert resposta.status_code == 200
    assert resposta.json()["bloqueantes"] == 0
    assert resposta.json()["opcionais"] > 0
    assert resposta.json()["pronto_para_conhecimento"] is True

    monkeypatch.setattr(contratacoes, "get_active_user", lambda: other)
    app_client[0].dependency_overrides[get_active_user] = lambda: other
    assert client.get(f"/contratacoes/{c.id}/plano/lacunas").status_code == 404


def test_upload_documental_valida_conteudo_e_vincula_informacao(
    app_client, db_session, users, monkeypatch, tmp_path
):
    _, client = app_client
    owner, _ = users
    monkeypatch.setattr(contratacoes.settings, "INVESTIGACAO_HABILITADA", True)
    monkeypatch.setattr(contratacoes.settings, "UPLOADS_DIR", str(tmp_path / "uploads"))
    from types import SimpleNamespace
    monkeypatch.setattr(contratacoes, "extrair_e_registrar_pdf",
        lambda *args: SimpleNamespace(metodo_obtencao="extracao_falhou"))
    c = Contratacao(usuario_id=owner.id, objeto="Café", orgao_unidade="Compras", status="investigacao")
    db_session.add(c)
    db_session.commit()
    plano = criar_plano_deterministico(db_session, c)
    _validar_e_persistir(db_session, c, plano, _proposta_fallback(_catalogo(db_session, plano)))
    db_session.commit()
    from app.models import PlanoInformacao
    upload = db_session.query(PlanoInformacao).filter_by(estrategia="upload").first()

    invalido = client.post(
        f"/contratacoes/{c.id}/plano/informacoes/{upload.id}/upload",
        files={"arquivo": ("memoria.pdf", b"nao e pdf", "application/pdf")},
    )
    assert invalido.status_code == 415

    valido = client.post(
        f"/contratacoes/{c.id}/plano/informacoes/{upload.id}/upload",
        files={"arquivo": ("../memoria.pdf", b"%PDF-1.4 fixture", "application/pdf")},
    )
    assert valido.status_code == 200
    db_session.refresh(upload)
    assert upload.status == "coletada_upload"
    assert upload.origem == "upload_usuario"
    assert upload.confianca == "alta"
    assert json.loads(upload.valor_json)["nome_original"] == "memoria.pdf"
    evidencias = client.get(f"/contratacoes/{c.id}/plano/evidencias")
    assert evidencias.status_code == 200
    assert len(evidencias.json()) == 1
    evidencia_id = evidencias.json()[0]["id"]
    validada = client.patch(
        f"/contratacoes/{c.id}/plano/evidencias/{evidencia_id}",
        json={"status_validacao": "confirmada"},
    )
    assert validada.status_code == 200
    assert validada.json()["status_validacao"] == "confirmada"
    db_session.refresh(upload)
    assert upload.estado_semantico == "confirmado"


def test_evidencia_nova_conflita_e_substituicao_e_explicita(app_client, db_session, users, monkeypatch):
    _, client = app_client
    owner, _ = users
    monkeypatch.setattr(contratacoes.settings, "INVESTIGACAO_HABILITADA", True)
    c = Contratacao(usuario_id=owner.id, objeto="Café", orgao_unidade="Compras", status="investigacao")
    db_session.add(c)
    db_session.commit()
    plano = criar_plano_deterministico(db_session, c)
    _validar_e_persistir(db_session, c, plano, _proposta_fallback(_catalogo(db_session, plano)))
    from app.models import PlanoInformacao
    info = db_session.query(PlanoInformacao).first()
    anterior = criar_evidencia(db_session, info.id, tipo="declaracao", descricao="Versão 1",
        conteudo={"valor": "A"}, origem="usuario", metodo_obtencao="pergunta", confianca="alta")
    nova = criar_evidencia(db_session, info.id, tipo="declaracao", descricao="Versão 2",
        conteudo={"valor": "B"}, origem="usuario", metodo_obtencao="pergunta", confianca="alta")
    db_session.commit()
    assert anterior.estado == "vigente"
    assert nova.estado == "conflitante"
    response = client.post(f"/contratacoes/{c.id}/plano/evidencias/{nova.id}/substituir",
        json={"evidencia_anterior_id": anterior.id})
    assert response.status_code == 200
    db_session.refresh(anterior)
    assert anterior.estado == "substituida"
    assert response.json()["estado"] == "vigente"
    assert response.json()["substitui_evidencia_id"] == anterior.id


def test_conhecimento_por_card_e_snapshot_bcc(app_client, db_session, users, monkeypatch):
    _, client = app_client
    owner, _ = users
    monkeypatch.setattr(contratacoes.settings, "INVESTIGACAO_HABILITADA", True)
    c = Contratacao(usuario_id=owner.id, objeto="Café", orgao_unidade="Compras", status="investigacao")
    db_session.add(c)
    db_session.commit()
    plano = criar_plano_deterministico(db_session, c)
    _validar_e_persistir(db_session, c, plano, _proposta_fallback(_catalogo(db_session, plano)))
    from app.models import CardInformacao, CriterioCardCatalogo, EvidenciaCriterio, PlanoInformacao
    itens = db_session.query(contratacoes.PlanoCardDecisao).filter_by(plano_id=plano.id).all()
    for item in itens:
        obrigatorias = db_session.query(CardInformacao).filter_by(
            card_id=item.card_id, obrigatoria=True).all()
        for indice, obrigatoria in enumerate(obrigatorias):
            info = db_session.query(PlanoInformacao).filter_by(
                plano_card_id=item.id, informacao_id=obrigatoria.informacao_id).one()
            ev = criar_evidencia(db_session, info.id, tipo="teste", descricao="Evidência confirmada",
                conteudo={"confirmado": True, "card": item.id, "info": info.id}, origem="fixture",
                metodo_obtencao="teste", confianca="alta")
            ev.status_validacao = "confirmada"
            if indice == 0:
                for criterio in db_session.query(CriterioCardCatalogo).filter_by(card_id=item.card_id).all():
                    db_session.add(EvidenciaCriterio(evidencia_id=ev.id, criterio_id=criterio.id))
    db_session.commit()
    gerados = client.post(f"/contratacoes/{c.id}/plano/conhecimentos")
    assert gerados.status_code == 200
    assert len(gerados.json()) == 14
    assert all(k["robustez_pct"] == 100 for k in gerados.json())
    assert all(k["fontes_confirmadas"][0]["codigo"] == "LEI-14133-2021" for k in gerados.json())
    fontes_d005 = next(k["fontes_confirmadas"] for k in gerados.json() if k["codigo_card"] == "D005")
    assert {fonte["orgao_emissor"] for fonte in fontes_d005} == {
        "Presidência da República", "TCU", "TCE-ES"
    }
    primeiro = gerados.json()[0]
    aprovado = client.patch(f"/contratacoes/{c.id}/plano/conhecimentos/{primeiro['id']}",
        json={"status": "aprovado"})
    assert aprovado.status_code == 200
    consolidada = client.post(f"/contratacoes/{c.id}/plano/consolidar-bcc")
    assert consolidada.status_code == 200
    assert consolidada.json()["dados"]["metricas"]["decisoes_total"] == 14
    from app.models import SnapshotBCC
    assert db_session.query(SnapshotBCC).filter_by(contratacao_id=c.id).count() == 1
    pesquisa = Pesquisa(usuario_id=owner.id, contratacao_id=c.id, termo_busca="Café",
        limite_processos=5, status="completo", resultado_json='{"processos": []}')
    db_session.add(pesquisa)
    db_session.commit()
    with pytest.raises(ValueError, match="Todos os Cards"):
        _montar_dados_processo(db_session, pesquisa, {})
    from app.models import ConhecimentoCard
    for conhecimento in db_session.query(ConhecimentoCard).all():
        conhecimento.status = "aprovado"
        conhecimento.aprovado_por_usuario_id = owner.id
    db_session.commit()
    assert client.post(f"/contratacoes/{c.id}/plano/consolidar-bcc").status_code == 200
    dados_geracao = json.loads(_montar_dados_processo(db_session, pesquisa, {}))
    assert dados_geracao["fonte_canonica"] == "snapshot_bcc_aprovado"
    assert dados_geracao["snapshot_bcc"]["versao"] == 2
    primeira_info = db_session.query(PlanoInformacao).filter_by(plano_card_id=itens[0].id).first()
    criar_evidencia(db_session, primeira_info.id, tipo="teste", descricao="Nova versão",
        conteudo={"alterado": True}, origem="fixture", metodo_obtencao="teste", confianca="alta")
    db_session.commit()
    assert db_session.query(ConhecimentoCard).filter_by(plano_card_id=itens[0].id).one().status == "superado"
    assert all(k.status != "superado" for k in db_session.query(ConhecimentoCard).filter(
        ConhecimentoCard.plano_card_id.in_([itens[1].id, itens[2].id])).all())
    reprocessados = client.post(f"/contratacoes/{c.id}/plano/conhecimentos")
    assert reprocessados.status_code == 200
    assert [item["codigo_card"] for item in reprocessados.json()] == ["D001"]
    versao_antiga = client.patch(
        f"/contratacoes/{c.id}/plano/conhecimentos/{primeiro['id']}", json={"status": "aprovado"})
    assert versao_antiga.status_code == 409
    assert "versão mais recente" in versao_antiga.json()["detail"]


def test_dispensa_proposta_exige_revisao_humana(app_client, db_session, users, monkeypatch):
    _, client = app_client
    owner, _ = users
    monkeypatch.setattr(contratacoes.settings, "INVESTIGACAO_HABILITADA", True)
    c = Contratacao(usuario_id=owner.id, objeto="Café", orgao_unidade="Compras", status="investigacao")
    db_session.add(c)
    db_session.commit()
    plano = criar_plano_deterministico(db_session, c)
    proposta = _proposta_fallback(_catalogo(db_session, plano))
    proposta["cards"][1]["aplicavel"] = False
    proposta["cards"][1]["justificativa"] = "Resultados já definidos em processo anterior"
    _validar_e_persistir(db_session, c, plano, proposta)
    db_session.commit()
    item = db_session.query(contratacoes.PlanoCardDecisao).filter_by(
        plano_id=plano.id, ordem=2).one()
    assert item.status == "dispensa_proposta"
    assert item.dispensa_status == "proposta"
    response = client.patch(f"/contratacoes/{c.id}/plano/cards/{item.id}/dispensa",
        json={"decisao": "rejeitar"})
    assert response.status_code == 200
    db_session.refresh(item)
    assert item.aplicavel is True
    assert item.dispensa_status == "rejeitada"
    assert item.dispensa_revisada_por_usuario_id == owner.id


def test_fallback_de_perguntas_e_especifico_e_passa_controle_de_qualidade(
        db_session, users):
    owner, _ = users
    contratacao = Contratacao(usuario_id=owner.id, objeto="Ambulância tipo 5",
        orgao_unidade="Saúde", status="gerando_plano")
    db_session.add(contratacao)
    db_session.commit()
    plano = criar_plano_deterministico(db_session, contratacao)
    proposta = _proposta_fallback(_catalogo(db_session, plano), contratacao.objeto)
    _validar_qualidade_perguntas(proposta)
    perguntas = [info["pergunta"] for card in proposta["cards"]
        for info in card["informacoes"] if info["pergunta"]]
    assert all("situação atual de" not in pergunta["texto"].lower() for pergunta in perguntas)
    assert len({tuple(a["texto"] for a in pergunta["alternativas"])
        for pergunta in perguntas}) == len(perguntas)
