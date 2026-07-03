import json
import logging

from app.config import settings
from app.database import SessionLocal
from app.models import Analise, Pesquisa
from app.services.gemini_service import (
    carregar_prompt_base,
    chamar_gemini,
    montar_prompt_final,
    resumir_textos_pdfs,
)
from app.services.pdf_extractor import extrair_textos_da_pasta

logger = logging.getLogger("analise_service")


def executar_analise(analise_id: int, pesquisa_id: int):
    db = SessionLocal()
    try:
        pesquisa = db.query(Pesquisa).filter(Pesquisa.id == pesquisa_id).first()
        analise = db.query(Analise).filter(Analise.id == analise_id).first()
        if pesquisa is None or analise is None:
            logger.error(f"Pesquisa {pesquisa_id} ou Analise {analise_id} não encontrada.")
            return

        analise.status = "em_andamento"
        db.commit()

        pesquisa_dict = json.loads(pesquisa.resultado_json)

        textos_pdfs_brutos = extrair_textos_da_pasta(pesquisa.pasta_downloads)
        logger.info(f"Extraídos textos de {len(textos_pdfs_brutos)} PDF(s) em {pesquisa.pasta_downloads}.")

        textos_pdfs = resumir_textos_pdfs(textos_pdfs_brutos)

        prompt = montar_prompt_final(
            pesquisa_dict, textos_pdfs, pesquisa.quantidade_desejada, carregar_prompt_base()
        )
        resultado = chamar_gemini(prompt)

        analise.status = "completo"
        analise.resultado_json = json.dumps(resultado, ensure_ascii=False)
        analise.modelo_gemini = settings.GEMINI_MODEL
        db.commit()
    except Exception as e:
        logger.error(f"Erro ao executar análise {analise_id}: {e}", exc_info=True)
        db.rollback()
        analise = db.query(Analise).filter(Analise.id == analise_id).first()
        if analise is not None:
            analise.status = "erro"
            analise.erro_mensagem = str(e)
            db.commit()
    finally:
        db.close()
