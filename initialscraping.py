import json
import os
import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

TERMO_BUSCA = "cafe"
URL = "https://www.portaldecompraspublicas.com.br/processos"
OUTPUT_FILE = "resultados.json"
PASTA_DOWNLOADS = "downloads"

SITUACOES = {
    'Recebendo propostas', 'Aguardando início de recebimento de propostas',
    'Encerrado', 'Suspenso', 'Homologado', 'Deserto', 'Fracassado', 'Revogado'
}


def iniciar_driver():
    os.makedirs(PASTA_DOWNLOADS, exist_ok=True)
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_experimental_option("prefs", {
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    })
    driver = webdriver.Chrome(options=options)
    return driver


def fechar_banner_cookies(driver):
    try:
        btn = driver.find_element(By.XPATH, '//button[contains(@class, "adopt-c-jKIhxf")]')
        driver.execute_script("arguments[0].click();", btn)
        print("Banner de cookies fechado.")
        time.sleep(1)
    except Exception:
        pass


def buscar_processos(driver, termo):
    print("Abrindo URL...")
    driver.get(URL)
    print(f"Página carregada: {driver.title}")
    wait = WebDriverWait(driver, 20)

    fechar_banner_cookies(driver)

    print("Aguardando campo #objeto...")
    campo_objeto = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="objeto"]')))
    print("Campo encontrado! Digitando termo...")
    campo_objeto.clear()
    campo_objeto.send_keys(termo)
    campo_objeto.send_keys(Keys.ENTER)
    print("Enter pressionado. Aguardando resultados...")
    time.sleep(3)

    cards = driver.find_elements(By.XPATH, '//a[contains(@class, "process-card__link")]')
    print(f"Cards de processo encontrados: {len(cards)}")
    return cards


def parsear_processo(linhas):
    dados = {}

    # numero_processo e situacao
    for l in linhas:
        if 'Nº do Processo:' in l:
            dados['numero_processo'] = l.replace('Nº do Processo:', '').strip()
        if l in SITUACOES:
            dados['situacao'] = l

    # comprador e modalidade (ficam 3 e 2 linhas antes do Nº do Processo)
    try:
        idx = next(i for i, l in enumerate(linhas) if 'Nº do Processo:' in l)
        dados['comprador'] = linhas[idx - 3] if idx >= 3 else None
        dados['modalidade'] = linhas[idx - 2] if idx >= 2 else None
    except StopIteration:
        pass

    # objeto: texto mais longo antes de "Informações"
    try:
        idx_info = next(i for i, l in enumerate(linhas) if l == 'Informações')
        dados['objeto'] = max(linhas[:idx_info], key=len, default=None)
    except StopIteration:
        pass

    # Informações (pares chave: valor entre "Informações" e "Datas")
    dados['informacoes'] = {}
    try:
        idx_info = next(i for i, l in enumerate(linhas) if l == 'Informações')
        idx_datas = next(i for i, l in enumerate(linhas) if l == 'Datas')
        i = idx_info + 1
        while i < idx_datas - 1:
            if linhas[i].endswith(':'):
                dados['informacoes'][linhas[i][:-1]] = linhas[i + 1]
                i += 2
            else:
                i += 1
    except StopIteration:
        pass

    # Datas (label seguido de data no formato dd/mm/yyyy)
    dados['datas'] = {}
    try:
        idx_datas = next(i for i, l in enumerate(linhas) if l == 'Datas')
        fim_datas = next(
            i for i, l in enumerate(linhas)
            if i > idx_datas and l in ('ESCLARECIMENTO', 'Documentos', 'Itens')
        )
        i = idx_datas + 1
        while i < fim_datas - 1:
            if re.match(r'\d{2}/\d{2}/\d{4}', linhas[i + 1]):
                dados['datas'][linhas[i]] = linhas[i + 1]
                i += 2
            else:
                i += 1
    except (StopIteration, IndexError):
        pass

    # Documentos (nomes, tipos, datas — URLs extraídas separadamente)
    dados['documentos'] = []
    try:
        idx_docs = next(i for i, l in enumerate(linhas) if l == 'Documentos')
        idx_itens = next(i for i, l in enumerate(linhas) if l == 'Itens' and i > idx_docs)
        i = idx_docs + 1
        doc_atual = {}
        while i < idx_itens:
            l = linhas[i]
            if l in ('Processo', 'Fornecedores'):
                i += 1
                continue
            if l.startswith('Tipo:'):
                doc_atual['tipo'] = l.replace('Tipo:', '').strip()
            elif re.match(r'\d{2}/\d{2}/\d{4}-\d{2}:\d{2}:\d{2}', l):
                doc_atual['data'] = l
                if doc_atual:
                    dados['documentos'].append(doc_atual)
                doc_atual = {}
            else:
                doc_atual['nome'] = l
            i += 1
    except StopIteration:
        pass

    # Itens
    dados['itens'] = []
    try:
        idx_itens = next(i for i, l in enumerate(linhas) if l == 'Itens')
        idx_andamento = next(
            i for i, l in enumerate(linhas)
            if l == 'Andamento do processo' and i > idx_itens
        )
        i = idx_itens + 1
        while i < idx_andamento and not re.match(r'^Item \d+$', linhas[i]):
            i += 1

        item_atual = None
        while i < idx_andamento:
            l = linhas[i]
            if re.match(r'^Item \d+$', l):
                if item_atual:
                    dados['itens'].append(item_atual)
                item_atual = {'numero': l}
            elif item_atual is not None:
                if l in ('Fechado', 'Recebendo Propostas', 'Suspenso', 'Aberto', 'Homologado'):
                    item_atual['situacao_item'] = l
                elif l.endswith(':') and i + 1 < idx_andamento:
                    chave = l[:-1].lower().replace(' ', '_')
                    item_atual[chave] = linhas[i + 1]
                    i += 2
                    continue
                elif 'descricao' not in item_atual and len(l) > 5:
                    item_atual['descricao'] = l
            i += 1
        if item_atual:
            dados['itens'].append(item_atual)
    except (StopIteration, IndexError) as e:
        dados['itens_erro'] = str(e)

    # Andamento
    dados['andamento'] = []
    try:
        idx_andamento = next(i for i, l in enumerate(linhas) if l == 'Andamento do processo')
        i = idx_andamento + 1
        while i < len(linhas):
            l = linhas[i]
            if re.match(r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2} \|', l):
                entrada = {'data_hora_autor': l}
                if i + 1 < len(linhas):
                    entrada['descricao'] = linhas[i + 1]
                    i += 2
                    dados['andamento'].append(entrada)
                    continue
            i += 1
    except StopIteration:
        pass

    return dados


def extrair_dados_processo(driver):
    time.sleep(2)

    try:
        texto = driver.find_element(By.TAG_NAME, 'main').text
    except Exception:
        texto = driver.find_element(By.TAG_NAME, 'body').text

    linhas = [l.strip() for l in texto.split('\n') if l.strip()]
    dados = {'url': driver.current_url}
    dados.update(parsear_processo(linhas))
    dados['conteudo_bruto'] = linhas
    return dados


def aguardar_download(pasta, arquivos_antes, timeout=30):
    inicio = time.time()
    while time.time() - inicio < timeout:
        todos = set(os.listdir(pasta))
        em_progresso = [f for f in todos if f.endswith('.crdownload') or f.endswith('.tmp')]
        novos = todos - arquivos_antes - set(em_progresso)
        if novos and not em_progresso:
            return novos
        time.sleep(0.5)
    # Retorna o que houver mesmo assim
    return set(os.listdir(pasta)) - arquivos_antes - {f for f in os.listdir(pasta) if f.endswith('.crdownload')}


def baixar_documentos(driver, url_processo):
    slug = url_processo.rstrip('/').split('/')[-1]
    pasta = os.path.abspath(os.path.join(PASTA_DOWNLOADS, slug))
    os.makedirs(pasta, exist_ok=True)

    driver.execute_cdp_cmd("Page.setDownloadBehavior", {
        "behavior": "allow",
        "downloadPath": pasta,
    })

    # Conta quantos botões existem dentro de document-wrapper (os botões de download por documento)
    n_botoes = len(driver.find_elements(By.CSS_SELECTOR, "div.document-wrapper button"))
    if n_botoes == 0:
        print("  Nenhum botão de download encontrado.")
        return []

    print(f"  {n_botoes} botão(ões) de download encontrado(s).")
    baixados = []

    for i in range(n_botoes):
        # Re-busca a cada iteração para evitar StaleElementReferenceException após re-render do Angular
        botoes = driver.find_elements(By.CSS_SELECTOR, "div.document-wrapper button")
        if i >= len(botoes):
            print(f"  [{i+1}] Botão não encontrado após re-render, pulando.")
            continue

        btn = botoes[i]

        # Nome: texto do card (2 níveis acima do botão), primeira linha
        try:
            nome_doc = btn.find_element(By.XPATH, './ancestor::div[2]').text.split('\n')[0].strip()
        except Exception:
            nome_doc = f"documento_{i + 1}"

        arquivos_antes = set(os.listdir(pasta))
        print(f"  [{i+1}] Baixando: {nome_doc}")

        try:
            driver.execute_script("arguments[0].click();", btn)
        except Exception as e:
            print(f"    -> Erro ao clicar: {e}")
            continue

        novos = aguardar_download(pasta, arquivos_antes, timeout=30)
        for nome in novos:
            tamanho = os.path.getsize(os.path.join(pasta, nome))
            baixados.append({'arquivo': nome, 'tamanho_bytes': tamanho, 'pasta': pasta})
            print(f"    -> {nome} ({tamanho:,} bytes)")

        if not novos:
            print(f"    -> Timeout ao baixar '{nome_doc}'")

    return baixados


def salvar_json(dados, arquivo):
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    print(f"Dados salvos em: {arquivo}")


def main():
    driver = iniciar_driver()
    resultado = {"termo_busca": TERMO_BUSCA, "processos": []}

    try:
        cards = buscar_processos(driver, TERMO_BUSCA)

        if not cards:
            print("Nenhum card de processo encontrado.")
            salvar_json(resultado, OUTPUT_FILE)
            return

        hrefs = [card.get_attribute("href") for card in cards[:4]]
        print(f"Coletados {len(hrefs)} processos para extrair.")

        for i, href in enumerate(hrefs, start=1):
            print(f"\n[{i}/{len(hrefs)}] Navegando para: {href}")
            driver.get(href)

            dados_processo = extrair_dados_processo(driver)
            print(f"  Processo: {dados_processo.get('numero_processo')} | {dados_processo.get('comprador')}")

            try:
                print("  Baixando documentos...")
                arquivos = baixar_documentos(driver, href)
            except Exception as e:
                print(f"  Erro ao baixar documentos: {e}")
                arquivos = []
            dados_processo['arquivos_baixados'] = arquivos

            resultado["processos"].append(dados_processo)

    except Exception as e:
        import traceback
        print(f"Erro: {e}")
        print(traceback.format_exc())
        resultado["erro"] = str(e)

    finally:
        salvar_json(resultado, OUTPUT_FILE)
        input("\nPressione Enter para fechar o navegador...")
        driver.quit()


if __name__ == "__main__":
    main()
