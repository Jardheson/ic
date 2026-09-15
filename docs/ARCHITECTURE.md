# Arquitetura: Clean Architecture + Page Object Model (7 Camadas)

> Projeto construído seguindo **Clean Architecture** (Uncle Bob) + **SOLID** + **DDD tático** + **Page Object Model (POM)**.
> Saiba mais em: [README.md](file:///g:/ic/README.md) | [CONTRIBUTING.md](file:///g:/ic/docs/CONTRIBUTING.md)

---

## 1. Diagrama Textual das 7 Camadas (Dependência SEMPRE Inward)

```mermaid
flowchart TD
    A[main.py<br/>(Entry Point Fino <200L)] --> B[Services<br/>(Casos de Uso<br/>@with_retry ≥3)]
    B --> C[Pages<br/>(Page Object Model<br/>Locators PRIVADOS)]
    B --> D[Domain<br/>(Entidades + Regras<br/>Selenium-Free)]
    B --> E[Config<br/>(Pydantic .env<br/>+ Constants IDs)]
    B --> F[Core<br/>(Errors + Retry + Sec + Lock)]
    C --> G[Infrastructure<br/>(Selenium Driver,<br/>Waits, Actions JS)]
    G --> F

    style A fill:#3b82f6,stroke:#1e40af,color:#fff
    style B fill:#6366f1,stroke:#3730a3,color:#fff
    style C fill:#8b5cf6,stroke:#5b21b6,color:#fff
    style D fill:#10b981,stroke:#065f46,color:#fff
    style E fill:#f59e0b,stroke:#92400e,color:#111
    style F fill:#ef4444,stroke:#991b1b,color:#fff
    style G fill:#0ea5e9,stroke:#075985,color:#fff
```

---

## 2. Responsabilidades Por Camada

### 2.1 `config/` — Configuração (Família mais externa)
**Depende de:** nada (interno, só Pydantic + python-dotenv)

| Arquivo | Responsabilidade |
|---|---|
| [settings.py](file:///g:/ic/config/settings.py) | `CfgSettings` (Pydantic BaseSettings) → carrega `.env` fail-fast. Valida permissões do arquivo `.env` (SEG-5). Sanitiza mensagens ValidationError. |
| [constants.py](file:///g:/ic/config/constants.py) | IDs PrimeFaces 100% extraídos do DOM, mapeamentos padrão (Coorte=634, mai/2026 → jul/2026), 15 variáveis padrão, URL Whitelist, Watchdog 60min. |

**Regra rígida:** Qualquer ID JSF novo é adicionado AQUI. NUNCA hard-coded em Pages/Services.

---

### 2.2 `core/` — Fundamentos Cross-Cutting
**Depende de:** Nada (biblioteca padrão só)

| Arquivo | Responsabilidade |
|---|---|
| [errors.py](file:///g:/ic/core/errors.py) | Hierarquia: `AppError` (base) → `RetryableError` → `BrowserError` / `TimeoutError`; `NavigationError` (não-retry) → `AppError`. |
| [retry.py](file:///g:/ic/core/retry.py) | Decorator `@with_retry(tentativas=3, delay_start=1.0, backoff=2.0, jitter, retry_types=(RetryableError,))`. Aplica exponential backoff + jitter. |
| [security.py](file:///g:/ic/core/security.py) | 4 funções SEG: `sanitize_log_message()` (keywords regex), `assert_url_whitelist()` (hostname + subdomínios), `check_env_file_permissions()` (POSIX 0600 / Windows ACL advapi32), `start_watchdog/check_watchdog/watchdog_remaining_s()` (monotônico). |
| [lock.py](file:///g:/ic/core/lock.py) | `SingleInstanceLock` cross-platform com 3 estratégias: Windows `msvcrt.locking` → POSIX `fcntl.flock` → Fallback arquivo PID `O_CREAT|O_EXCL`. Context manager `__enter__/__exit__`. |

---

### 2.3 `domain/` — Entidades e Regras de Domínio
**Depende de:** `core/` (validações)  
**Garantia rígida:** NENHUM import Selenium / By / find_element. Camada 100% testável offline.

| Arquivo | Responsabilidade |
|---|---|
| [models.py](file:///g:/ic/domain/models.py) | `PesquisaParams` (Pydantic frozen). Campos: `coorte, mes_inicio, ano_inicio, mes_fim, ano_fim, codigos_variaveis, tipo_estimativa, exibicao, orientacao`. Todos validators acoplados. |
| [validators.py](file:///g:/ic/domain/validators.py) | Funções puras: `validar_mes(1..12)`, `validar_ano(2010..2100)`, `validar_coorte(not empty)`, `validar_codigos_variaveis(not empty)`, `validar_orientacao(LINHA\|COLUNA)`. |
| [mappings.py](file:///g:/ic/domain/mappings.py) | `VAR_COD_POR_VALUE` ← mapa INVERTÍVEL de 31 values reais checkbox → 31 códigos internos. `codigos_para_values([codigo,...])` → `[value_real, ...]` (usado por parametros_page). |

---

### 2.4 `infrastructure/browser/` — Driver Técnico Selenium
**Depende de:** `core/` (errors, retry), Selenium 4.49  
**Responsabilidade:** Detalhes técnicos de automação browser. NÃO contém lógica de negócio.

| Arquivo | Responsabilidade |
|---|---|
| [driver.py](file:///g:/ic/infrastructure/browser/driver.py) | `create_driver(headless: bool)` → Chrome com options custom (disable-infobars, sandbox, downloads padrão); `teardown_driver(driver)` → quit seguro com try/except. |
| [waits.py](file:///g:/ic/infrastructure/browser/waits.py) | 6 perfis polling: `aguardar_pagina_pronta(modo=leve/normal/pesado)`, `aguardar_navegacao()`, `aguardar_ajax_idle()`, overlay PrimeFaces, hash change. **Função `passo(driver, titulo, fn: Callable, *args, modo_antes, modo_depois)`:** wrapper obrigatório que valida `fn` é callable (previne TypeError). |
| [actions.py](file:///g:/ic/infrastructure/browser/actions.py) | **Batch helpers JS PrimeFaces:** `_ajustar_checkboxes_js(modo=lista_valores/todas/preferencia, arguments[0..3] SEGURO)`, `marcar_radiobutton_primefaces(descobre NAME real via JS, fallback click visual)`, `abrir_selectcheckboxmenu_primefaces`, `fechar_painel_selectcheckboxmenu`, `selecionar_valor`, `valor_campo_jah_correto` (early return nativo JS evita 56s!). |

---

### 2.5 `pages/` — Page Object Model (POM)
**Depende de:** `infrastructure/browser/*`, `config/constants`, `domain/mappings`

| Regra rígida do POM | Status |
|---|---|
| Todos locators são **PRIVADOS** (`_LOCATOR_*`) → tuplas `(By.ID, "...")` 
| Services NÃO importam `By` / `find_element` — só métodos Page de alto nível 
| Nenhuma regra de negócio; só interação UI mapeada 
| By.ID para IDs com `:` (evita escape manual) 
| Arquivo | Métodos Públicos |
|---|---|
| [base_page.py](file:///g:/ic/pages/base_page.py) | Construtor recebe driver; encapsulamento comum. |
| [login_page.py](file:///g:/ic/pages/login_page.py) | `preencher_login(user, pwd)`, `clicar_entrar()` |
| [menu_page.py](file:///g:/ic/pages/menu_page.py) | Métodos hover + clique dos menus de navegação. |
| [parametros_page.py](file:///g:/ic/pages/parametros_page.py) | `preencher_5_filtros_basicos()`, `_preencher_estrato()`, **`preencher_variaveis(lista_codigos)` (interseção defaults + valida tokens 2x)**, `_validar_tokens_variaveis()`, `marcar_tipo_estimativa()`, `marcar_exibicao()`, `marcar_orientacao()`, `clicar_pesquisar()` |
| [resultados_page.py](file:///g:/ic/pages/resultados_page.py) | `aguardar_datatable(timeout)`, `clicar_exportar_excel()` |

---

### 2.6 `services/` — Casos de Uso (Orquestração)
**Depende de:** `pages/*`, `domain/models`, `core/retry`, `core/errors`, `config/settings`

| Regras rígidas | Status |
|---|---|
| Todo método público decorado com `@with_retry ≥ 3` 
| **NUNCA** importa `By` / `find_element` / `Select` — só delega a Pages 
| Ordem rígida FASE 3 IMPOSTA dentro de `PesquisaService` (não no main) 

| Arquivo | Responsabilidade |
|---|---|
| [auth_service.py](file:///g:/ic/services/auth_service.py) | FASE 1.2: `logar(user, pwd)` → (ok: bool, msg: str). Orquestra LoginPage + espera pós-login. |
| [navigation_service.py](file:///g:/ic/services/navigation_service.py) | FASE 2: `navegar_para_form_parametros()` → bool. Orquestra 5 passos menu (hover + Por Atividade). |
| [pesquisa_service.py](file:///g:/ic/services/pesquisa_service.py) | FASE 3 + FASE 4: `pesquisar_exportar_excel()` → bool. Executa **ordem OBRIGATÓRIA**: 5 filtros → Estrato → Variáveis → Radios → Orientação → Pesquisar → Datatable → Export Excel. |

---

### 2.7 `main.py` — Entry Point (Camada Mais Externa)
**Depende de:** TUDO (é o composition root)
**Regra rígida:** `< 200 linhas`. NÃO contém lógica de negócio. Só orquestra flow FASE 0→4 + limpeza recursos.

```
main()
├─ with SingleInstanceLock(lock_path)  [SEG-6]
│  ├─ start_watchdog(3600s)            [SEG-3]
│  ├─ _fase0_carregar_settings fail-fast
│  ├─ create_driver
│  ├─ try:
│  │   ├─ driver.get + assert_url_whitelist [SEG-2]
│  │   ├─ check_watchdog + AuthService.logar + assert_whitelist
│  │   ├─ check_watchdog + NavigationService + assert_whitelist
│  │   ├─ check_watchdog + PesquisaService.pesquisar_exportar_excel + assert_whitelist
│  │   └─ print SUCESSO
│  ├─ finally:
│  │   └─ teardown_driver
│  └─ except Exception → sanitize_log_message(msg + repr)  [SEG-4]
└─ print SUCESSO / FALHA
```

---

## 3. Princípios SOLID Aplicados

| Princípio | Aplicação Prática |
|---|---|
| **SRP — Single Responsibility** | Cada camada/arquivo tem 1 responsabilidade única. `PesquisaParams` = dados; `retry.py` = retry; `PesquisaService` = orquestra Fase3+4 só. |
| **OCP — Open/Closed** | Novo caso de uso = novo arquivo em `services/` (não edita services existentes). Nova variável = adicionar em constants/mappings. |
| **LSP — Liskov Substitution** | `RetryableError`/`NavigationError` são `AppError` e substituem sem quebrar. `SingleInstanceLock` funciona com msvcrt/fcntl/fallback sem mudar caller. |
| **ISP — Interface Segregation** | Pages expõem só métodos de alto nível (services não enxergam locators). `@with_retry` só aceita `retry_types` explícitos. |
| **DIP — Dependency Inversion** | Services dependem de abstrações (interfaces Page) não de Selenium concreto. `core/` não depende de nenhuma camada acima. |

---

## 4. Fluxo de Dados Pipeline (Fase 0 → 4)

```
FASE 0
  get_settings()
    ├─ Pydantic valida CNI_USER/CNI_PASSWORD preenchidos
    ├─ check_env_file_permissions(SEG-5) → WARNING se world-readable
    └─ retorna CfgSettings
          ↓
FASE 1
  create_driver(headless=False)
  driver.get(URL_BASE_LOGIN)
  assert_url_whitelist(pesquisasconjunturais.cni.com.br)  [SEG-2]
  AuthService.logar() @with_retry(3)
    ├─ LoginPage.preencher_login
    ├─ LoginPage.clicar_entrar
    └─ espera pós-login
  assert_url_whitelist
          ↓
FASE 2
  check_watchdog("login") [SEG-3]
  NavigationService.navegar_para_form_parametros() @with_retry(3)
    └─ MenuPage (5 passos hover + Por Atividade)
  assert_url_whitelist
          ↓
FASE 3 (ORDEM IMPOSTA)
  check_watchdog("navegacao")
  ParametrosPage.preencher_5_filtros_basicos()
    → Coorte(634) → Mês Início(5) → Ano Início(2026) → Mês Fim(7) → Ano Fim(2026)
  ParametrosPage._preencher_estrato()
    → Espera AJAX OBRIGATÓRIA
  ParametrosPage.preencher_variaveis(15 codigos)
    → (a) defaults interseção? 15/15? ok pula
    → (b) senão abre painel → _ajustar_checkboxes_js(lista_valores, arguments seguro)
    → (c) fecha painel → _validar_tokens_variaveis() [FONTE VERDADE VISUAL]
    → (d) faltou? reabre, remarca forcado (max 2x)
  ParametrosPage marcar TipoEstimativa → Exibição → Orientação
  ParametrosPage.clicar_pesquisar()
          ↓
FASE 4
  check_watchdog("pesquisa+export")
  ResultadosPage.aguardar_datatable()
  ResultadosPage.clicar_exportar_excel()
  assert_url_whitelist
          ↓
SUCESSO → Excel baixado na pasta Downloads
```

---

## 5. Hard Constraints Não Negociáveis

1. **Ordem FASE 3:** 5 filtros → Estrato → Variáveis → Radios → Orientação. **NUNCA inverter.**
2. **`passo(fn: Callable)`:** espera.py exige argumento posicional `fn` callable. Chamadas sem `fn` levantam `TypeError`.
3. **By.ID para campos `:`:** IDs JSF com `selectForm:XXX` usam `By.ID`. `By.CSS_SELECTOR` exige escape `\\:`.
4. **Services sem Selenium:** Nenhum `services/*.py` importa `By` / `find_element` / `Select`.
5. **`@with_retry ≥ 3`:** Todo método público de `services` tem pelo menos 3 tentativas.
6. **`PesquisaParams` frozen:** Imutável. Nenhuma alteração depois de construído; validações Pydantic rodam no __init__.
7. **Credenciais:** NÃO logar valores reais de `CNI_PASSWORD` / etc. Toda exceção no main passa por `sanitize_log_message()`.
8. **Padrão de 15 variáveis (p1..p11):** Sempre exatas 15. Nenhuma a mais, nenhuma a menos.
