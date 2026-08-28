import hashlib
import json
import math
import re
import statistics
import threading
import unicodedata
import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from app.config import settings
from app.database import SessionLocal
from app.models import (BaseConhecimento, CampanhaPesquisaPrecos, ConsultaPesquisaPrecos,
    Contratacao, EvidenciaPlano, HistoricoContratacao, InformacaoCatalogo,
    ObservacaoPreco, Pesquisa, PlanoCardDecisao, PlanoInformacao, PlanoInvestigacao,
    SnapshotBCC)
from app.scraper.scraping_core import executar_scraping
from app.services.evidencia_plano_service import criar_evidencia, substituir_evidencia
from app.services.gemini_service import chamar_gemini
from app.services.job_checkpoint_service import criar_job, executar_com_retry_idempotente
from app.services.coleta_plano_service import consolidar_resultado_coleta
from app.services.pdf_extractor import extrair_texto_pdf


STOPWORDS = {"a", "ao", "aos", "as", "com", "da", "das", "de", "do", "dos", "e",
    "em", "para", "por", "que", "tipo", "uma", "um", "aquisição", "contratação"}
logger = logging.getLogger("pesquisa_precos_service")


def _normalizar_texto(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", texto.lower()).strip()


def _tokens(texto: str) -> set[str]:
    return {p for p in _normalizar_texto(texto).split() if len(p) > 2 and p not in STOPWORDS}


def _perfil_objeto(c: Contratacao) -> dict:
    return {"descricao": c.objeto, "tipo": c.tipo_contratacao,
        "orgao_unidade": c.orgao_unidade, "contexto": c.contexto_inicial,
        "termos_essenciais": sorted(_tokens(c.objeto)), "quantidade": None,
        "unidade": None, "regiao": None, "exclusoes": []}


def _termos_fallback(perfil: dict, total: int) -> list[str]:
    objeto = perfil["descricao"].strip()
    essenciais = " ".join(perfil["termos_essenciais"])
    candidatos = [objeto, essenciais, f"aquisição {essenciais}",
        f"fornecimento {essenciais}", f"registro de preços {essenciais}",
        f"pregão {essenciais}", f"contratação {essenciais}", f"edital {essenciais}",
        f"termo de referência {essenciais}", f"ata de preços {essenciais}"]
    unicos = []
    for termo in candidatos:
        termo = re.sub(r"\s+", " ", termo).strip()
        if termo and termo.casefold() not in {x.casefold() for x in unicos}:
            unicos.append(termo)
    return unicos[:total]


def _planejar_termos(perfil: dict, total: int) -> list[str]:
    prompt = ("Gere variações curtas de busca para localizar contratações públicas comparáveis. "
        "Não invente especificações. Retorne JSON {\"termos\": [strings]}. Use nome exato, "
        "sinônimos administrativos e descrição técnica resumida.\nOBJETO:\n" +
        json.dumps(perfil, ensure_ascii=False) + f"\nQUANTIDADE: {total}")
    try:
        dados, _ = chamar_gemini(prompt)
        termos = [str(t).strip() for t in dados.get("termos", []) if str(t).strip()]
        termos = list(dict.fromkeys([perfil["descricao"], *termos]))
        if len(termos) >= total:
            return termos[:total]
    except Exception:
        pass
    return _termos_fallback(perfil, total)


def _decimal(valor) -> Decimal | None:
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float, Decimal)):
        try: return Decimal(str(valor))
        except InvalidOperation: return None
    texto = re.sub(r"[^0-9,.-]", "", str(valor))
    if not texto: return None
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try: return Decimal(texto)
    except InvalidOperation: return None


def _aderencia(perfil: dict, descricao: str) -> int:
    base, item = set(perfil["termos_essenciais"]), _tokens(descricao)
    return round(100 * len(base & item) / max(1, len(base)))


def _percentil(valores: list[float], p: float) -> float:
    if len(valores) == 1: return valores[0]
    pos = (len(valores) - 1) * p
    baixo, alto = math.floor(pos), math.ceil(pos)
    if baixo == alto: return valores[baixo]
    return valores[baixo] + (valores[alto] - valores[baixo]) * (pos - baixo)


def _calcular_resultado(observacoes: list[ObservacaoPreco], consultas: list[ConsultaPesquisaPrecos]) -> dict:
    candidatas = [o for o in observacoes if o.comparavel and o.aderencia_pct >= 40]
    valores = sorted(float(Decimal(o.valor_unitario)) for o in candidatas)
    if not valores:
        return {"amostra": 0, "consultas_executadas": len(consultas),
            "processos_unicos": len({o.processo_url for o in observacoes}),
            "confianca": "insuficiente", "pendencias": ["Nenhum preço comparável foi identificado"]}
    q1, q3 = _percentil(valores, .25), _percentil(valores, .75)
    iqr = q3 - q1
    inferior, superior = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    tratados = [v for v in valores if inferior <= v <= superior]
    outliers = [v for v in valores if v < inferior or v > superior]
    confianca = "alta" if len(tratados) >= 8 else "media" if len(tratados) >= 3 else "baixa"
    return {"amostra": len(valores), "amostra_tratada": len(tratados),
        "consultas_executadas": len(consultas),
        "processos_unicos": len({o.processo_url for o in observacoes}),
        "menor": min(tratados), "maior": max(tratados),
        "mediana": statistics.median(tratados), "media_tratada": statistics.mean(tratados),
        "q1": q1, "q3": q3, "outliers": outliers, "confianca": confianca,
        "moeda": "BRL", "criterio_outlier": "1,5 × intervalo interquartil",
        "pendencias": ([] if len(tratados) >= 3 else ["Ampliar a amostra antes da aprovação"])}


def consolidar_campanha_no_plano(db, campanha: CampanhaPesquisaPrecos) -> int:
    plano = (db.query(PlanoInvestigacao).filter_by(contratacao_id=campanha.contratacao_id)
        .order_by(PlanoInvestigacao.versao.desc()).first())
    if plano is None:
        return 0
    processos, vistos = [], set()
    consultas = db.query(ConsultaPesquisaPrecos).filter_by(campanha_id=campanha.id).all()
    for consulta in consultas:
        if not consulta.pesquisa_id:
            continue
        pesquisa = db.query(Pesquisa).filter_by(id=consulta.pesquisa_id).first()
        resultado = json.loads(pesquisa.resultado_json) if pesquisa and pesquisa.resultado_json else {}
        for processo in resultado.get("processos", []):
            chave = processo.get("url") or processo.get("numero_processo")
            if chave and chave not in vistos:
                vistos.add(chave)
                processos.append(processo)
    return consolidar_resultado_coleta(db, plano.id, {"processos": processos})


def extrair_documentos_comparaveis(db, campanha: CampanhaPesquisaPrecos, limite: int = 6) -> int:
    resultado = json.loads(campanha.resultado_json or "{}")
    if resultado.get("documentos_comparaveis"):
        return len(resultado["documentos_comparaveis"])
    consultas = db.query(ConsultaPesquisaPrecos).filter_by(campanha_id=campanha.id).all()
    candidatos = []
    prioridades = {"termo de referencia": 12, "termo_de_referencia": 12, "tr ": 10,
        "estudo tecnico": 11, "etp": 10, "especific": 9, "edital": 5}
    penalidades = {"impugn": -8, "retific": -3, "publica": -6, "parecer": -5}
    for consulta in consultas:
        if not consulta.pesquisa_id:
            continue
        pesquisa = db.query(Pesquisa).filter_by(id=consulta.pesquisa_id).first()
        if not pesquisa or not pesquisa.pasta_downloads:
            continue
        for caminho in Path(pesquisa.pasta_downloads).rglob("*.pdf"):
            nome = _normalizar_texto(caminho.name)
            score = sum(peso for termo, peso in prioridades.items() if termo in nome)
            score += sum(peso for termo, peso in penalidades.items() if termo in nome)
            if score > 0:
                candidatos.append((score, caminho))
    selecionados, processos_usados = [], set()
    perfil = json.loads(campanha.objeto_canonico_json)
    for _, caminho in sorted(candidatos, key=lambda item: (-item[0], str(item[1]))):
        processo = str(caminho.parent)
        if processo in processos_usados:
            continue
        extracao = extrair_texto_pdf(str(caminho))
        texto = extracao.get("texto", "").strip()
        if len(texto) < 200:
            continue
        aderencia = _aderencia(perfil, texto[:30000])
        if aderencia < 20:
            continue
        processos_usados.add(processo)
        selecionados.append({"arquivo": str(caminho), "nome": caminho.name,
            "processo_local": caminho.parent.name, "aderencia_pct": aderencia,
            "metodo_extracao": extracao.get("metodo"), "status_extracao": extracao.get("status"),
            "trecho_extraido": texto[:12000],
            "hash_texto": hashlib.sha256(texto.encode()).hexdigest()})
        if len(selecionados) >= limite:
            break
    resultado["documentos_comparaveis"] = selecionados
    resultado["aviso_documental"] = ("Referências externas comparáveis; requisitos, quantidades e "
        "condições somente podem ser adotados após validação para a realidade local.")
    campanha.resultado_json = json.dumps(resultado, ensure_ascii=False)
    return len(selecionados)


def _executar_campanha(campanha_id: int) -> None:
    db = SessionLocal()
    try:
        campanha = db.query(CampanhaPesquisaPrecos).filter_by(id=campanha_id).one()
        campanha.status, campanha.erro_mensagem = "executando", None
        db.commit()
        perfil = json.loads(campanha.objeto_canonico_json)
        consultas = db.query(ConsultaPesquisaPrecos).filter_by(campanha_id=campanha_id).order_by(
            ConsultaPesquisaPrecos.ordem).all()
        vistos = {o.processo_url for o in db.query(ObservacaoPreco).filter_by(campanha_id=campanha_id)}
        for consulta in consultas:
            if consulta.status == "completa": continue
            consulta.status = "executando"; db.commit()
            contratacao = db.query(Contratacao).filter_by(id=campanha.contratacao_id).one()
            pesquisa = Pesquisa(usuario_id=contratacao.usuario_id, contratacao_id=contratacao.id,
                termo_busca=consulta.termo, limite_processos=settings.MAX_PROCESSOS,
                status="em_andamento")
            db.add(pesquisa); db.flush(); consulta.pesquisa_id = pesquisa.id; db.commit()
            pasta = f"downloads/pesquisa_precos/{campanha_id}/{consulta.id}"
            resultado = executar_scraping(consulta.termo, min(10, settings.MAX_PROCESSOS),
                pasta_downloads_base=pasta)
            pesquisa.resultado_json = json.dumps(resultado, ensure_ascii=False)
            pesquisa.pasta_downloads = pasta
            pesquisa.status = "erro" if resultado.get("erro") else "completo"
            pesquisa.erro_mensagem = resultado.get("erro")
            processos = resultado.get("processos", [])
            consulta.processos_encontrados = len(processos)
            novos = 0
            for processo in processos:
                url = processo.get("url") or processo.get("numero_processo") or ""
                if not url: continue
                if url not in vistos: novos += 1; vistos.add(url)
                for item in processo.get("itens", []):
                    valor = _decimal(item.get("valor_de_referência"))
                    descricao = str(item.get("descricao") or "").strip()
                    if valor is None or valor <= 0 or not descricao: continue
                    chave = hashlib.sha256(f"{campanha_id}|{url}|{item.get('numero')}|{valor}".encode()).hexdigest()
                    if db.query(ObservacaoPreco).filter_by(chave_fonte=chave).first(): continue
                    aderencia = _aderencia(perfil, descricao)
                    docs = processo.get("documentos", [])
                    db.add(ObservacaoPreco(campanha_id=campanha_id, consulta_id=consulta.id,
                        chave_fonte=chave, processo_url=url,
                        numero_processo=processo.get("numero_processo"), comprador=processo.get("comprador"),
                        descricao_item=descricao, quantidade=str(item.get("quantidade") or "") or None,
                        unidade=str(item.get("unidade") or "") or None,
                        valor_unitario=str(valor), tipo_valor="referencia", aderencia_pct=aderencia,
                        comparavel=aderencia >= 40,
                        motivo_exclusao=None if aderencia >= 40 else "Baixa aderência ao objeto canônico",
                        documento_origem=docs[0].get("nome") if docs else None))
            consulta.processos_novos, consulta.status = novos, "completa"
            db.commit()
        observacoes = db.query(ObservacaoPreco).filter_by(campanha_id=campanha_id).all()
        consultas = db.query(ConsultaPesquisaPrecos).filter_by(campanha_id=campanha_id).all()
        campanha.resultado_json = json.dumps(_calcular_resultado(observacoes, consultas), ensure_ascii=False)
        campanha.status = "pronta_revisao"
        atualizadas = consolidar_campanha_no_plano(db, campanha)
        documentos = extrair_documentos_comparaveis(db, campanha)
        db.add(HistoricoContratacao(contratacao_id=campanha.contratacao_id,
            usuario_id=db.query(Contratacao).filter_by(id=campanha.contratacao_id).one().usuario_id,
            acao="Referências comparáveis incorporadas ao Plano",
            detalhe=(f"{atualizadas} informação(ões) atualizadas | "
                f"{documentos} documento(s) comparável(is) extraído(s)")))
        db.commit()
        pacote = montar_pacote_pesquisa_precos(db, campanha)
        _incorporar_pacote_na_bcc(db, campanha.contratacao_id, pacote)
        db.commit()
    except Exception as exc:
        db.rollback()
        campanha = db.query(CampanhaPesquisaPrecos).filter_by(id=campanha_id).first()
        if campanha:
            campanha.status, campanha.erro_mensagem = "erro", str(exc); db.commit()
        raise
    finally:
        db.close()


def iniciar_campanha(campanha_id: int) -> None:
    db = SessionLocal()
    try:
        campanha = db.query(CampanhaPesquisaPrecos).filter_by(id=campanha_id).one()
        job = criar_job(db, "pesquisa_precos", campanha.contratacao_id, referencia_id=campanha_id)
        job_id = job.id
    finally: db.close()
    retomar_campanha(job_id, campanha_id)


def retomar_campanha(job_id: int, campanha_id: int) -> None:
    def executar():
        def concluida():
            sessao = SessionLocal()
            try:
                return sessao.query(CampanhaPesquisaPrecos).filter_by(
                    id=campanha_id, status="pronta_revisao").first() is not None
            finally:
                sessao.close()
        executar_com_retry_idempotente(SessionLocal, job_id,
            lambda: _executar_campanha(campanha_id),
            concluida,
            etapa_execucao="pesquisando_mercado", etapa_sucesso="amostra_pronta",
            checkpoint=lambda: {"campanha_id": campanha_id})
    threading.Thread(target=executar, daemon=True).start()


def iniciar_pesquisa_automatica(contratacao_id: int) -> None:
    """Cria e dispara a pesquisa sem bloquear o início da investigação."""
    def preparar():
        db = SessionLocal()
        try:
            existente = (db.query(CampanhaPesquisaPrecos).filter_by(
                contratacao_id=contratacao_id).order_by(CampanhaPesquisaPrecos.id.desc()).first())
            if existente:
                if existente.status in {"planejada", "erro"}:
                    iniciar_campanha(existente.id)
                return
            contratacao = db.query(Contratacao).filter_by(id=contratacao_id).first()
            if contratacao is None:
                return
            campanha = criar_campanha(db, contratacao)
            iniciar_campanha(campanha.id)
        except Exception:
            logger.exception("Falha ao preparar pesquisa automática para contratacao_id=%s",
                contratacao_id)
            db.rollback()
        finally:
            db.close()
    threading.Thread(target=preparar, daemon=True).start()


def criar_campanha(db, contratacao: Contratacao, total_consultas: int = 5) -> CampanhaPesquisaPrecos:
    perfil = _perfil_objeto(contratacao)
    campanha = CampanhaPesquisaPrecos(contratacao_id=contratacao.id, status="planejada",
        objeto_canonico_json=json.dumps(perfil, ensure_ascii=False), max_consultas=10)
    db.add(campanha); db.flush()
    for ordem, termo in enumerate(_planejar_termos(perfil, total_consultas), 1):
        db.add(ConsultaPesquisaPrecos(campanha_id=campanha.id, ordem=ordem, termo=termo))
    db.commit(); db.refresh(campanha)
    return campanha


def expandir_campanha(db, campanha: CampanhaPesquisaPrecos, quantidade: int = 3) -> int:
    existentes = db.query(ConsultaPesquisaPrecos).filter_by(campanha_id=campanha.id).order_by(
        ConsultaPesquisaPrecos.ordem).all()
    disponiveis = max(0, campanha.max_consultas - len(existentes))
    quantidade = min(quantidade, disponiveis)
    if quantidade == 0: return 0
    perfil = json.loads(campanha.objeto_canonico_json)
    candidatos = _planejar_termos(perfil, campanha.max_consultas)
    usados = {c.termo.casefold() for c in existentes}
    novos = [t for t in candidatos if t.casefold() not in usados][:quantidade]
    for indice, termo in enumerate(novos, len(existentes) + 1):
        db.add(ConsultaPesquisaPrecos(campanha_id=campanha.id, ordem=indice, termo=termo))
    campanha.status, campanha.erro_mensagem = "planejada", None
    db.commit()
    return len(novos)


def montar_pacote_pesquisa_precos(db, campanha: CampanhaPesquisaPrecos) -> dict:
    observacoes = (db.query(ObservacaoPreco).filter_by(
        campanha_id=campanha.id, comparavel=True).order_by(ObservacaoPreco.id).all())
    return {"campanha_id": campanha.id, "status_revisao": campanha.status,
        "aprovada_em": campanha.aprovado_em.isoformat() if campanha.aprovado_em else None,
        "objeto": json.loads(campanha.objeto_canonico_json),
        "resultado": json.loads(campanha.resultado_json),
        "observacoes": [{"id": o.id, "processo_url": o.processo_url,
            "numero_processo": o.numero_processo, "comprador": o.comprador,
            "descricao_item": o.descricao_item, "valor_unitario": o.valor_unitario,
            "unidade": o.unidade, "aderencia_pct": o.aderencia_pct,
            "documento_origem": o.documento_origem,
            "status_validacao": o.status_validacao} for o in observacoes]}


def obter_pacote_disponivel(db, contratacao_id: int) -> dict | None:
    campanha = (db.query(CampanhaPesquisaPrecos).filter_by(
        contratacao_id=contratacao_id).filter(CampanhaPesquisaPrecos.status.in_(
            ["pronta_revisao", "aprovada"])).order_by(CampanhaPesquisaPrecos.id.desc()).first())
    return montar_pacote_pesquisa_precos(db, campanha) if campanha else None


def _incorporar_pacote_na_bcc(db, contratacao_id: int, pacote: dict) -> None:
    bcc = db.query(BaseConhecimento).filter_by(contratacao_id=contratacao_id).first()
    if bcc:
        dados = json.loads(bcc.dados_json)
        dados["pesquisa_precos"] = pacote
        bcc.dados_json = json.dumps(dados, ensure_ascii=False)
    ultimo = (db.query(SnapshotBCC).filter_by(contratacao_id=contratacao_id)
        .order_by(SnapshotBCC.versao.desc()).first())
    if ultimo:
        dados = json.loads(ultimo.dados_json)
        dados["pesquisa_precos"] = pacote
        serializado = json.dumps(dados, ensure_ascii=False, sort_keys=True)
        if hashlib.sha256(serializado.encode()).hexdigest() != ultimo.hash_conteudo:
            db.add(SnapshotBCC(contratacao_id=contratacao_id, versao=ultimo.versao + 1,
                dados_json=serializado,
                hash_conteudo=hashlib.sha256(serializado.encode()).hexdigest()))


def _registrar_evidencias_no_plano(db, campanha: CampanhaPesquisaPrecos, pacote: dict) -> None:
    plano = (db.query(PlanoInvestigacao).filter_by(contratacao_id=campanha.contratacao_id)
        .order_by(PlanoInvestigacao.versao.desc()).first())
    if plano is None:
        return
    infos = (db.query(PlanoInformacao, InformacaoCatalogo)
        .join(PlanoCardDecisao, PlanoCardDecisao.id == PlanoInformacao.plano_card_id)
        .join(InformacaoCatalogo, InformacaoCatalogo.id == PlanoInformacao.informacao_id)
        .filter(PlanoCardDecisao.plano_id == plano.id,
            InformacaoCatalogo.codigo.in_(["I015", "I016"])).all())
    descricoes = {
        "I015": "Pesquisa de preços com fontes rastreáveis e amostra revisada pelo usuário",
        "I016": "Metodologia estatística da pesquisa de preços, incluindo tratamento de outliers",
    }
    for info, catalogo in infos:
        anterior = (db.query(EvidenciaPlano).filter_by(
            plano_informacao_id=info.id, estado="vigente")
            .order_by(EvidenciaPlano.id.desc()).first())
        evidencia = criar_evidencia(db, info.id, tipo="pesquisa_precos",
            descricao=descricoes[catalogo.codigo], conteudo=pacote,
            origem=f"campanha_pesquisa_precos:{campanha.id}",
            metodo_obtencao="pesquisa_painel_compras_revisada", confianca="alta")
        evidencia.status_validacao = "confirmada"
        if anterior is not None and anterior.id != evidencia.id:
            substituir_evidencia(db, evidencia, anterior)
        else:
            evidencia.estado = "vigente"
        info.status = "coletada"
        info.estado_semantico = "confirmado"
        info.valor_json = json.dumps(pacote, ensure_ascii=False, sort_keys=True)
        info.origem = "pesquisa_precos"
        info.confianca = "alta"


def aprovar_campanha(db, campanha: CampanhaPesquisaPrecos, usuario_id: int) -> None:
    resultado = json.loads(campanha.resultado_json)
    if resultado.get("amostra_tratada", 0) < 3:
        raise ValueError("A pesquisa precisa de ao menos três preços comparáveis para aprovação")
    campanha.status, campanha.aprovado_por_usuario_id = "aprovada", usuario_id
    campanha.aprovado_em = datetime.now(timezone.utc).replace(tzinfo=None)
    for observacao in db.query(ObservacaoPreco).filter_by(campanha_id=campanha.id).all():
        observacao.status_validacao = "confirmada" if observacao.comparavel else "rejeitada"
    db.flush()
    pacote = montar_pacote_pesquisa_precos(db, campanha)
    _registrar_evidencias_no_plano(db, campanha, pacote)
    _incorporar_pacote_na_bcc(db, campanha.contratacao_id, pacote)
    db.add(HistoricoContratacao(contratacao_id=campanha.contratacao_id, usuario_id=usuario_id,
        acao="Pesquisa de preços aprovada", detalhe=f"Campanha #{campanha.id} | {resultado['amostra_tratada']} preços comparáveis"))
    db.commit()
