from app.services.pdf_extractor import extrair_textos_da_pasta
import sys, json

if __name__ == "__main__":
    pasta = sys.argv[1] if len(sys.argv) > 1 else "downloads"
    resultados = extrair_textos_da_pasta(pasta)
    for nome, r in resultados.items():
        print(nome, "->", r["status"], "len=", len(r["texto"]))
