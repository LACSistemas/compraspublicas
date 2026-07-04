import json
import logging
import re

import requests

from .fonte_base import FonteDados

logger = logging.getLogger("scraper")

_BASE = "https://compras.api.portaldecompraspublicas.com.br"
_ARQUIVOS_BASE = "https://arquivos.portaldecompraspublicas.com.br"

_HEADERS = {
    "Accept": "application/json, */*",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.portaldecompraspublicas.com.br/",
}


def _sanitize_filename(nome: str) -> str:
    nome = re.sub(r'[\\/:*?"<>|]', "_", nome)
    return nome[:200].strip()


class FontePortal(FonteDados):
    def __init__(self):
        self._s = requests.Session()
        self._s.headers.update(_HEADERS)

    def buscar(self, termo: str, limite: int) -> list:
        resultados = []
        vistos: set = set()
        pagina = 1
        limite_pagina = min(limite, 12)

        while len(resultados) < limite:
            r = self._s.get(
                f"{_BASE}/v2/licitacao/processos",
                params={"objeto": termo, "pagina": pagina, "limitePagina": limite_pagina},
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            items = data.get("result", []) if isinstance(data, dict) else data
            if not items:
                break
            for item in items:
                cod = item.get("codigoLicitacao")
                if cod and cod not in vistos and len(resultados) < limite:
                    vistos.add(cod)
                    resultados.append(item)
            if len(items) < limite_pagina:
                break
            pagina += 1

        return resultados

    def detalhar(self, lista_item: dict) -> dict:
        url_ref = lista_item.get("urlReferencia", "")
        r = self._s.get(f"{_BASE}/v2/licitacao{url_ref}", timeout=30)
        r.raise_for_status()
        return r.json()

    def listar_itens(self, codigo_licitacao: int) -> dict:
        r = self._s.get(
            f"{_BASE}/v2/licitacao/{codigo_licitacao}/itens",
            params={"pagina": 1},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def listar_documentos(self, codigo_licitacao: int) -> list:
        r = self._s.get(
            f"{_BASE}/v2/licitacao/{codigo_licitacao}/documentos/processo",
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []

    def baixar_documento(self, doc: dict, destino: str) -> int:
        url = doc.get("url")
        if not url:
            return 0

        r = self._s.get(url, headers={"Accept": "*/*"}, stream=True, timeout=60)
        r.raise_for_status()

        nome = doc.get("nome", "")
        eh_pdf = nome.lower().endswith(".pdf")
        validado = False
        tamanho = 0

        with open(destino, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if not validado and eh_pdf and chunk:
                    if not chunk.startswith(b"%PDF"):
                        raise ValueError(f"Conteúdo inválido: magic={chunk[:8]!r}")
                    validado = True
                f.write(chunk)
                tamanho += len(chunk)

        return tamanho

    def listar_chat(self, codigo_licitacao: int) -> dict:
        try:
            r = self._s.get(
                f"{_BASE}/v1/licitacao/{codigo_licitacao}/chat",
                timeout=15,
            )
            r.raise_for_status()
            return r.json()
        except Exception:
            return {"frasesChat": []}


def mapear_processo(
    lista_item: dict,
    detalhe: dict,
    itens_resp: dict,
    documentos: list,
    arquivos_baixados: list,
    andamento: list = None,
    documentos_descartados: list = None,
) -> dict:
    url_ref = lista_item.get("urlReferencia", "")
    url_publica = f"https://www.portaldecompraspublicas.com.br/processos{url_ref}"

    tipo_lic = lista_item.get("tipoLicitacao") or {}
    modalidade = tipo_lic.get("modalidadeLicitacao") or detalhe.get("tipoPregao", "")

    leg = (
        detalhe.get("legislacaoAplicavel")
        or ("Lei nº 14.133/2021" if detalhe.get("lei14133") else "")
        or ("Lei nº 8.666/1993" if detalhe.get("lei8666") else "")
    )

    datas: dict = {}
    if detalhe.get("dataHoraPublicacao"):
        datas["Data de Publicação"] = detalhe["dataHoraPublicacao"]
    if detalhe.get("dataHoraLimiteImpugnacoes"):
        datas["Limite p/ Impugnações"] = detalhe["dataHoraLimiteImpugnacoes"]
    if detalhe.get("dataHoraInicioPropostas"):
        datas["Abertura das Propostas"] = detalhe["dataHoraInicioPropostas"]
    if detalhe.get("dataHoraFinalPropostas"):
        datas["Limite p/ Recebimento das Propostas"] = detalhe["dataHoraFinalPropostas"]

    informacoes: dict = {}
    if tipo_lic.get("tipoLicitacao"):
        informacoes["Tipo"] = tipo_lic["tipoLicitacao"]
    if detalhe.get("nomePregoeiro"):
        informacoes["Pregoeiro"] = detalhe["nomePregoeiro"]
    if detalhe.get("nomeAutoridadeCompetente"):
        informacoes["Autoridade Competente"] = detalhe["nomeAutoridadeCompetente"]
    if leg:
        informacoes["Legislação Aplicável"] = leg
    if detalhe.get("tipoJulgamento"):
        informacoes["Critério de Julgamento"] = detalhe["tipoJulgamento"]
    if detalhe.get("origemRecurso"):
        informacoes["Origem do Recurso"] = detalhe["origemRecurso"]

    itens_raw = (itens_resp.get("itens") or {}).get("result") or [] if itens_resp else []
    itens = [
        {
            "numero": it.get("codigo"),
            "descricao": it.get("descricao"),
            "quantidade": it.get("quantidade"),
            "valor_de_referência": it.get("valorReferencia"),
            "unidade": it.get("unidade"),
        }
        for it in itens_raw
    ]

    docs = [
        {
            "nome": d.get("nome"),
            "tipo": d.get("tipo"),
            "data": d.get("dataHora"),
        }
        for d in documentos
        if d.get("nome")
    ]

    situacao = ""
    status_obj = lista_item.get("status")
    if isinstance(status_obj, dict):
        situacao = status_obj.get("descricao", "")
    elif isinstance(status_obj, str):
        situacao = status_obj

    return {
        "url": url_publica,
        "numero_processo": detalhe.get("numeroProcesso") or lista_item.get("numero", ""),
        "situacao": situacao,
        "comprador": lista_item.get("razaoSocial") or lista_item.get("nomeUnidade", ""),
        "modalidade": modalidade,
        "objeto": detalhe.get("resumo") or lista_item.get("resumo", ""),
        "informacoes": informacoes,
        "datas": datas,
        "documentos": docs,
        "itens": itens,
        "andamento": andamento or [],
        "arquivos_baixados": arquivos_baixados,
        "documentos_descartados": [d.get("nome", "") for d in (documentos_descartados or [])],
        "conteudo_bruto": json.dumps(detalhe, ensure_ascii=False)[:50000],
    }
