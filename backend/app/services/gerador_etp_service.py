import json
import logging
import os
from pathlib import Path

from app.config import settings
from app.database import SessionLocal
from app.models import Geracao, Pesquisa
from app.services.gemini_service import chamar_gemini_geracao
from app.services.gerador_documento import gerar_etp, gerar_tr
from app.services.pdf_extractor import extrair_textos_da_pasta

logger = logging.getLogger("gerador_etp_service")

_BACKEND_DIR = Path(__file__).parent.parent.parent
_PROMPTS_DIR = _BACKEND_DIR / "prompts"


def _carregar_prompt(tipo: str) -> str:
    nome = "prompt_etp.md" if tipo == "etp" else "prompt_tr.md"
    return (_PROMPTS_DIR / nome).read_text(encoding="utf-8")


def _montar_prompt(tipo: str, dados_processo: str, params: dict) -> str:
    template = _carregar_prompt(tipo)
    return template.replace("{dados_processo}", dados_processo).replace(
        "{params}", json.dumps(params, ensure_ascii=False, indent=2)
    )


def executar_geracao(geracao_id: int, pesquisa_id: int, params: dict):
    db = SessionLocal()
    try:
        pesquisa = db.query(Pesquisa).filter(Pesquisa.id == pesquisa_id).first()
        geracao = db.query(Geracao).filter(Geracao.id == geracao_id).first()
        if pesquisa is None or geracao is None:
            logger.error(f"Pesquisa {pesquisa_id} ou Geração {geracao_id} não encontrada.")
            return

        geracao.status = "em_andamento"
        db.commit()

        pesquisa_dict = json.loads(pesquisa.resultado_json) if pesquisa.resultado_json else {}

        textos_pdfs = {}
        if pesquisa.pasta_downloads and os.path.isdir(pesquisa.pasta_downloads):
            textos_pdfs = extrair_textos_da_pasta(pesquisa.pasta_downloads)
            logger.info(f"Extraídos textos de {len(textos_pdfs)} PDF(s).")

        dados_processo = json.dumps(
            {"processos": pesquisa_dict, "textos_pdfs": textos_pdfs},
            ensure_ascii=False,
        )

        tipo = geracao.tipo
        prompt = _montar_prompt(tipo, dados_processo, params)

        logger.info(f"Chamando Gemini para geração de {tipo.upper()} (geracao_id={geracao_id})")
        resultado = chamar_gemini_geracao(prompt)

        geracoes_dir = _BACKEND_DIR / settings.GERACOES_DIR / str(geracao_id)
        geracoes_dir.mkdir(parents=True, exist_ok=True)
        nome_arquivo = f"{tipo}_{geracao_id}.docx"
        destino = str(geracoes_dir / nome_arquivo)

        if tipo == "etp":
            gerar_etp(resultado, destino)
        else:
            gerar_tr(resultado, destino)

        logger.info(f"Documento gerado: {destino}")

        pendencias = resultado.get("pendencias", [])

        geracao.status = "completo"
        geracao.resultado_json = json.dumps(resultado, ensure_ascii=False)
        geracao.arquivo_gerado = destino
        geracao.modelo_gemini = settings.GEMINI_MODEL_GERACAO or settings.GEMINI_MODEL
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
