import json
import logging
import os
from pathlib import Path

from app.config import settings
from app.database import SessionLocal
from app.models import (
    BaseConhecimento,
    ConhecimentoCard,
    Geracao,
    Pesquisa,
    PlanoCardDecisao,
    PlanoInvestigacao,
    SnapshotBCC,
)
from app.services.gemini_service import chamar_gemini_geracao, salvar_uso_tokens
from app.services.gerador_documento import gerar_documento_generico, gerar_etp, gerar_tr
from app.services.pdf_extractor import extrair_textos_da_pasta
from app.services.governanca_ia_service import exigir_orcamento_disponivel

logger = logging.getLogger("gerador_etp_service")

_BACKEND_DIR = Path(__file__).parent.parent.parent
_PROMPTS_DIR = _BACKEND_DIR / "prompts"


def _carregar_prompt(tipo: str) -> str:
    nomes = {"dfd": "prompt_dfd.md", "etp": "prompt_etp.md",
        "mapa_riscos": "prompt_mapa_riscos.md", "tr": "prompt_tr.md"}
    nome = nomes[tipo]
    return (_PROMPTS_DIR / nome).read_text(encoding="utf-8")


def _montar_prompt(tipo: str, dados_processo: str, params: dict) -> str:
    template = _carregar_prompt(tipo)
    prompt = template.replace("{dados_processo}", dados_processo).replace(
        "{params}", json.dumps(params, ensure_ascii=False, indent=2)
    )
    return prompt + ("\n\nInclua no JSON `rastreabilidade_secoes`, mapeando cada seção aos códigos "
        "D001–D014 que a sustentam. Não preencha lacunas críticas com conteúdo plausível; "
        "registre-as em `pendencias`.")


def _montar_dados_processo(db, pesquisa: Pesquisa, textos_pdfs: dict) -> str:
    pesquisa_dict = json.loads(pesquisa.resultado_json) if pesquisa.resultado_json else {}
    if pesquisa.contratacao_id is None:
        return json.dumps(
            {"processos": pesquisa_dict, "textos_pdfs": textos_pdfs},
            ensure_ascii=False,
        )

    plano = (db.query(PlanoInvestigacao)
        .filter_by(contratacao_id=pesquisa.contratacao_id)
        .order_by(PlanoInvestigacao.versao.desc()).first())
    snapshot = (db.query(SnapshotBCC)
        .filter_by(contratacao_id=pesquisa.contratacao_id)
        .order_by(SnapshotBCC.versao.desc()).first())
    if plano is None or snapshot is None:
        bcc = db.query(BaseConhecimento).filter_by(
            contratacao_id=pesquisa.contratacao_id).first()
        if bcc is None:
            raise ValueError("Consolide o BCC antes de gerar documentos")
        return json.dumps({
            "fonte_canonica": "bcc_legada_consolidada",
            "aviso_governanca": (
                "Contratação criada antes do Plano de Investigação; conteúdo sujeito "
                "a revisão humana reforçada."
            ),
            "bcc": json.loads(bcc.dados_json),
            "pesquisa_de_apoio": pesquisa_dict,
            "textos_pdfs_de_apoio": textos_pdfs,
        }, ensure_ascii=False)

    itens = db.query(PlanoCardDecisao).filter_by(
        plano_id=plano.id, aplicavel=True).all()
    conhecimentos = []
    for item in itens:
        ultimo = (db.query(ConhecimentoCard).filter_by(plano_card_id=item.id)
            .order_by(ConhecimentoCard.versao.desc()).first())
        if ultimo is None or ultimo.status != "aprovado":
            raise ValueError("Todos os Cards aplicáveis precisam de conhecimento aprovado")
        conhecimentos.append(ultimo)

    snapshot_dict = json.loads(snapshot.dados_json)
    decisoes = snapshot_dict.get("decisoes", [])
    if len(decisoes) != len(itens) or any(d.get("status") != "aprovado" for d in decisoes):
        raise ValueError("O snapshot BCC mais recente não contém todos os Cards aprovados")

    return json.dumps({
        "fonte_canonica": "snapshot_bcc_aprovado",
        "snapshot_bcc": {"versao": snapshot.versao, "hash": snapshot.hash_conteudo,
            "dados": snapshot_dict},
        "pesquisa_de_apoio": pesquisa_dict,
        "textos_pdfs_de_apoio": textos_pdfs,
    }, ensure_ascii=False)


def executar_geracao(geracao_id: int, pesquisa_id: int, params: dict, usuario_id: int):
    db = SessionLocal()
    try:
        pesquisa = db.query(Pesquisa).filter(Pesquisa.id == pesquisa_id).first()
        geracao = db.query(Geracao).filter(Geracao.id == geracao_id).first()
        if pesquisa is None or geracao is None:
            logger.error(f"Pesquisa {pesquisa_id} ou Geração {geracao_id} não encontrada.")
            return

        geracao.status = "em_andamento"
        db.commit()

        if pesquisa.contratacao_id is not None:
            exigir_orcamento_disponivel(db, pesquisa.contratacao_id)

        textos_pdfs = {}
        if pesquisa.pasta_downloads and os.path.isdir(pesquisa.pasta_downloads):
            textos_pdfs = extrair_textos_da_pasta(pesquisa.pasta_downloads)
            logger.info(f"Extraídos textos de {len(textos_pdfs)} PDF(s).")

        dados_processo = _montar_dados_processo(db, pesquisa, textos_pdfs)

        tipo = geracao.tipo
        prompt = _montar_prompt(tipo, dados_processo, params)

        logger.info(f"Chamando Gemini para geração de {tipo.upper()} (geracao_id={geracao_id})")
        resultado, token_info = chamar_gemini_geracao(prompt)

        geracoes_dir = _BACKEND_DIR / settings.GERACOES_DIR / str(geracao_id)
        geracoes_dir.mkdir(parents=True, exist_ok=True)
        nome_arquivo = f"{tipo}_{geracao_id}.docx"
        destino = str(geracoes_dir / nome_arquivo)

        if tipo == "etp":
            gerar_etp(resultado, destino)
        elif tipo == "tr":
            gerar_tr(resultado, destino)
        else:
            titulo = "DOCUMENTO DE FORMALIZAÇÃO DA DEMANDA" if tipo == "dfd" else "MAPA DE RISCOS"
            gerar_documento_generico(resultado, destino, titulo)

        logger.info(f"Documento gerado: {destino}")

        salvar_uso_tokens(db, usuario_id, tipo, token_info, referencia_id=geracao_id)

        geracao.status = "completo"
        geracao.resultado_json = json.dumps(resultado, ensure_ascii=False)
        geracao.arquivo_gerado = destino
        geracao.modelo_gemini = token_info.modelo
        db.commit()

    except Exception as e:
        logger.error(f"Erro ao executar geração {geracao_id}: {e}", exc_info=True)
        db.rollback()
        geracao = db.query(Geracao).filter(Geracao.id == geracao_id).first()
        if geracao is not None:
            geracao.status = "erro"
            geracao.erro_mensagem = str(e)
            db.commit()
    finally:
        db.close()
