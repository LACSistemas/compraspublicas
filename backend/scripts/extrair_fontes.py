"""
Extrai Lei 14.133 (docx) e Decreto 5352-R (pdf) para markdown em fontes_verdade/.
Rodar uma vez; se as fontes mudarem, rodar novamente para recriar o cache Gemini.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent  # raiz do projeto
BACKEND = Path(__file__).parent.parent
DEST = BACKEND / "fontes_verdade"
DEST.mkdir(exist_ok=True)

LEI_DOCX = ROOT / "L14133.docx"
DECRETO_PDF = ROOT / "Decreto Estadual 5352-R-2023 - NLLC - Pregão, Concorrência, Contratação Direta, Bens de luxo e Designação de Agentes - Consolidado até o 5766.pdf"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _limpar(texto: str) -> str:
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def extrair_lei_docx(src: Path, dest: Path) -> str:
    from docx import Document
    doc = Document(str(src))
    linhas = []
    for p in doc.paragraphs:
        t = p.text.strip()
        if t:
            linhas.append(t)
    texto = _limpar("\n".join(linhas))
    sha = sha256_file(src)
    conteudo = (
        f"---\nnorma: Lei nº 14.133/2021\n"
        f"arquivo_fonte: {src.name}\n"
        f"sha256: {sha}\n---\n\n"
        + texto
    )
    dest.write_text(conteudo, encoding="utf-8")
    print(f"[OK] {dest.name} — {len(texto):,} chars")
    return sha


def extrair_decreto_pdf(src: Path, dest: Path) -> str:
    import pdfplumber
    paginas = []
    with pdfplumber.open(str(src)) as pdf:
        for pg in pdf.pages:
            t = pg.extract_text() or ""
            if t.strip():
                paginas.append(t)
    texto = _limpar("\n".join(paginas))
    sha = sha256_file(src)
    conteudo = (
        f"---\nnorma: Decreto Estadual 5352-R/2023 (consolidado até 5766-R)\n"
        f"arquivo_fonte: {src.name}\n"
        f"sha256: {sha}\n---\n\n"
        + texto
    )
    dest.write_text(conteudo, encoding="utf-8")
    print(f"[OK] {dest.name} — {len(texto):,} chars")
    return sha


def main():
    erros = []

    if not LEI_DOCX.exists():
        erros.append(f"Arquivo não encontrado: {LEI_DOCX}")
    if not DECRETO_PDF.exists():
        erros.append(f"Arquivo não encontrado: {DECRETO_PDF}")
    if erros:
        for e in erros:
            print(f"[ERRO] {e}", file=sys.stderr)
        sys.exit(1)

    sha_lei = extrair_lei_docx(LEI_DOCX, DEST / "lei_14133.md")
    sha_dec = extrair_decreto_pdf(DECRETO_PDF, DEST / "decreto_5352R.md")

    hashes = {"lei_14133": sha_lei, "decreto_5352R": sha_dec}
    (DEST / "hashes.json").write_text(json.dumps(hashes, indent=2), encoding="utf-8")
    print(f"[OK] hashes.json gravado")
    print("Extração concluída.")


if __name__ == "__main__":
    main()
