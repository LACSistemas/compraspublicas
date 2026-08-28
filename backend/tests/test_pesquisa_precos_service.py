from types import SimpleNamespace

from app.services.pesquisa_precos_service import (
    _aderencia,
    _calcular_resultado,
    _decimal,
    _termos_fallback,
)


def _observacao(valor: str, *, aderencia: int = 100, comparavel: bool = True):
    return SimpleNamespace(valor_unitario=valor, aderencia_pct=aderencia,
        comparavel=comparavel, processo_url=f"https://fonte.test/{valor}")


def test_planejamento_fallback_preserva_objeto_e_limite():
    perfil = {"descricao": "Aquisição de ambulância tipo 5",
        "termos_essenciais": ["ambulancia"]}
    termos = _termos_fallback(perfil, 5)
    assert termos[0] == perfil["descricao"]
    assert len(termos) == 5
    assert len({termo.casefold() for termo in termos}) == 5


def test_normalizacao_de_valor_e_aderencia():
    assert str(_decimal("R$ 123.456,78")) == "123456.78"
    perfil = {"termos_essenciais": ["ambulancia", "veiculo"]}
    assert _aderencia(perfil, "Veículo ambulância equipado") == 100


def test_resultado_exclui_nao_comparaveis_e_trata_outlier():
    observacoes = [_observacao(valor) for valor in ["100", "105", "110", "115", "1000"]]
    observacoes.append(_observacao("50", aderencia=10))
    resultado = _calcular_resultado(observacoes, [SimpleNamespace()] * 5)
    assert resultado["amostra"] == 5
    assert resultado["amostra_tratada"] == 4
    assert resultado["outliers"] == [1000.0]
    assert resultado["mediana"] == 107.5
    assert resultado["confianca"] == "media"
