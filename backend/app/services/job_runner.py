import threading

from app.services.analise_service import executar_analise
from app.services.scraper_service import executar_e_persistir


def iniciar_job_scraping(pesquisa_id: int, termo: str, limite: int):
    thread = threading.Thread(
        target=executar_e_persistir, args=(pesquisa_id, termo, limite), daemon=True
    )
    thread.start()


def iniciar_job_analise(analise_id: int, pesquisa_id: int):
    thread = threading.Thread(
        target=executar_analise, args=(analise_id, pesquisa_id), daemon=True
    )
    thread.start()
