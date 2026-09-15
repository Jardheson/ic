# Refatoração Arquitetural Automação CNI - Product Requirements Document

## Overview
- **Summary**: Refatoração completa do monólito `main.py` (~2900 linhas) em uma arquitetura em camadas seguindo Clean Code, SOLID, Design Patterns, Separação de Preocupações e Padrão Page Object Model (POM). O objetivo é substituir o arquivo monolítico por módulos coesos, desacoplados, tipados, com hierarquia de erros robusta, tratamento de retry/backoff, validações rigorosas e configuração externalizada.
- **Purpose**: O código atual, embora funcional, apresenta: (1) estado global mutável (`driver`, `actions`, `wait` em nível de módulo); (2) mistura de responsabilidades (setup driver, autenticação, navegação, manipulação de UI, lógica de domínio, orquestração do pipeline em um único arquivo); (3) ausência de type hints; (4) credenciais hardcoded em texto plano; (5) ausência de hierarquia de erros tratável; (6) Nenhum mecanismo padronizado de retry/backoff; (7) constantes, IDs e mappings espalhados por todo o fluxo orquestral; (8) dificuldade de manutenção e testabilidade.
- **Target Users**: Jardheson Oliveira (Arquiteto de Software Sênior / Desenvolvedor Full Stack) — usuário único e mantenedor direto do código; equipe de Engenharia de Dados que consome os outputs.

## Goals
1. **G1 - Arquitetura em Camadas**: Estruturar o projeto em camadas claras: Core (cross-cutting) → Infrastructure (browser/driver) → Domain (models/validators/mappings) → Services (casos de uso orquestrais) → Presentation/Pages (Page Object Model encapsulando interação com UI da CNI) → Entry Point (`main.py` fino, delegando).
2. **G2 - Remover Estado Global**: Eliminar variáveis globais `driver`, `actions`, `wait`, `short_wait`, `ultra_short_wait`; driver deve ser injetado como dependência e gerenciado por um ciclo de vida explícito.
3. **G3 - Tipagem Estrita**: Adicionar type hints em 100% das assinaturas de função, parâmetros de entrada/saída, models de domínio e configurações.
4. **G4 - Hierarquia de Erros + Retry/Backoff**: Implementar `AppError` base com subclasses (`RetryableError`, `TimeoutError`, `ValidationError`, `BrowserError`, `NavigationError`). Implementar decorator/engine `with_retry` com exponential backoff e jitter para ações transitórias.
5. **G5 - Configuração Externalizada**: Credenciais, perfis de espera, locators estáticos, mappings de variáveis (VAR_COD_POR_VALUE) e constantes desacopladas do fluxo. Oferecer `.env.example` + carregamento via `python-dotenv`.
6. **G6 - Page Object Model (POM)**: Cada tela da UI CNI encapsulada em um Page Object com métodos de ação, locators privados e sem `print` nem orquestração (Pages são ignorantes do pipeline).
7. **G7 - Orquestração de Pipeline em Camada de Serviço**: As 4 FASES (Autenticação → Navegação → Preenchimento Filtros → Exportação) devem ser expostas como métodos em Services dedicados, sem lógica de interação direta com Selenium neles.
8. **G8 - Compatibilidade Funcional 100%**: Ao rodar o novo entry point, o comportamento funcional DEVE ser idêntico ao código atual. Nenhuma regra de negócio, ordem de preenchimento (Filtros → Estrato → Variáveis → Radios), valores default, mapeamento de códigos de variável ou timings otimizados aplicados em rodadas anteriores podem ser alterados sem aprovação.

## Non-Goals
1. **NG1 - NÃO** alterar a lógica de negócio da automação: valores de preenchimento (Ceará 634, Junho 5, 2026, 4 variáveis 955/956/957/958, radio 21 Frequência, true Valor, LINHA, etc.) permanecem exatamente os mesmos.
2. **NG2 - NÃO** reescrever a engine de espera `aguardar_pagina_pronta` do zero; ela deve ser movida e integrada intacta (com os perfis recentemente otimizados) para `infrastructure/browser/waits.py`.
3. **NG3 - NÃO** introduzir AsyncIO ou refatorar para `async`/`await`; manter execução síncrona compatível com Selenium 4.x.
4. **NG4 - NÃO** introduzir novos frameworks de teste ou testes de UI/E2E; foco em testes unitários de camada (domain/services/utils).
5. **NG5 - NÃO** alterar a plataforma/browser: permanece Chrome maximizado via `webdriver.Chrome()` padrão.
6. **NG6 - NÃO** inventar novas telas, novas fases, novas variáveis ou novas funcionalidades que não existiam no monólito original.

## Background & Context
- Código atual: `g:\ic\main.py` (2800-2900 linhas). Único arquivo. 43+ funções nível módulo. Estado global: `driver`, `actions`, `wait`, `short_wait`, `ultra_short_wait`, `_PERFIS`.
- Fluxo pipeline atual (confirmado em rodadas anteriores): FASE 1 Autenticação (`fazer_login_turbo`) → FASE 1.2 Render pós-login → FASE 2 Navegação Menus (Sondagem Industrial → Consultas → Resultados/Índices → Federação → link "Por Atividade") → FASE 3 Parâmetros (5 filtros → 3.2 Estrato → 3.1 Variáveis → Radios (TipoEstimativa/Exibição) → 3.4 Orientação) → FASE 4 Export Excel.
- Regra de negócio IMPOSTA PELO USUÁRIO em mensagem anterior (hard constraint): Ordem FASE 3 RÍGIDA: Filtros → PRIMEIRO ESTRATO (3.2) → DEPOIS VARIÁVEIS (3.1) → DEPOIS RADIOS (3.3) → DEPOIS ORIENTAÇÃO (3.4) → FASE 4.
- Otimizações de performance aplicadas em rodadas anteriores (ativas, NÃO alterar): JS nativo em `selecionar_valor` e `valor_campo_jah_correto` (contornar bug option vazio topo); `_ajustar_checkboxes_js` em lote (0.01s para TODOS checkboxes); helper `marcar_radiobutton_primefaces` com diagnóstico automático; locators `By.ID` preferencialmente para IDs com `:`; `_locator_to_css` com escape regex; perfis `_PERFIS` otimizados e polling reduzido; `esperar_estavel` janela 0.08s.
- Dependências atuais (ambiente venv `g:\ic\.venv\`): Python 3.14.3, Selenium 4.49.0. `requirements.txt` NÃO existe.
- Restrição "NÃO INVENTE" do perfil do usuário: Qualquer decisão arquitetural que não esteja 100% lastreada no código atual e nas preferências do perfil é marcada como Open Question abaixo.

## Functional Requirements
- **FR-1**: O novo entry point `main.py` deve, ao ser executado (`python main.py`), reproduzir exatamente o mesmo pipeline de automação do monólito original (Login → Menus → Por Atividade → Parâmetros → Pesquisar → Export Excel), sem regressão funcional.
- **FR-2**: A criação, configuração e destruição do `webdriver.Chrome()` devem ser encapsuladas em um gerenciador de ciclo de vida (`BrowserDriver` class com `__enter__`/`__exit__` ou factory `create_driver()` + `teardown()`).
- **FR-3**: As constantes da UI (IDs JSF, values de radio, `VAR_COD_POR_VALUE`, `_PERFIS`, preferências de labels Estrato) devem ser movidas para módulos `config/constants.py` e `domain/mappings.py` respectivamente, sem qualquer presença no fluxo orquestral principal.
- **FR-4**: Credenciais `SEU_USUARIO` / `SUA_SENHA` NÃO podem mais estar hardcoded no código; devem ser lidas de variáveis de ambiente (`CNI_USER`, `CNI_PASSWORD`), com fallback a `.env` via `python-dotenv`. Validação de presença no startup; `ValidationError` se ausentes.
- **FR-5**: Cada tela/fluxo da UI deve ter um Page Object: `LoginPage`, `MenuPage`, `ParametrosPage`, `ResultadosPage`. Cada um deve receber o driver via construtor, expor métodos de alto nível (ex: `LoginPage.logar(user, senha)`) e manter seus locators como atributos privados de classe.
- **FR-6**: Actions de browser (clicar, hover, preencher texto, selecionar select, marcar radio, abrir/fechar painel scbmenu, ajustar checkboxes js) devem estar em módulos de infraestrutura (`infrastructure/browser/actions.py`) recebendo driver como primeiro argumento, sem uso de estado global.
- **FR-7**: Engine de espera `aguardar_pagina_pronta`, `aguardar_ajax`, `esperar_estavel`, `aguardar_navegacao`, `_limpar_overlays_orphans`, `_PERFIS` devem ser movidas intactas para `infrastructure/browser/waits.py`, adaptadas apenas para receber driver explícito e acessar `_PERFIS` de `config/constants.py`.
- **FR-8**: A hierarquia de exceções deve permitir distinguir: (a) erros transitórios passíveis de retry (`RetryableError` subclasse AppError); (b) timeout de espera (`TimeoutError` subclasse RetryableError); (c) erro de validação (domínio/credenciais, `ValidationError` subclasse AppError, NÃO retryable); (d) erro de navegador/DOM (BrowserError); (e) erro de navegação/fluxo (NavigationError).
- **FR-9**: Implementar decorator `@with_retry(max_attempts=3, initial_delay=0.05, backoff=2.0, jitter=0.02, retry_on=(RetryableError, StaleElementReferenceException, ElementNotInteractableException))` que aplica exponential backoff+jitter em ações passíveis de falha transitória, e propagar exceção original após última tentativa.
- **FR-10**: Models de domínio tipados via dataclass: `PesquisaParams` (Coorte, mesInicio, anoInicio, mesFim, anoFim, CodigosVariaveis desejados, TipoEstimativa, Exibicao, Orientacao). `PesquisaParams` deve ter validadores embutidos.
- **FR-11**: Arquivo `requirements.txt` deve ser criado listando todas as dependências do projeto, com pins compatíveis ao ambiente atual: `selenium==4.49.0`, `python-dotenv>=1.0.0`, e (se aprovado) `pydantic>=2.0.0` para validações tipadas.
- **FR-12**: O arquivo `.env.example` deve conter `CNI_USER=` e `CNI_PASSWORD=` com comentário explicativo, NUNCA com valores reais.
- **FR-13**: O `main.py` antigo deve ser preservado como `main_monolith_backup.py` (não executado, só histórico) antes da substituição; nenhum código é perdido.

## Non-Functional Requirements
- **NFR-1 - Type Hints**: 100% das funções, métodos, parâmetros, retornos e models públicos devem ter type hints. Uso de `from __future__ import annotations` para referências forward, `typing.Optional` (Python 3.14.3).
- **NFR-2 - Coesão e Acoplamento**: Cada módulo deve ter < 3 responsabilidades. Métrica: Classes/funções por arquivo < 15 (exceto Page Objects e helpers de ações agrupados).
- **NFR-3 - Legibilidade Clean Code**: Nomes autoexplicativos, sem abreviações ambíguas. Funções < 80 linhas exceto casos justificados (execute_script grande em `_ajustar_checkboxes_js`).
- **NFR-4 - Solidez Retry/Backoff**: Decorator `with_retry` aplicado em no mínimo: `clicar_com_retry` e equivalentes Page Object, `fazer_login_turbo`, `clicar_por_atividade_turbo` e passos de navegação menu com hover suscetíveis a StaleElement.
- **NFR-5 - Sem Regressão Performance**: Tempo total de execução do pipeline novo NÃO pode exceder em mais de 5% o tempo do código atual (medido após 3 execuções de referência). Os gains dos helpers JS em lote NÃO podem ser perdidos.
- **NFR-6 - Segurança Credenciais**: Nenhum `print` ou `logging` de mensagens pode logar a senha real. Valores sensíveis passados como `**masked` em logs de erro.
- **NFR-7 - Portabilidade**: Toda manipulação de path deve usar `pathlib.Path` (não concatenação de string hardcoded separador Windows).
- **NFR-8 - Compatibilidade Compilação**: Todo módulo novo deve passar `python -m py_compile` sem warnings.
- **NFR-9 - Fácil Rastreabilidade**: Matriz de cobertura AC → Tasks deve existir em `tasks.md`, permitindo auditar qual tarefa entrega qual requisito.

## Constraints
- **Technical-C1**: Ambiente de execução: Windows 10/11, Python 3.14.x, Selenium 4.x (pin compatível). Não há Docker nem headless.
- **Technical-C2**: Permanecer em Python Selenium síncrono; NÃO Playwright, NÃO Requests/HTTP direto (UI da CNI usa PrimeFaces/JSF com AJAX dependente de sessão de navegador).
- **Technical-C3**: Manter intactos os blocos JS críticos de performance (early return JS selected value, `_ajustar_checkboxes_js` em lote, diagnósticos radios, `Function.call` no onclick "Por Atividade"); podem ser movidos mas NÃO alterados em comportamento.
- **Business-C1**: Ordem FASE 3 e regras de preenchimento são hard constraints impostas pelo usuário. QUALQUER desvio resulta em regressão inaceitável.
- **Business-C2**: Hard constraint IDs JSF com `:` → SEMPRE `By.ID`, NUNCA `By.CSS_SELECTOR #campo:id` (pseudo-seletor). Todos os helpers/locators nos novos Page Objects devem seguir isso.
- **Dependencies-C1**: Atualmente só `selenium==4.49.0` está instalado no `.venv`. Quaisquer novas dependências (ex: `python-dotenv`, `pydantic`) estão listadas como Open Questions e só entram após aprovação.
- **Dependencies-C2**: NÃO se pode usar bibliotecas que alterem drasticamente a arquitetura (ex: `seleniumbase`, `webdriver_manager` custom driver download); persistir `webdriver.Chrome()` padrão.

## Assumptions
- **A1**: A introdução de `python-dotenv` é um requisito de segurança razoável para remover hardcoded de credenciais e está alinhado com as preferências do usuário (validações rigorosas).
- **A2**: A introdução de `pydantic` para models de domínio validados tipadamente (acoplado a preferência Zod/Pydantic do perfil) é desejável, mas foi marcada como Open Question Q1 para evitar instalar biblioteca sem aprovação. Como fallback de mínimo impacto, usamos `@dataclass` + `__post_init__` validadores built-in (sem nova dependência).
- **A3**: O `print` estruturado com emojis (`✅/⏭/⚠️/❌/ℹ️`) e `flush=True` do código atual é o logging padrão desejado. Não substituímos por `logging.INFO` em nenhum pipeline; a camada de services pode oferecer `verbose=True`/callback opcional no futuro.
- **A4**: O usuário deseja 100% compatibilidade com o código de otimização de performance da última rodada; por isso todos os helpers JS e waits otimizados são movidos INALTERADOS.

## Acceptance Criteria

### AC-1: Arquitetura em Camadas e Estrutura de Diretórios Presente
- **Type**: `rule`
- **Given**: O código foi refatorado.
- **When**: Listamos o diretório `g:\ic\` e seus submódulos (excluindo `.venv/` e `__pycache__/`).
- **Then**: Devem existir os arquivos e diretórios: `main.py` (entry point novo < 200 linhas), `requirements.txt`, `.env.example`, `config/` (settings + constants), `core/` (errors + retry), `infrastructure/browser/` (driver + waits + actions), `domain/` (models + mappings + validators), `services/` (auth + navigation + pesquisa), `pages/` (4 Page Objects), `main_monolith_backup.py` (backup).
- **Pass Condition**: Todos os 14 itens acima existem e passam `py_compile`.
- **Evidence**: `LS g:\ic` + `Get-ChildItem -Recurse -Directory` e resultado `python -m py_compile main.py config/*.py core/*.py infrastructure/*/*.py domain/*.py services/*.py pages/*.py` == 0.

### AC-2: Nenhuma Variável Global de Driver/Waits/Actions
- **Type**: `rule`
- **Given**: Código refatorado.
- **When**: Aplicamos `Grep` por `^driver =|^actions =|^wait =|^short_wait =|^ultra_short_wait =` em nível módulo em todos os arquivos Python exceto backup.
- **Then**: Nenhum match encontrado. Driver/Waits/Actions só podem existir como atributos de classe, parâmetros ou variáveis locais.
- **Pass Condition**: 0 matches fora de `main_monolith_backup.py`.
- **Evidence**: Saída `Grep pattern=^driver =|^actions =|^wait =|^short_wait =|^ultra_short_wait =` com 0 matches nos módulos novos.

### AC-3: Credenciais São Carregadas de Variáveis de Ambiente e Validadas
- **Type**: `rule`
- **Given**: Código refatorado, `.env` ausente e `CNI_USER`/`CNI_PASSWORD` ausentes no env.
- **When**: Executamos `python main.py`.
- **Then**: Startup aborta com `ValidationError` contendo mensagem clara de credenciais ausentes, e NÃO expõe stack trace confuso de Selenium.
- **Pass Condition**: Retorno c/ `ValidationError` e mensagem contendo "CNI_USER" e "CNI_PASSWORD".
- **Evidence**: Sessão de terminal reproduzindo cenário + saída.

### AC-4: Page Objects Existem e Não Expõem Locators Fora da Classe
- **Type**: `rule`
- **Given**: Código refatorado.
- **When**: Inspecionamos `pages/*.py`.
- **Then**: 4 classes `LoginPage`, `MenuPage`, `ParametrosPage`, `ResultadosPage` existem; cada recebe driver via `__init__(self, driver)` e armazena em `self._driver`; locators são atributos de classe privados (`_LOCATOR_XXX` ou `By.ID + ID` no corpo do método); nenhum arquivo `services/` importa `By` ou chama `driver.find_element` diretamente (todas as interações UI passam por Pages).
- **Pass Condition**: Classes 4/4 existem + pattern de locators privados + services NÃO importam `By` / NÃO chamam `find_element`.
- **Evidence**: Inspeção `Read` dos arquivos pages + grep services por `By\.` e `find_element` = 0.

### AC-5: Hierarquia de Erros AppError e Decorator Retry com Backoff
- **Type**: `rule`
- **Given**: Código refatorado, `core/errors.py` e `core/retry.py`.
- **When**: Inspecionamos e testamos um cenário de retry simulado.
- **Then**: Hierarquia `AppError(Exception)` com subclasses `RetryableError(AppError)`, `ValidationError(AppError)`, `BrowserError(RetryableError)`, `TimeoutError(RetryableError)`, `NavigationError(AppError)` existe. Decorator `with_retry(...)` aplica backoff exponencial + jitter, re-lança última exceção após `max_attempts`.
- **Pass Condition**: Todas as classes existem + `@with_retry` aplicado em no mínimo 3 ações transitórias (clique retry, login, clique Por Atividade) + teste unitário pass (ou teste em memória que 3 tentativas ocorrem).
- **Evidence**: Read `core/errors.py`, `core/retry.py` + usos via grep.

### AC-6: Models Tipada `PesquisaParams` e Validações
- **Type**: `rule`
- **Given**: Código refatorado.
- **When**: Instanciamos `PesquisaParams` com valores válidos e com valores inválidos (ex: `mesInicio = 13`, `anoInicio = "abcd"`).
- **Then**: Valores válidos → objeto criado sem erro. Valores inválidos → `ValidationError` explicativo lançado imediatamente.
- **Pass Condition**: 2 casos de teste: (a) params válidos passa; (b) params inválidos levanta ValidationError específico.
- **Evidence**: Snippet de execução dos dois casos.

### AC-7: Orquestração Pipeline em Services (4 FASES) Sem Lógica UI Direta
- **Type**: `rule`
- **Given**: Código refatorado.
- **When**: Inspecionamos `services/auth_service.py`, `services/navigation_service.py`, `services/pesquisa_service.py`.
- **Then**: Métodos de alto nível existem: `AuthService.logar(user, senha)`, `NavigationService.navegar_ate_parametros_por_atividade()` → bool, `PesquisaService.executar_pesquisa(params: PesquisaParams)` → path download. Nenhum desses métodos chama `By.ID`, `find_element`, `Select`, Keys etc. diretamente (apenas delega para Page Objects e infra).
- **Pass Condition**: 3 services existem com métodos acima e nenhum import de `By`/Selenium Webdriver expected_conditions dentro de services/.
- **Evidence**: Read arquivos services + grep por selenium imports dentro de services (exceto tipos de exceções).

### AC-8: Compatibilidade Funcional 100% (Regressão Zero)
- **Type**: `rubric`
- **Dimension**: Paridade funcional com o monólito original
- **Scale**: 1-5
- **Anchors**: 1 = pipeline trava em uma das fases e não produz output Excel; 2 = algumas fases executam, mas output Excel é gerado com conteúdo diferente ou vazio; 3 = pipeline termina sem exception, mas valores preenchidos diferem (ex: variáveis marcadas erradas, rádios errados, orientação COLUNA); 4 = pipeline idêntico funcionalmente, ordem correta, tudo preenchido certo, Excel gerado igual, porém com pequeno overhead de tempo 5% < overhead <= 15%; 5 = comportamento idêntico em 100% dos detalhes + overhead de tempo <= 5% vs. o monólito.
- **Pass Threshold**: >= 4
- **Evidence**: Log das 4 fases executadas (antes → backup, depois → novo) + artefato Excel de ambos comparados em conteúdo + tempos por fase registrados.

### AC-9: Cobertura Type Hints 100% em APIs Públicas
- **Type**: `rubric`
- **Dimension**: Proporção de type hints em assinaturas públicas
- **Scale**: 1-5
- **Anchors**: 1 = < 30% funções tipadas; 2 = 30-55%; 3 = 55-80%; 4 = 80-95% com poucas funções internas de helper não tipadas; 5 = 100% funções, métodos, parâmetros, retornos e models públicos tipados.
- **Pass Threshold**: >= 4
- **Evidence**: Relatório de inspeção de todos os arquivos novos, contando funções tipadas / total.

### AC-10: Preservação de Otimizações Performance (Gains JS Não Perdidos)
- **Type**: `rubric`
- **Dimension**: Fidelidade na migração dos helpers otimizados (JS em lote, early returns, perfis)
- **Scale**: 1-5
- **Anchors**: 1 = mais de 2 helpers otimizados foram perdidos/alterados e gargalos de 56s em mesInicio voltaram + checkboxes voltaram a ser clicar_com_retry item a item; 2 = pelo menos um helper JS crítico foi alterado em comportamento e afeta performance > 10%; 3 = helpers movidos intactos, mas small regressions 5-10% por overhead de POM; 4 = helpers todos intactos, perfis e polling inalterados, perda <= 5% (aceitável por overhead de classes); 5 = helpers intactos e até ganhos adicionais de composição (perda 0% ou negativa = mais rápido ainda).
- **Pass Threshold**: >= 4
- **Evidence**: Identificação por grep de helpers (selecionar_valor JS early return, `_ajustar_checkboxes_js`, `valor_campo_jah_correto` JS, `marcar_radiobutton_primefaces` diagnóstico, `clicar_por_atividade_turbo` Function.call) todos presentes nos novos locais com código JS idêntico.

## Open Questions
- [ ] **Q1 (Dependencies)**: Instalar `pydantic>=2.0.0` para models e validações tipadas de `PesquisaParams` (preferência Zod/Pydantic do perfil)? **Alternativa Built-In de fallback**: usar `@dataclass` + `__post_init__` validadores manuais (sem nova dependência, mas menos elegante). Recomendação: **Instalar Pydantic (Recomendado)**.
- [ ] **Q2 (Logging)**: Substituir `print(..., flush=True)` com emojis pelo módulo padrão `logging` (formatter customizado mantendo emojis e cores)? **Alternativa Built-In**: manter `print` estruturado igual hoje. Recomendação: **Manter prints (atual) por agora**, evitando inventar comportamento.
- [ ] **Q3 (Testes Unitários)**: Criar testes unitários para `core.errors`, `core.retry`, `domain.validators`, `domain.mappings` com `pytest` (instalar pytest)? **Alternativa Built-In**: Sem testes unitários por enquanto, só validação `py_compile` + comparação logs. Recomendação: **pytest (Recomendado)**, pois perfil do usuário exige "cobertura de testes unitários".
- [ ] **Q4 (Driver Manager)**: Instalar `webdriver-manager` para resolver automaticamente versão do ChromeDriver (em vez de depender da compatibilidade padrão do Selenium 4.6+)? Alternativa: manter `webdriver.Chrome()` default (já funciona no ambiente). Recomendação: **NÃO instalar**, pois `selenium 4.49` já gerencia driver e adicionar dependências é risco.
- [ ] **Q5 (Config Adicional em .env)**: Externalizar também a URL base, timeout do Chrome, e flags maximizado? Ou manter hardcoded default em `config/constants.py` como readonly? Recomendação: **Externalizar só credenciais agora**, demais constantes ficam em `config/constants.py` (melhor simplicidade).
