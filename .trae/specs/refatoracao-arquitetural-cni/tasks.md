# Refatoração Arquitetural Automação CNI - Implementation Plan

---

## Task 1: Backup + Estrutura de Diretórios e Módulos (esqueletos)
- **Status**: `pending`
- **Priority**: high
- **Depends On**: None
- **Description**:
  - Fazer backup do monólito atual para `main_monolith_backup.py` (preservação 100% do original)
  - Criar estrutura de diretórios: `config/`, `core/`, `infrastructure/`, `infrastructure/browser/`, `domain/`, `services/`, `pages/`
  - Criar arquivos `__init__.py` em todos os packages
  - Criar arquivos vazios: `config/settings.py`, `config/constants.py`, `core/errors.py`, `core/retry.py`, `infrastructure/browser/__init__.py`, `infrastructure/browser/driver.py`, `infrastructure/browser/waits.py`, `infrastructure/browser/actions.py`, `domain/models.py`, `domain/mappings.py`, `domain/validators.py`, `services/auth_service.py`, `services/navigation_service.py`, `services/pesquisa_service.py`, `pages/base_page.py`, `pages/login_page.py`, `pages/menu_page.py`, `pages/parametros_page.py`, `pages/resultados_page.py`
  - Criar `requirements.txt` + `.env.example`
- **Acceptance Criteria Addressed**: AC-1, AC-3
- **Test Requirements**:
  - `rule` TR-1.1: Estrutura de diretórios e arquivos existe exatamente como listado. Evidence: `Get-ChildItem -Recurse -Directory -Name` + `Get-ChildItem -Recurse -File -Name` (exceto venv/pycache).
  - `rule` TR-1.2: `main_monolith_backup.py` tem conteúdo idêntico ao `main.py` original. Evidence: `Compare-Object (Get-Content main.py) (Get-Content main_monolith_backup.py)` vazio.
  - `rule` TR-1.3: Todos os arquivos `__init__.py` e arquivos vazios criados passam `py_compile` (exit 0). Evidence: `python -m py_compile` em cada um.
- **Notes**: Nenhum código funcional ainda; só esqueleto. AC-1 cobre estrutura básica.

---

## Task 2: `config/` - Settings, Constantes e Mappings (lidos do monólito)
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 1
- **Description**:
  - Extrair do monólito todas as constantes para `config/constants.py`: `_PERFIS` (dicionário com perfis intactos), IDs do formulário (`selectForm:*`), base URL (`https://pesquisasconjunturais.cni.com.br/...`), preferências labels Estrato (`preferencia_labels`).
  - Extrair para `domain/mappings.py`: `VAR_COD_POR_VALUE` (dicionário intacto).
  - Criar `config/settings.py` com carregamento de variáveis de ambiente (`CNI_USER`, `CNI_PASSWORD`) via `python-dotenv`, com função `get_settings()` que retorna objeto `Settings` dataclass e levanta `ValidationError` se credenciais ausentes.
  - Criar `.env.example` com `CNI_USER=` e `CNI_PASSWORD=` (valores VAZIOS).
  - **Se Q1 aprovado (Pydantic)**: usar `pydantic_settings.BaseSettings`; senão fallback `@dataclass` + `os.getenv` + `pathlib` para `.env`.
- **Acceptance Criteria Addressed**: AC-1 (requirements.txt/.env), AC-3 (settings validam credenciais), AC-10 (perfis não alterados)
- **Test Requirements**:
  - `rule` TR-2.1: `_PERFIS` em `config/constants.py` é deep-equal ao do backup. Evidence: comparação por `deepdiff` ou código Python assertiva.
  - `rule` TR-2.2: `VAR_COD_POR_VALUE` em `domain/mappings.py` é deep-equal ao do backup. Evidence: idem.
  - `rule` TR-2.3: `settings.get_settings()` sem env/.env levanta ValidationError com menção a "CNI_USER" e "CNI_PASSWORD". Evidence: snippet REPL.
  - `rule` TR-2.4: `.env.example` contém CNI_USER/CNI_PASSWORD vazios e NÃO contém valores reais. Evidence: grep por `@`/`#` (senhas hardcoded) = 0.
- **Notes**: Q1/Q5 pendentes. Fallback: `@dataclass` sem Pydantic; settings validam em `__post_init__`.

---

## Task 3: `core/errors.py` - Hierarquia AppError e `core/retry.py` Decorator
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 1
- **Description**:
  - Implementar `core/errors.py`: `class AppError(Exception)` → subclasses `RetryableError(AppError)`, `ValidationError(AppError)`, `BrowserError(RetryableError)`, `TimeoutError(RetryableError)`, `NavigationError(AppError)`. Todas aceitam `message: str`, `cause: Optional[BaseException]=None`. `__str__` inclui mensagem e causa se houver.
  - Implementar `core/retry.py`: função `with_retry(max_attempts=3, initial_delay=0.05, backoff_factor=2.0, jitter=0.02, retry_on=(RetryableError, StaleElementReferenceException, ElementNotInteractableException))` como decorator genérico que (a) executa função, (b) em exceção pertencente a `retry_on`, sleep com `delay = initial_delay * (backoff_factor**(attempt-1)) + uniform(0, jitter)` antes de retry, (c) após última tentativa, re-levanta exceção original (encapsulada em RetryableError se não for da lista).
- **Acceptance Criteria Addressed**: AC-5
- **Test Requirements**:
  - `rule` TR-3.1: Hierarquia de 6 classes existe e isinstance funciona. Evidence: `isinstance(ValidationError(""), AppError) == True`, `isinstance(ValidationError(""), RetryableError) == False`, `isinstance(BrowserError(""), RetryableError) == True`.
  - `rule` TR-3.2: `@with_retry(max_attempts=3)` aplicado em função que sempre levanta `StaleElementReferenceException` resulta em exatamente 3 tentativas e depois propaga exceção. Sleeps são progressivos. Evidence: snippet de teste com mock sleep/counter.
  - `rule` TR-3.3: `@with_retry` aplicado em função que retorna sucesso na 2a tentativa, retorna resultado sem exceção. Evidence: snippet counter == 2 e return value ok.
- **Notes**: Q3 (pytest) se aprovado, testes ficam em `tests/test_core.py`. Caso contrário, validação snippets in-memory.

---

## Task 4: `infrastructure/browser/driver.py` - Gerenciamento de Ciclo de Vida
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 1, Task 3
- **Description**:
  - Criar `create_driver() -> webdriver.Chrome`: instancia `webdriver.Chrome()` (default, SEM options custom, igual monólito), chama `.maximize_window()`, retorna driver. Tudo envolto em try/except que converte exceções genéricas de Selenium em `BrowserError`.
  - Criar `teardown_driver(driver) -> None`: chama `.quit()` com segurança (exc = BrowserError encapsulada).
  - Opcional: context manager `BrowserDriver()` com `__enter__` retorna create_driver(), `__exit__` chama teardown_driver().
- **Acceptance Criteria Addressed**: AC-2, FR-2
- **Test Requirements**:
  - `rule` TR-4.1: `create_driver()` retorna instância de `webdriver.Chrome`. Evidence: assert isinstance.
  - `rule` TR-4.2: `teardown_driver(driver)` fecha sessão sem exceção. Evidence: driver.session_id é None após.
  - `rule` TR-4.3: Nenhuma variável global driver é criada no módulo. Evidence: grep por `^driver =` no arquivo = 0.
- **Notes**: AC-2 (NÃO criar estado global) é essencial aqui. Driver só existe como retorno/parâmetro.

---

## Task 5: `infrastructure/browser/waits.py` + `actions.py` - Helpers Movidos INTACTOS
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 1, Task 2 (constants/_PERFIS), Task 3 (erros)
- **Description**:
  - **Waits (100% código preservado do monólito, só assinaturas adicionam `driver` primeiro parâmetro e importam `_PERFIS` de `config.constants`)**: `_pagina_status`, `_sem_overlays_de_carregamento`, `_ajax_em_repouso`, `_elemento_habilitado`, `_limpar_overlays_orphans`, `aguardar_pagina_pronta`, `aguardar_ajax`, `esperar_estavel`, `aguardar_navegacao`, `aguardar_tela_inicial`.
  - **Actions (código preservado do monólito, driver primeiro parâmetro)**: `clicar_com_retry(driver, locator, tentativas=3)`, `hover_em(driver, locator, tentativas=3)`, `passo(titulo, fn, *args, modo_antes, modo_depois)` (agora aceita driver param opcional ou usa closures), `preencher_login_rapido(driver, locator, valor, sensivel=False)` → integra com `preencher_texto_simples`, `preencher_texto_simples(driver, locator, valor, sensivel=False)`, `_locator_to_css(locator)` (sem driver, util puro), `fechar_painel_selectcheckboxmenu(driver, base_id, timeout=8)`, `marcar_radiobutton_primefaces(driver, table_id, value_alvo, label_table=None, timeout=10)`, `abrir_selectcheckboxmenu_primefaces(driver, base_id, timeout_geral=...)`, `_validar_campo_preenchido(driver, locator, valor_esperado)`, `_preencher_por_send_keys_direto(driver, locator, valor, limpar=True)`, `_preencher_por_js_com_events(driver, locator, valor)`, `_preencher_por_action_chains(driver, locator, valor)`, `_ajustar_checkboxes_js(driver, base_id, modo="todas", valores_desejados=None, labels_preferidas=None)`, `_checar_mensagem_obrigatorio(driver)`, `selecionar_valor(driver, locator, valor, tipo="select")`, `valor_campo_jah_correto(driver, locator, valor_esperado, tipo="select")`, `tentar_por_trigger_e_options(driver, locator_select_hidden, valor_option)`, `fechar_popups_e_dialogos(driver)`, `clicar_por_atividade_turbo(driver, timeout_geral=...)`.
  - WAITS: Trocar TODAS as ocorrências de `driver.` (global do monólito) por parâmetro `driver`. Mesmo para `actions` (usar `ActionChains(driver)` local se necessário em vez de global).
- **Acceptance Criteria Addressed**: AC-7 (waits intactos), AC-10 (gains JS preservados)
- **Test Requirements**:
  - `rule` TR-5.1: `_PERFIS` é importado de `config.constants` e NÃO redefinido inline. Evidence: grep por `_PERFIS = {` = 0 em waits.py.
  - `rule` TR-5.2: `_ajustar_checkboxes_js(driver, ...)` contém exatamente o mesmo script JS do monólito (string multilinha idêntica). Evidence: diff de strings.
  - `rule` TR-5.3: `selecionar_valor` early return topo usa o mesmo script JS nativo `s.value` do monólito (NÃO usa Selenium Select.first_selected_option). Evidence: grep por `Select(el).first_selected_option.value` dentro de selecionar_valor/tentar_por_trigger = 0.
  - `rule` TR-5.4: `clicar_por_atividade_turbo(driver, ...)` usa `Function(attr.onclick).call(window)` (identical ao monólito). Evidence: grep por `Function.call(window)`.
- **Notes**: MAIOR TAREFA da refatoração. Alinhamento 100% com os blocos do monólito. NÃO inventar otimizações novas aqui; mover intacto.

---

## Task 6: `domain/models.py` + `validators.py` - `PesquisaParams` Tipado
- **Status**: `pending`
- **Priority**: medium
- **Depends On**: Task 1, Task 3 (ValidationError), Task 2 (mappings VAR_COD_POR_VALUE opcional para validar códigos)
- **Description**:
  - Definir `PesquisaParams` com atributos: `coorte: str` (ex "634"), `mes_inicio: int` (0-11), `ano_inicio: int` (4 dígitos), `mes_fim: int` (0-11), `ano_fim: int`, `codigos_variaveis: list[str]` (ex ["17","21","23","25"]), `tipo_estimativa: str` (ex "21"), `exibicao: bool` (True=Valor, False=Variação), `orientacao: str` ("LINHA" ou "COLUNA").
  - Validadores: (a) mes_inicio e mes_fim ∈ 0..11; (b) ano_inicio/ano_fim >= 1990 e <= 2100; (c) codigos_variaveis não vazio; (d) tipo_estimativa ∈ {"21"} por enquanto (ou mais se soubermos); (e) orientacao ∈ {"LINHA","COLUNA"}.
  - **Se Q1 aprovado**: `pydantic.BaseModel` com `field_validator`. Fallback: `@dataclass` + `__post_init__` que levanta `ValidationError` de core.errors.
  - `domain/validators.py`: funções utilitárias `validar_mes(val: int) -> int`, `validar_ano(val: int) -> int`, `validar_lista_codigos(cods: list[str]) -> list[str]` para reuso.
- **Acceptance Criteria Addressed**: AC-6, NFR-1 (100% type hints em models)
- **Test Requirements**:
  - `rule` TR-6.1: `PesquisaParams` com valores válidos é construído sem erro. Evidence: exemplo params = PesquisaParams("634", 5, 2026, 7, 2026, ["17","21","23","25"], "21", True, "LINHA") ok.
  - `rule` TR-6.2: `PesquisaParams(mes_inicio=13, ...)` levanta ValidationError. Evidence: try/except.
  - `rule` TR-6.3: `PesquisaParams(orientacao="INVALIDO", ...)` levanta ValidationError. Evidence: idem.
  - `rubric` TR-6.4: Type hints; scale 1-3; 1=não tipado, 2=parcial, 3=total; threshold>=3; evidence: inspeção do arquivo.
- **Notes**: Evita validações inventadas (NÃO inventar restrições além das óbvias listadas).

---

## Task 7: Pages - Page Object Model Base + 4 Telas
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 4, Task 5, Task 2 (constants IDs)
- **Description**:
  - `pages/base_page.py`: `class BasePage: __init__(self, driver)` salva `self._driver`. Métodos utilitários proxy: `_click(locator)`, `_wait_element(locator, timeout=5)`, `_find(locator)`, `_aguardar_pronta(modo="leve")` (delega para infrastructure waits).
  - `pages/login_page.py`: `LoginPage(BasePage)`. Locators privados: `_USER_LOCATOR = (By.ID, "loginForm:username")`, `_SENHA_LOCATOR = (By.ID, "loginForm:password")`, `_SUBMIT_LOCATOR = (By.ID, "loginForm:j_idt23")` (ajustar IDs exatos do backup). Método `logar(user: str, senha: str) -> tuple[bool, str]` (retorna logou, msg_erro). Encapsula `preencher_login_rapido` e submit. Não orquestra waits pós-login (delega para AuthService).
  - `pages/menu_page.py`: `MenuPage(BasePage)`. Métodos: `clicar_menu_sondagem_industrial()`, `hover_consultas()`, `hover_resultados_indices()`, `clicar_federacao()`, `clicar_link_por_atividade() -> bool`. Encapsula `passo_hover_menu`, `passo_clique_menu`, `clicar_por_atividade_turbo`. Não orquestra sequência (delega NavigationService).
  - `pages/parametros_page.py`: `ParametrosPage(BasePage)`. MÉTODOS (cada um corresponde a um preenchimento do monólito): `preencher_coorte(valor)`, `preencher_mes_inicio(valor)`, `preencher_ano_inicio(valor)`, `preencher_mes_fim(valor)`, `preencher_ano_fim(valor)` → todos usam `selecionar_valor` ou `preencher_texto_simples` com modos_antes/modo_depois de config/constants (como monólito: Coorte modo_depois estrito, mesFim/anoFim modo_depois instantaneo). Métodos: `preencher_estrato() -> bool`, `preencher_variaveis(codigos_variaveis: list[str]) -> int`, `marcar_tipo_estimativa_por_value(value="21")`, `marcar_exibicao_por_value(valor: bool)`, `marcar_orientacao_por_value(valor: str)`, `clicar_pesquisar()`. Locators de campos/checkboxes/radios são constantes privadas na classe.
  - `pages/resultados_page.py`: `ResultadosPage(BasePage)`. Métodos: `aguardar_datatable(timeout=30)`, `exportar_excel() -> str` (clica link j_idt140). Locator `_EXPORT_LOCATOR = (By.ID, "listDifusaoLinhaForm:indicesVariavelDataTable:j_idt140")`.
- **Acceptance Criteria Addressed**: AC-4 (Pages existem, locators privados)
- **Test Requirements**:
  - `rule` TR-7.1: Todas as 4 pages herdam de BasePage e recebem driver no __init__. Evidence: inspeção.
  - `rule` TR-7.2: `services/` (ainda não implementado) deve poder usar pages sem importar By. Evidence: Pages expõem métodos de alto nível; API pública não contém parâmetros locator.
  - `rule` TR-7.3: Nenhum `By.ID` ou `By.CSS_SELECTOR` está hardcoded no corpo do método; são atributos de classe privados `_X_LOCATOR`. Evidence: grep por `By\.` no corpo de métodos (fora dos atributos de classe) = 0 ou exceções justificadas.
- **Notes**: Identificar IDs exatos no backup (monólito) para não errar. Todos os `By.ID` para `selectForm:*` (NÃO CSS #).

---

## Task 8: Services - Auth, Navigation, Pesquisa (Orquestração Pipeline)
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 7, Task 6, Task 3 (with_retry decorator)
- **Description**:
  - `services/auth_service.py`: `AuthService` recebe `driver` no construtor. Métodos: `fazer_login(user, senha) -> bool`: chama `LoginPage.logar`, aplica `@with_retry(max_attempts=2)`. Método `aguardar_render_pos_login()`: encapsula render pós-login do monólito (FASE 1.2).
  - `services/navigation_service.py`: `NavigationService` recebe `driver`. Método `navegar_ate_parametros_por_atividade() -> bool` (FASE 2): orquestra ordem de menus exatamente igual ao monólito (Sondagem Industrial → hover Consultas → Resultados/Índices → Federação → Por Atividade + submit onclick + staleness wait). Aplica `@with_retry` sobre navegação completa ou steps individualmente.
  - `services/pesquisa_service.py`: `PesquisaService` recebe `driver`. Método `executar_pesquisa(params: PesquisaParams)`: (FASE 3 + FASE 4): Ordem RÍGIDA: 5 filtros → 3.2 Estrato → 3.1 Variáveis → Radios TipoEstimativa → Exibição → 3.4 Orientação → Clicar Pesquisar → Export Excel. NÃO inverte NENHUMA ordem. Aplica `@with_retry` no passo `clicar_pesquisar` e Export se transiente. Retorna None ou path download (se detectável).
- **Acceptance Criteria Addressed**: AC-7 (services não chamam find_element, delegam pages), FR-8/G8 (ordem rígida)
- **Test Requirements**:
  - `rule` TR-8.1: `PesquisaService.executar_pesquisa` NÃO importa `By` e NÃO chama `find_element`/`Select`/Selenium expected_conditions diretamente (só via pages/infra). Evidence: grep de `By\.`, `find_element`, `Select(` em services/ = 0 (exceto tipos de exceção).
  - `rule` TR-8.2: Ordem FASE 3 em `executar_pesquisa` é: filtros → estrato → variáveis → tipo_estimativa → exibição → orientação → pesquisar. Evidence: inspeção de ordem de chamadas no código.
  - `rule` TR-8.3: `@with_retry` está aplicado em pelo menos 3 pontos (login, navegação, pesquisar/export). Evidence: grep por `@with_retry`.
- **Notes**: `FR-8` é hard constraint. Qualquer inversão → bug.

---

## Task 9: Entry Point `main.py` Novo (PIPELINE COMPLETO)
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 2 (settings), Task 4 (driver), Task 8 (3 services), Task 6 (PesquisaParams default)
- **Description**:
  - Novo `main.py` < 200 linhas. Fluxo:
    1. `from __future__ import annotations`, imports mínimos.
    2. `settings = get_settings()` → valida credenciais (ValidationError se ausentes).
    3. `driver = create_driver()` → BrowserError se falha.
    4. `try: driver.get(URL_BASE de config/constants)` → Navegação inicial.
    5. FASE 1: `auth_svc = AuthService(driver) ; auth_svc.fazer_login(settings.cni_user, settings.cni_password)` → levanta NavigationError se falhar após retry.
    6. FASE 1.2: `auth_svc.aguardar_render_pos_login()`.
    7. FASE 2: `nav_svc = NavigationService(driver) ; nav_svc.navegar_ate_parametros_por_atividade()` → NavigationError se falhar.
    8. FASE 3+4: Instancia `params = PesquisaParams(VALORES DEFAULT DO MONÓLITO)` (Ceará 634, Junho 5, 2026, Agosto 7, 2026, ["17","21","23","25"], tipo_estimativa="21", exibicao=True, orientacao="LINHA").
    9. `pesq_svc = PesquisaService(driver) ; pesq_svc.executar_pesquisa(params)`.
    10. Prints de `SUCESSO` + sleep curto (igual monólito, mas reduzido, 3s de preferência).
    11. `finally: teardown_driver(driver)`.
  - NÃO há lógica de UI nem constantes inline; tudo vem de modules.
- **Acceptance Criteria Addressed**: AC-1 (main.py novo <200 linhas), FR-1 (paridade funcional), AC-8 (rubrica paridade), FR-12 (security: NÃO loga senha)
- **Test Requirements**:
  - `rule` TR-9.1: `main.py` tem < 200 linhas (incluindo linhas vazias). Evidence: `(Get-Content main.py).Count`.
  - `rule` TR-9.2: `main.py` NÃO contém strings hardcoded de senha real. Evidence: grep por `@` + senha backup = 0 no novo main.
  - `rule` TR-9.3: Bloco `finally: teardown_driver(driver)` está presente. Evidence: inspeção main.py.
  - `rule` TR-9.4: `requirements.txt` lista `selenium==4.49.0`, `python-dotenv>=1.0` e (Q1/Q3 aprovados) `pydantic>=2.0`, `pytest>=8.0`. Evidence: Read requirements.txt.
- **Notes**: Entry point é PONTO DE ENTRADA FINAL; NÃO deve conter helpers inline.

---

## Task 10: Validação Compilação Global + Diagnósticos + Smoke Test Integrado
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Tasks 1-9 COMPLETAS (inclusive main.py novo)
- **Description**:
  - Rodar `python -m py_compile` em TODOS os arquivos Python novos (exceto backup venv pycache).
  - Rodar `GetDiagnostics` no IDE para erros de lint/type.
  - Rodar **smoke test de import**: `python -c "import config, core, infrastructure.browser, domain, services, pages ; from config import settings, constants ; from core import errors, retry ; from domain import models, mappings, validators ; from pages import login_page, menu_page, parametros_page, resultados_page ; from services import auth_service, navigation_service, pesquisa_service ; print('OK')"`.
  - **Smoke teste de settings sem env**: Executar `python main.py` com credenciais ausentes, confirmar ValidationError contendo "CNI_USER".
  - **Comparativo performance inicial (monólito vs novo)**: Identificar por grep os helpers JS críticos estão todos presentes (TR-5.3/TR-5.4).
- **Acceptance Criteria Addressed**: Todos AC (ciclo de verificação inicial antes do Review independente)
- **Test Requirements**:
  - `rule` TR-10.1: `py_compile` em todos os arquivos novos exit_code=0.
  - `rule` TR-10.2: `GetDiagnostics` retorna vazio.
  - `rule` TR-10.3: Smoke test import "OK" imprimido, sem ImportError/ModuleNotFound.
  - `rule` TR-10.4: Smoke test settings ausentes → ValidationError.
- **Notes**: Antes de passar para Review independente, todos TR desta tarefa devem passar.

---

## Task 11: (CONDICIONAL - Q3 Aprovado) Testes Unitários de Camada
- **Status**: `pending`
- **Priority**: medium
- **Depends On**: Task 3, Task 6; Q3 pytest aprovado
- **Description**:
  - Criar `tests/` com `__init__.py`, `test_core_errors.py`, `test_core_retry.py`, `test_domain_models.py`.
  - `test_core_errors.py`: assertivas isinstance.
  - `test_core_retry.py`: monkeypatch `time.sleep`, testar 3 attempts, progressão backoff, sucesso na 2a.
  - `test_domain_models.py`: casos TR-6.1/TR-6.2/TR-6.3 parametrizados.
  - Adicionar `pytest>=8.0` a `requirements.txt`.
- **Acceptance Criteria Addressed**: NFR-4 (solidéz retry), perfil do usuário (testes unitários)
- **Test Requirements**:
  - `rule` TR-11.1: Rodar `pytest tests/` retorna `passed` (0 falhas). Evidence: saída de terminal.
  - `rule` TR-11.2: Cobertura mínima 1 teste por classe de erro (6) + 2 para retry (falha/sucesso) + 3 para models (válido/inválido/mês_inválido). Evidence: contagem de `def test_`.
- **Notes**: Tarefa cancelável se Q3 = Não (manter sem testes).
