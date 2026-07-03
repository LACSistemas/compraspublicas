import os

import pdfplumber
from pypdf import PdfReader

LIMITE_MINIMO_CHARS = 50


def _extrair_com_pypdf(caminho: str) -> str:
    reader = PdfReader(caminho)
    return "".join(page.extract_text() or "" for page in reader.pages)


def _extrair_com_pdfplumber(caminho: str) -> str:
    with pdfplumber.open(caminho) as pdf:
        return "".join(page.extract_text() or "" for page in pdf.pages)


def _extrair_com_ocr(caminho: str) -> str:
    from pdf2image import convert_from_path
    import pytesseract
    paginas = convert_from_path(caminho, dpi=200)
    return "\n".join(pytesseract.image_to_string(pag, lang="por") for pag in paginas)


def extrair_texto_pdf(caminho_arquivo: str) -> dict:
    texto_pypdf = None
    erro_pypdf = None
    try:
        texto_pypdf = _extrair_com_pypdf(caminho_arquivo)
    except Exception as e:
        erro_pypdf = str(e)

    if texto_pypdf is not None and len(texto_pypdf.strip()) >= LIMITE_MINIMO_CHARS:
        return {"texto": texto_pypdf, "status": "ok", "metodo": "pypdf", "erro": None}

    texto_pdfplumber = None
    erro_pdfplumber = None
    try:
        texto_pdfplumber = _extrair_com_pdfplumber(caminho_arquivo)
    except Exception as e:
        erro_pdfplumber = str(e)

    if texto_pdfplumber is not None and len(texto_pdfplumber.strip()) >= LIMITE_MINIMO_CHARS:
        return {"texto": texto_pdfplumber, "status": "ok", "metodo": "pdfplumber", "erro": None}

    # Nível 3: OCR via Tesseract (PDFs escaneados sem texto extraível)
    erro_ocr = None
    try:
        texto_ocr = _extrair_com_ocr(caminho_arquivo)
        if len(texto_ocr.strip()) >= LIMITE_MINIMO_CHARS:
            return {"texto": texto_ocr, "status": "ok_ocr", "metodo": "tesseract", "erro": None}
        return {"texto": texto_ocr, "status": "vazio_apos_ocr", "metodo": "tesseract", "erro": None}
    except Exception as e_ocr:
        erro_ocr = str(e_ocr)

    if erro_pypdf and erro_pdfplumber:
        return {
            "texto": "",
            "status": "erro",
            "metodo": None,
            "erro": f"pypdf: {erro_pypdf}; pdfplumber: {erro_pdfplumber}; ocr: {erro_ocr}",
        }

    texto_final = texto_pdfplumber or texto_pypdf or ""
    metodo_final = "pdfplumber" if texto_pdfplumber else ("pypdf" if texto_pypdf else None)
    return {
        "texto": texto_final,
        "status": "vazio_possivelmente_escaneado",
        "metodo": metodo_final,
        "erro": None,
    }


def extrair_textos_da_pasta(pasta: str) -> dict:
    resultados = {}
    for raiz, _dirs, arquivos in os.walk(pasta):
        for nome in arquivos:
            if nome.lower().endswith(".pdf"):
                caminho_completo = os.path.join(raiz, nome)
                nome_relativo = os.path.relpath(caminho_completo, pasta)
                resultados[nome_relativo] = extrair_texto_pdf(caminho_completo)
    return resultados
