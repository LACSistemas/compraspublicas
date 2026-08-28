CARDS_MANIFESTACAO_FORMAL = {"D001", "D006", "D007", "D008", "D009", "D014"}


def robustez_minima_aprovacao(codigo_card: str) -> int:
    return 75 if codigo_card in CARDS_MANIFESTACAO_FORMAL else 60
