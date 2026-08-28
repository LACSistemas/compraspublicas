import json
import logging
import os
import threading

from app.database import SessionLocal
from app.models import BaseConhecimento, Contratacao, HistoricoContratacao, PerguntaContratacao
from app.services.gemini_service import chamar_gemini, salvar_uso_tokens
from app.services.pesquisa_precos_service import obter_pacote_disponivel

logger = logging.getLogger("bcc_service")

_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "prompt_bcc.md")


def _montar_qa(perguntas: list) -> str:
    linhas = []
    for p in perguntas:
        alts = json.loads(p.alternativas_json)
        alt_map = {a["letra"]: a["texto"] for a in alts}
        resp_letra = p.resposta_escolhida or "?"
        resp_texto = alt_map.get(resp_letra, "não respondida")
        linhas.append(f"{p.ordem}. {p.texto}")
        linhas.append(f"Resposta: ({resp_letra}) {resp_texto}\n")
    return "\n".join(linhas)


def _job_processar_bcc(contratacao_id: int):
    db = SessionLocal()
    try:
        contratacao = db.query(Contratacao).filter(Contratacao.id == contratacao_id).first()
        if not contratacao:
            return

        perguntas = (
            db.query(PerguntaContratacao)
            .filter(PerguntaContratacao.contratacao_id == contratacao_id)
            .order_by(PerguntaContratacao.ordem)
            .all()
        )

        with open(_PROMPT_PATH, encoding="utf-8") as f:
            template = f.read()

        prompt = template.format(
            objeto=contratacao.objeto,
            orgao=contratacao.orgao_unidade,
            tipo=contratacao.tipo_contratacao or "não especificado",
            equipe=contratacao.equipe_responsavel or "não informada",
            processo=contratacao.numero_processo or "não informado",
            contexto=contratacao.contexto_inicial or "não informado",
            perguntas_e_respostas=_montar_qa(perguntas),
        )

        pesquisa_precos = obter_pacote_disponivel(db, contratacao_id)
        if pesquisa_precos:
            prompt += ("\n\nPESQUISA DE MERCADO E PREÇOS RASTREÁVEL:\n" +
                json.dumps(pesquisa_precos, ensure_ascii=False) +
                "\nUse as referências apenas como comparáveis externos. Não trate requisitos, "
                "quantidades ou condições de outros órgãos como fatos desta contratação.")

        dados, token_info = chamar_gemini(prompt)
        if pesquisa_precos:
            dados["pesquisa_precos"] = pesquisa_precos

        metricas = dados.get("metricas", {})
        progresso = metricas.get("progresso_pct", 0)
        maturidade = metricas.get("nivel_maturidade", "Insuficiente")

        bcc = db.query(BaseConhecimento).filter_by(contratacao_id=contratacao_id).first()
        if bcc is None:
            bcc = BaseConhecimento(contratacao_id=contratacao_id)
            db.add(bcc)
        bcc.dados_json = json.dumps(dados, ensure_ascii=False)
        bcc.progresso_pct = progresso
        bcc.nivel_maturidade = maturidade
        bcc.modelo_gemini = token_info.modelo

        salvar_uso_tokens(db, contratacao.usuario_id, "bcc_contratacao", token_info, contratacao_id)

        db.add(HistoricoContratacao(
            contratacao_id=contratacao_id,
            usuario_id=contratacao.usuario_id,
            acao="IA construiu a Base de Conhecimento da Contratação",
            detalhe=(
                f"Progresso: {progresso}% | Maturidade: {maturidade} | "
                f"Modelo: {token_info.modelo} | Tokens: {token_info.total}"
            ),
        ))

        contratacao.status = "bcc_ativa"
        db.commit()
        logger.info("BCC processada com sucesso para contratacao_id=%s", contratacao_id)

    except Exception as exc:
        logger.exception("Erro ao processar BCC para contratacao_id=%s", contratacao_id)
        db.rollback()
        try:
            c = db.query(Contratacao).filter(Contratacao.id == contratacao_id).first()
            if c:
                c.status = "erro"
                c.erro_mensagem = str(exc)
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


def iniciar_processamento_bcc(contratacao_id: int):
    threading.Thread(
        target=_job_processar_bcc, args=(contratacao_id,), daemon=True
    ).start()
