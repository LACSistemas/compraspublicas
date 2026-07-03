from app.scraper.scraping_core import executar_scraping
import json

if __name__ == "__main__":
    resultado = executar_scraping(termo="cafe", limite=2, headless=True, pasta_downloads_base="downloads/teste_isolado")
    print(json.dumps(resultado, ensure_ascii=False, indent=2)[:3000])
    print("Erro:", resultado.get("erro"))
    print("Total de processos:", len(resultado["processos"]))
