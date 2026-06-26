PS C:\Projetos\compraspublicas> python initialscraping.py

DevTools listening on ws://127.0.0.1:51922/devtools/browser/f571ec2e-6ee4-4e34-9dc9-5b6600324c0d
Abrindo URL...
Página carregada: O Maior Marketplace de Licitações do Brasil
Banner de cookies fechado.
Aguardando campo #objeto...
Campo encontrado! Digitando termo...
Enter pressionado. Aguardando resultados...
[39524:39300:0608/094456.119:ERROR:google_apis\gcm\engine\registration_request.cc:291] Registration response error message: PHONE_REGISTRATION_ERROR
[39524:39300:0608/094456.152:ERROR:google_apis\gcm\engine\registration_request.cc:291] Registration response error message: PHONE_REGISTRATION_ERROR
[39524:39300:0608/094456.165:ERROR:google_apis\gcm\engine\registration_request.cc:291] Registration response error message: PHONE_REGISTRATION_ERROR
[39524:39300:0608/094456.268:ERROR:google_apis\gcm\engine\mcs_client.cc:702]   Error code: 401  Error message: Authentication Failed: wrong_secret
[39524:39300:0608/094456.268:ERROR:google_apis\gcm\engine\mcs_client.cc:704] Failed to log in to GCM, resetting connection.
Cards de processo encontrados: 24
Coletados 4 processos para extrair.

[1/4] Navegando para: https://www.portaldecompraspublicas.com.br/processos/mt/prefeitura-municipal-de-colider-589/pe-020-2026-2026-484925
  Processo: 020/2026 | Prefeitura Municipal de Colíder
  Baixando documentos...
  3 botão(ões) de download encontrado(s).
  [1] Baixando: Documentos
Created TensorFlow Lite XNNPACK delegate for CPU.
    -> downloads.htm (33,619,428 bytes)
  [2] Baixando: Documentos
[39524:39300:0608/094521.651:ERROR:google_apis\gcm\engine\registration_request.cc:291] Registration response error message: DEPRECATED_ENDPOINT
    -> Timeout: nenhum arquivo baixado para 'Documentos'
  [3] Baixando: documento_3
Erro: Message: stale element reference: stale element not found in the current frame
  (Session info: chrome=148.0.7778.179); For documentation on this error, please visit: https://www.selenium.dev/documentation/webdriver/troubleshooting/errors#staleelementreferenceexception
Stacktrace:
        chromedriver!GetHandleVerifier [0x7ff6d41b7de5+14895]
        chromedriver!GetHandleVerifier [0x7ff6d41b7e50+14900]
        chromedriver!(No symbol) [0x7ff6d3f1d5ad]
        chromedriver!(No symbol) [0x7ff6d3f25521]
        chromedriver!(No symbol) [0x7ff6d3f2897f]
        chromedriver!(No symbol) [0x7ff6d3fc5c7d]
        chromedriver!(No symbol) [0x7ff6d3fa005a]
        chromedriver!(No symbol) [0x7ff6d3fc486f]
        chromedriver!(No symbol) [0x7ff6d3f69df8]
        chromedriver!(No symbol) [0x7ff6d3f6ace3]
        chromedriver!GetHandleVerifier [0x7ff6d44ccc49+3296f9]
        chromedriver!GetHandleVerifier [0x7ff6d44c7375+323e25]
        chromedriver!GetHandleVerifier [0x7ff6d44ebc82+348732]
        chromedriver!GetHandleVerifier [0x7ff6d41d6045+32af5]
        chromedriver!GetHandleVerifier [0x7ff6d41decec+3b79c]
        chromedriver!GetHandleVerifier [0x7ff6d41c1bc4+1e674]
        chromedriver!GetHandleVerifier [0x7ff6d41c1d54+1e804]
        chromedriver!GetHandleVerifier [0x7ff6d41a60e7+2b97]
        KERNEL32!BaseThreadInitThunk [0x7ffb5291e957+17]
        ntdll!RtlUserThreadStart [0x7ffb53c8427c+2c]

Traceback (most recent call last):
  File "C:\Projetos\compraspublicas\initialscraping.py", line 312, in main
    arquivos = baixar_documentos(driver, href)
  File "C:\Projetos\compraspublicas\initialscraping.py", line 268, in baixar_documentos
    driver.execute_script("arguments[0].click();", btn)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\lucas\AppData\Local\Programs\Python\Python313\Lib\site-packages\selenium\webdriver\remote\webdriver.py", line 551, in execute_script
    return self.execute(command, {"script": script, "args": converted_args})["value"]
           ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\lucas\AppData\Local\Programs\Python\Python313\Lib\site-packages\selenium\webdriver\remote\webdriver.py", line 454, in execute
    self.error_handler.check_response(response)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^
  File "C:\Users\lucas\AppData\Local\Programs\Python\Python313\Lib\site-packages\selenium\webdriver\remote\errorhandler.py", line 232, in check_response
    raise exception_class(message, screen, stacktrace)
selenium.common.exceptions.StaleElementReferenceException: Message: stale element reference: stale element not found in the current frame
  (Session info: chrome=148.0.7778.179); For documentation on this error, please visit: https://www.selenium.dev/documentation/webdriver/troubleshooting/errors#staleelementreferenceexception
Stacktrace:
        chromedriver!GetHandleVerifier [0x7ff6d41b7de5+14895]
        chromedriver!GetHandleVerifier [0x7ff6d41b7e50+14900]
        chromedriver!(No symbol) [0x7ff6d3f1d5ad]
        chromedriver!(No symbol) [0x7ff6d3f25521]
        chromedriver!(No symbol) [0x7ff6d3f2897f]
        chromedriver!(No symbol) [0x7ff6d3fc5c7d]
        chromedriver!(No symbol) [0x7ff6d3fa005a]
        chromedriver!(No symbol) [0x7ff6d3fc486f]
        chromedriver!(No symbol) [0x7ff6d3f69df8]
        chromedriver!(No symbol) [0x7ff6d3f6ace3]
        chromedriver!GetHandleVerifier [0x7ff6d44ccc49+3296f9]
        chromedriver!GetHandleVerifier [0x7ff6d44c7375+323e25]
        chromedriver!GetHandleVerifier [0x7ff6d44ebc82+348732]
        chromedriver!GetHandleVerifier [0x7ff6d41d6045+32af5]
        chromedriver!GetHandleVerifier [0x7ff6d41decec+3b79c]
        chromedriver!GetHandleVerifier [0x7ff6d41c1bc4+1e674]
        chromedriver!GetHandleVerifier [0x7ff6d41c1d54+1e804]
        chromedriver!GetHandleVerifier [0x7ff6d41a60e7+2b97]
        KERNEL32!BaseThreadInitThunk [0x7ffb5291e957+17]
        ntdll!RtlUserThreadStart [0x7ffb53c8427c+2c]


Dados salvos em: resultados.json

O que aconteceu? Nao necessariamente todas paginas vai ter link pra baixar