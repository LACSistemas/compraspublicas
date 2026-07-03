import json
from app.services.gemini_service import montar_prompt_final, chamar_gemini, carregar_prompt_base

if __name__ == "__main__":
    with open("../resultados.json", "r", encoding="utf-8") as f:
        pesquisa_dict = json.load(f)
    pesquisa_dict["processos"] = pesquisa_dict["processos"][:1]  # só 1 processo pra teste rápido/barato
    textos_pdfs = {"documento_teste.pdf": {"texto": "Texto de exemplo de um edital fictício para teste.", "status": "ok"}}
    prompt = montar_prompt_final(pesquisa_dict, textos_pdfs, "2 toneladas", carregar_prompt_base())
    resultado = chamar_gemini(prompt)
    print(json.dumps(resultado, ensure_ascii=False, indent=2)[:3000])
    print("Chaves de topo:", list(resultado.keys()))
