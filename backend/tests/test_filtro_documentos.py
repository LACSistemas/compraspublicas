import pytest
import unicodedata

import app.scraper.filtro_documentos as fd


# ---------------------------------------------------------------------------
# Casos reais da execução de Ibuprofeno — fixtures de nomes/tipos do portal
# ---------------------------------------------------------------------------

CASOS = [
    # (nome, tipo, esperado_com_tipo, esperado_sem_tipo, descricao)

    # Provas do matching por token (e não substring)
    ("Portal Nacional de Contratações Públicas.pdf", None,    False, False, "filler com 'tr' dentro de 'contratacoes' — deve ser descartado"),
    ("TR_IBUPROFENO_300MG.pdf",                       None,    True,  True,  "token 'tr' com separador _ — deve ser mantido"),

    # Substring em nome concatenado (sem espaço)
    ("EDITAL2026028.pdf",                             None,    True,  True,  "edital sem espaço"),
    ("EDITAL2025-044 - Termo de Referência.pdf",      None,    True,  True,  "edital + acento em Referência"),

    # Mantido só via campo tipo quando USAR_CAMPO_TIPO=True
    ("PE087.2024.pdf",                                "Edital", True,  False, "nome neutro mas tipo=Edital"),
    ("DFD.pdf",                                       "Edital", True,  False, "DFD tipado como Edital — mantido pelo tipo"),

    # ETP
    ("ETP.pdf",                                       None,    True,  True,  "token 'etp'"),
    ("ETP_IBUPROFENO 300MG.pdf",                      None,    True,  True,  "token 'etp' com sufixo"),

    # Outros relevantes
    ("Mapa de Risco.pdf",                             None,    True,  True,  "mapa de risco"),
    ("MAPA DE RISCO.pdf",                             None,    True,  True,  "mapa de risco maiúsculas"),
    ("Matriz de Risco - Ibuprofeno.pdf",              None,    True,  True,  "matriz de risco"),
    ("Projeto Básico.pdf",                            None,    True,  True,  "projeto basico com acento"),
    ("Projeto básico - Termo de Referência.pdf",      "Projeto básico/Termo de referência",
                                                                 True,  True,  "projeto basico tipado"),

    # Filler — deve ser descartado
    ("Parecer Técnico.pdf",                           None,    False, False, "parecer técnico"),
    ("Julgamento Técnico.pdf",                        None,    False, False, "julgamento técnico"),
    ("Solicitação de Desclassificação.pdf",           None,    False, False, "desclassificação"),
    ("Análise Técnica.pdf",                           None,    False, False, "análise técnica"),
    ("Diligência 001.pdf",                            None,    False, False, "diligência"),
    ("Anexo II_Habilitação.pdf",                      None,    False, False, "habilitação"),
    ("ANEXO I_DADOS COMPLEMENTARES.docx",             None,    False, False, "anexo complementar"),
]


@pytest.mark.parametrize("nome,tipo,esperado_com_tipo,_,descricao", CASOS)
def test_com_tipo(nome, tipo, esperado_com_tipo, _, descricao):
    original = fd.USAR_CAMPO_TIPO
    fd.USAR_CAMPO_TIPO = True
    try:
        assert fd.documento_relevante(nome, tipo) == esperado_com_tipo, descricao
    finally:
        fd.USAR_CAMPO_TIPO = original


@pytest.mark.parametrize("nome,tipo,_,esperado_sem_tipo,descricao", CASOS)
def test_sem_tipo(nome, tipo, _, esperado_sem_tipo, descricao):
    original = fd.USAR_CAMPO_TIPO
    fd.USAR_CAMPO_TIPO = False
    try:
        assert fd.documento_relevante(nome, tipo) == esperado_sem_tipo, descricao
    finally:
        fd.USAR_CAMPO_TIPO = original


def test_filtrar_documentos_separa_corretamente():
    docs = [
        {"nome": "EDITAL2026028.pdf",                       "tipo": None},
        {"nome": "TR_IBUPROFENO_300MG.pdf",                 "tipo": None},
        {"nome": "Parecer Técnico.pdf",                     "tipo": None},
        {"nome": "Portal Nacional de Contratações Públicas.pdf", "tipo": None},
        {"nome": "PE087.2024.pdf",                          "tipo": "Edital"},
    ]
    fd.USAR_CAMPO_TIPO = True
    mantidos, descartados = fd.filtrar_documentos(docs)

    nomes_mantidos  = [d["nome"] for d in mantidos]
    nomes_descartados = [d["nome"] for d in descartados]

    assert "EDITAL2026028.pdf"                            in nomes_mantidos
    assert "TR_IBUPROFENO_300MG.pdf"                      in nomes_mantidos
    assert "PE087.2024.pdf"                               in nomes_mantidos
    assert "Parecer Técnico.pdf"                          in nomes_descartados
    assert "Portal Nacional de Contratações Públicas.pdf" in nomes_descartados
    assert len(mantidos) + len(descartados) == len(docs)
