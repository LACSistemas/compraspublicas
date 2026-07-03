import json
import logging
import os
import time

from .fonte_portal import FontePortal, _sanitize_filename, mapear_processo

logger = logging.getLogger("scraper")


def _slug_do_processo(url_referencia: str) -> str:
    return url_referencia.rstrip("/").split("/")[-1]


def executar_scraping(
    termo: str,
    limite: int = 10,
    headless: bool = True,
    pasta_downloads_base: str = "downloads",
) -> dict:
    os.makedirs(pasta_downloads_base, exist_ok=True)
    fonte = FontePortal()
    resultado = {"termo_busca": termo, "processos": [], "erro": None}

    try:
        lista = fonte.buscar(termo, limite)
        logger.info(f"Encontrados {len(lista)} processos para '{termo}'")

        for i, item in enumerate(lista, 1):
            cod = item.get("codigoLicitacao")
            logger.info(f"[{i}/{len(lista)}] Processo {cod}: {item.get('razaoSocial', '')}")

            try:
                detalhe = fonte.detalhar(item)
            except Exception as e:
                logger.error(f"  Falha ao detalhar {cod}: {e}")
                detalhe = {}

            try:
                itens_resp = fonte.listar_itens(cod)
            except Exception as e:
                logger.warning(f"  Falha ao listar itens de {cod}: {e}")
                itens_resp = {}

            try:
                documentos = fonte.listar_documentos(cod)
            except Exception as e:
                logger.warning(f"  Falha ao listar documentos de {cod}: {e}")
                documentos = []

            andamento_resp = fonte.listar_chat(cod)
            andamento = andamento_resp.get("frasesChat", []) if andamento_resp else []

            slug = _slug_do_processo(item.get("urlReferencia", str(cod)))
            pasta = os.path.join(pasta_downloads_base, slug)
            os.makedirs(pasta, exist_ok=True)

            arquivos_baixados = []
            for doc in documentos:
                if not doc.get("idArquivo"):
                    continue
                nome = doc.get("nome", f"documento_{doc['idArquivo'][:8]}")
                destino = os.path.join(pasta, _sanitize_filename(nome))
                try:
                    tamanho = fonte.baixar_documento(doc, destino)
                    if tamanho > 0:
                        arquivos_baixados.append({
                            "arquivo": nome,
                            "tamanho_bytes": tamanho,
                            "pasta": pasta,
                        })
                        logger.info(f"  Baixado: {nome} ({tamanho:,} bytes)")
                except Exception as e:
                    logger.warning(f"  Falha ao baixar '{nome}': {e}")

            processo = mapear_processo(item, detalhe, itens_resp, documentos, arquivos_baixados, andamento)
            resultado["processos"].append(processo)

            time.sleep(0.3)

    except Exception as e:
        logger.error(f"Erro fatal: {e}", exc_info=True)
        resultado["erro"] = str(e)

    return resultado


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    resultado = executar_scraping("cafe", limite=2, headless=True)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
