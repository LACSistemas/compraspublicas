import json
import logging

from app.database import SessionLocal
from app.models import Pesquisa
from app.scraper.scraping_core import executar_scraping

logger = logging.getLogger("scraper_service")


def executar_e_persistir(pesquisa_id: int, termo: str, limite: int):
    db = SessionLocal()
    try:
        pesquisa = db.query(Pesquisa).filter(Pesquisa.id == pesquisa_id).first()
        if pesquisa is None:
            logger.error(f"Pesquisa {pesquisa_id} não encontrada.")
            return

        pesquisa.status = "em_andamento"
        db.commit()

        pasta_downloads = f"downloads/{pesquisa_id}"
        resultado = executar_scraping(
            termo, limite, headless=True, pasta_downloads_base=pasta_downloads
        )

        if resultado["erro"] is None:
            pesquisa.status = "completo"
        else:
            pesquisa.status = "erro"
            pesquisa.erro_mensagem = resultado["erro"]

        pesquisa.resultado_json = json.dumps(resultado, ensure_ascii=False)
        pesquisa.pasta_downloads = pasta_downloads
        db.commit()
    except Exception as e:
        logger.error(f"Erro inesperado ao processar pesquisa {pesquisa_id}: {e}", exc_info=True)
        db.rollback()
        pesquisa = db.query(Pesquisa).filter(Pesquisa.id == pesquisa_id).first()
        if pesquisa is not None:
            pesquisa.status = "erro"
            pesquisa.erro_mensagem = str(e)
            db.commit()
    finally:
        db.close()
