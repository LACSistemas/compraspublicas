import re
import unicodedata

USAR_CAMPO_TIPO = True

TERMOS_SUBSTRING = [
    "edital", "termo de referencia", "mapa de risco",
    "matriz de risco", "projeto basico",
]
TERMOS_TOKEN = ["tr", "etp"]  # curtos/ambíguos: exigem token isolado


def _normalizar(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto or "")
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", sem_acento.lower()).strip()


def documento_relevante(nome: str, tipo: str | None = None) -> bool:
    base = nome if not USAR_CAMPO_TIPO else f"{nome} {tipo or ''}"
    alvo = _normalizar(base)
    if any(t in alvo for t in TERMOS_SUBSTRING):
        return True
    return bool(set(alvo.split()) & set(TERMOS_TOKEN))


def filtrar_documentos(docs: list[dict]) -> tuple[list[dict], list[dict]]:
    mantidos, descartados = [], []
    for d in docs:
        (mantidos if documento_relevante(d.get("nome", ""), d.get("tipo")) else descartados).append(d)
    return mantidos, descartados
