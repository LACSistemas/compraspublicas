import json
import logging
import os
import re
from pathlib import Path

from google import genai
from google.genai import types

from app.config import settings

logger = logging.getLogger("gemini_service")

LIMITE_TOKENS_INPUT = 1_000_000
LIMITE_TOKENS_OUTPUT = 300_000
LIMITE_RESUMO_CHARS = 6000
LIMITE_TOKENS_OUTPUT_RESUMO = 2000

PROMPT_RESUMO = """Você é um assistente de extração de informações de documentos de licitação pública \
brasileira. Abaixo está o texto extraído do documento "{nome_arquivo}".

Resuma de forma objetiva e estruturada, preservando TODOS os números, datas, valores monetários, \
prazos e exigências relevantes para auditoria de compras públicas (tipo de documento, objeto, valores, \
datas-chave, exigências de habilitação, especificações técnicas, penalidades, cláusulas importantes e \
qualquer inconsistência notável). Não invente informação que não esteja no texto. Seja conciso — corte \
apenas redundância e formatação, nunca dados objetivos.

Texto original:

{texto}
"""

_PROMPT_MD_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "prompt.md")


def carregar_prompt_base() -> str:
    with open(_PROMPT_MD_PATH, "r", encoding="utf-8") as f:
        return f.read()


def montar_prompt_final(
    pesquisa_dict: dict,
    textos_pdfs: dict,
    quantidade_desejada: str | None,
    prompt_base: str,
) -> str:
    partes = [
        prompt_base,
        "\n\n---\n\n## DADOS DA PESQUISA (scraping)\n",
        json.dumps(pesquisa_dict, ensure_ascii=False),
        "\n\n## TEXTOS EXTRAÍDOS DOS DOCUMENTOS (PDFs)\n",
        json.dumps(textos_pdfs, ensure_ascii=False),
    ]
    if quantidade_desejada:
        partes.append(f"\n\n## QUANTIDADE DESEJADA PELO USUÁRIO\n{quantidade_desejada}")
    return "".join(partes)


def _extrair_json_da_resposta(texto: str) -> dict:
    texto = texto.strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        # "Extra data" — modelo retornou JSON válido seguido de conteúdo extra
        try:
            obj, _ = json.JSONDecoder().raw_decode(texto)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
        # Bloco ```json ... ```
        match = re.search(r"```json\s*(.*?)\s*```", texto, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise


def _client() -> genai.Client:
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def contar_tokens_input(prompt: str) -> int:
    client = _client()
    resposta = client.models.count_tokens(model=settings.GEMINI_MODEL, contents=prompt)
    return resposta.total_tokens


def chamar_gemini(prompt: str) -> dict:
    client = _client()

    tokens_input = contar_tokens_input(prompt)
    logger.info(f"Tokens de input (estimativa via count_tokens): {tokens_input:,}")
    if tokens_input > LIMITE_TOKENS_INPUT:
        raise ValueError(
            f"Prompt tem {tokens_input:,} tokens de input, acima do limite de "
            f"{LIMITE_TOKENS_INPUT:,}. Chamada à API abortada antes de gastar tokens."
        )

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            max_output_tokens=LIMITE_TOKENS_OUTPUT,
        ),
    )

    uso = response.usage_metadata
    if uso is not None:
        logger.info(
            f"Tokens reais da chamada — input: {uso.prompt_token_count:,} | "
            f"output: {uso.candidates_token_count:,} | total: {uso.total_token_count:,}"
        )

    if response.text is None:
        raise ValueError(
            f"Resposta do Gemini sem texto (finish_reason="
            f"{response.candidates[0].finish_reason if response.candidates else None}). "
            f"Provavelmente cortada por max_output_tokens ou bloqueada por safety."
        )

    return _extrair_json_da_resposta(response.text)


def resumir_documento(nome_arquivo: str, texto: str) -> str:
    client = _client()
    prompt = PROMPT_RESUMO.format(nome_arquivo=nome_arquivo, texto=texto)

    tokens_input = contar_tokens_input(prompt)
    logger.info(f"[resumo] '{nome_arquivo}' — tokens de input: {tokens_input:,}")
    if tokens_input > LIMITE_TOKENS_INPUT:
        raise ValueError(
            f"Documento '{nome_arquivo}' tem {tokens_input:,} tokens de input, acima do limite de "
            f"{LIMITE_TOKENS_INPUT:,}. Resumo abortado antes de gastar tokens."
        )

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(max_output_tokens=LIMITE_TOKENS_OUTPUT_RESUMO),
    )

    uso = response.usage_metadata
    if uso is not None:
        logger.info(
            f"[resumo] '{nome_arquivo}' — tokens reais: input {uso.prompt_token_count:,} | "
            f"output {uso.candidates_token_count:,} | total {uso.total_token_count:,}"
        )

    if response.text is None:
        logger.warning(f"[resumo] '{nome_arquivo}' sem texto na resposta, mantendo original truncado.")
        return texto[:LIMITE_RESUMO_CHARS]

    return response.text


_BACKEND_DIR = Path(__file__).parent.parent.parent
_FONTES_DIR = _BACKEND_DIR / settings.FONTES_VERDADE_DIR
_CACHE_STATE_FILE = _FONTES_DIR / "cache_state.json"


def obter_textos_fontes_verdade() -> str:
    lei = (_FONTES_DIR / "lei_14133.md").read_text(encoding="utf-8")
    decreto = (_FONTES_DIR / "decreto_5352R.md").read_text(encoding="utf-8")
    return f"=== Lei 14.133/2021 ===\n\n{lei}\n\n=== Decreto 5352-R/2023 ===\n\n{decreto}"


def _hashes_atuais() -> dict:
    hashes_file = _FONTES_DIR / "hashes.json"
    if hashes_file.exists():
        return json.loads(hashes_file.read_text(encoding="utf-8"))
    return {}


def criar_ou_recuperar_cache() -> str | None:
    """
    Cria ou reutiliza cache Gemini com fontes de verdade.
    Retorna o cache name se bem-sucedido, None em caso de falha.
    """
    client = _client()
    hashes = _hashes_atuais()

    if _CACHE_STATE_FILE.exists():
        estado = json.loads(_CACHE_STATE_FILE.read_text(encoding="utf-8"))
        if estado.get("hashes") == hashes and estado.get("cache_name"):
            cache_name = estado["cache_name"]
            try:
                client.caches.get(name=cache_name)
                logger.info(f"Cache Gemini reutilizado: {cache_name}")
                return cache_name
            except Exception:
                logger.info("Cache Gemini expirado ou inválido, recriando.")

    try:
        textos = obter_textos_fontes_verdade()
        cache = client.caches.create(
            model=(settings.GEMINI_MODEL_GERACAO or settings.GEMINI_MODEL),
            config=types.CreateCachedContentConfig(
                contents=[textos],
                ttl="3600s",
            ),
        )
        cache_name = cache.name
        _CACHE_STATE_FILE.write_text(
            json.dumps({"cache_name": cache_name, "hashes": hashes}, indent=2),
            encoding="utf-8",
        )
        logger.info(f"Novo cache Gemini criado: {cache_name}")
        return cache_name
    except Exception as e:
        logger.warning(f"Falha ao criar cache Gemini: {e}. Usará fontes inline.")
        return None


def chamar_gemini_geracao(prompt_geracao: str) -> dict:
    """
    Chama Gemini para geração de ETP/TR.
    Tenta usar cache; se falhar, injeta fontes inline.
    """
    client = _client()
    cache_name = criar_ou_recuperar_cache()

    try:
        if cache_name:
            response = client.models.generate_content(
                model=(settings.GEMINI_MODEL_GERACAO or settings.GEMINI_MODEL),
                contents=prompt_geracao,
                config=types.GenerateContentConfig(
                    cached_content=cache_name,
                    response_mime_type="application/json",
                    max_output_tokens=LIMITE_TOKENS_OUTPUT,
                ),
            )
        else:
            fontes = obter_textos_fontes_verdade()
            prompt_com_fontes = (
                f"## FONTES DE VERDADE LEGAIS\n\n{fontes}\n\n"
                f"---\n\n{prompt_geracao}"
            )
            response = client.models.generate_content(
                model=(settings.GEMINI_MODEL_GERACAO or settings.GEMINI_MODEL),
                contents=prompt_com_fontes,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    max_output_tokens=LIMITE_TOKENS_OUTPUT,
                ),
            )
    except Exception as e:
        # Fallback: sem cache, injeta inline
        logger.warning(f"Falha na chamada com cache, tentando inline: {e}")
        fontes = obter_textos_fontes_verdade()
        prompt_com_fontes = (
            f"## FONTES DE VERDADE LEGAIS\n\n{fontes}\n\n"
            f"---\n\n{prompt_geracao}"
        )
        response = client.models.generate_content(
            model=(settings.GEMINI_MODEL_GERACAO or settings.GEMINI_MODEL),
            contents=prompt_com_fontes,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                max_output_tokens=LIMITE_TOKENS_OUTPUT,
            ),
        )

    uso = response.usage_metadata
    if uso is not None:
        logger.info(
            f"[geracao] tokens — input: {uso.prompt_token_count:,} | "
            f"output: {uso.candidates_token_count:,} | total: {uso.total_token_count:,}"
        )

    if response.text is None:
        raise ValueError(
            f"Resposta do Gemini sem texto (finish_reason="
            f"{response.candidates[0].finish_reason if response.candidates else None})"
        )

    return _extrair_json_da_resposta(response.text)


def resumir_textos_pdfs(textos_pdfs: dict) -> dict:
    resultado = {}
    chamadas = 0

    for nome_arquivo, info in textos_pdfs.items():
        texto = info.get("texto", "")
        if info.get("status") != "ok" or len(texto) <= LIMITE_RESUMO_CHARS:
            resultado[nome_arquivo] = info
            continue

        resumo = resumir_documento(nome_arquivo, texto)
        chamadas += 1
        resultado[nome_arquivo] = {**info, "texto": resumo, "resumido": True}

    logger.info(
        f"resumir_textos_pdfs: {chamadas} documento(s) resumido(s) de {len(textos_pdfs)} no total."
    )
    return resultado
