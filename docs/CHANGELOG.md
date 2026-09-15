# Changelog

Todas as mudanças importantes deste projeto são documentadas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
padrão [Conventional Commits](file:///g:/ic/docs/CONTRIBUTING.md) e versão calendário (YYYY.MM.DD).

---

## [2026.09.15b] — Melhoria Variáveis (15 exatas) + Segurança 6 Pilares

### Melhorias Principais do Dia (maior release até agora)
- **Correção assertiva seleção de 15 variáveis (B-VAR-1 + B-VAR-2):**
  - Etapa defaults agora checa **interseção** entre defaults ativos do JSF e os 15 valores desejados (antes só checava quantidade ≥15 → passava com 31 defaults errados contendo só 14 corretos).
  - Nova validação de **TOKENS** (chips visuais do `SelectCheckboxMenu`): helper `_validar_tokens_variaveis()` extrai `data-item-value` de `<ul.ui-selectcheckboxmenu-token-container li.ui-selectcheckboxmenu-token>` = FONTE DE VERDADE VISUAL do PrimeFaces. Se faltar valor → reabre painel, remarca forcado modo `lista_valores`, revalida até 2x.
  - Logs detalhados: `"Variáveis: DEFAULTS ATIVOS + INTERSEÇÃO OK (15/15)"` + `"TOKENS pós-fechamento: 15/15 corretos (tentativa N/2)"`.
- **Segurança (6 pilares implementados):**
  - SEG-1. Injeção JS zero concatenação. Todo `execute_script` usa `arguments[0..N]` (zero f-string / `+ var +` em string JS). Refatorado `_ajustar_checkboxes_js` (3 modos), `marcar_radiobutton` (early/checado/marcar/diag), defaults variáveis, `_validar_tokens_variaveis`.
  - SEG-2. URL Whitelist. `assert_url_whitelist()` em 4 pontos críticos (GET login, pós-login, pós-navegação menus, pós-pesquisar). Domínios default: só `pesquisasconjunturais.cni.com.br`.
  - SEG-3. Watchdog timeout global. `start_watchdog(3600s padrão)` com `check_watchdog("label")` antes de cada Service. Warning aos 5 min restantes; `TimeoutError` se expirar. Usa `time.monotonic()` imune a ajustes NTP.
  - SEG-4. Sanitização de Logs. `sanitize_log_message()` (regex keywords: PASSWORD, SENHA, TOKEN, SECRET, CNI_USER, CNI_PASSWORD, API_KEY) substitui valores por `***`. Aplicado em ValidationError Pydantic e todo `except Exception` do `main.py` (msg + repr).
  - SEG-5. Permissões `.env`. `check_env_file_permissions()`: POSIX valida `0o600` emite warning se world-readable; Windows tenta ACL advapi32; fallback sempre executa sem bloquear.
  - SEG-6. Lock Single-Instance cross-platform. `SingleInstanceLock` com 3 estratégias: Windows `msvcrt.locking` → POSIX `fcntl.flock` → Fallback arquivo PID `O_CREAT|O_EXCL` + stale PID timeout. Context manager; levanta `SingleInstanceLockError` se dupla execução.
- **Integração main:** `main.py` recebe Lock context manager + Watchdog start/check + 4x URL Whitelist assertions + Sanitize exception. Entry point agora com `< 200 linhas`.

### Arquivos Criados
- [core/security.py](file:///g:/ic/core/security.py) — SEG-2, SEG-3, SEG-4, SEG-5 (sanitize, whitelist, watchdog, env-perms)
- [core/lock.py](file:///g:/ic/core/lock.py) — SEG-6 (SingleInstanceLock cross-platform)
- [README.md](file:///g:/ic/README.md) — Documentação principal (visão geral, stack, execução, troubleshooting, estrutura)
- [docs/ARCHITECTURE.md](file:///g:/ic/docs/ARCHITECTURE.md) — Clean Arch 7 camadas, diagrama Mermaid, SOLID, fluxo Fases 0–4, Hard Constraints
- [docs/SECURITY.md](file:///g:/ic/docs/SECURITY.md) — 6 pilares detalhados com como testar cada um
- [docs/TESTING.md](file:///g:/ic/docs/TESTING.md) — 18 testes pytest por arquivo, como rodar, coverage desejada vs atual
- [docs/DEPLOYMENT.md](file:///g:/ic/docs/DEPLOYMENT.md) — Windows Server / Linux headless, `.env`, permissões, Task Scheduler / cron
- [docs/AUTOMACAO_MAPA_CAMPOS.md](file:///g:/ic/docs/AUTOMACAO_MAPA_CAMPOS.md) — 100% IDs PrimeFaces extraídos do DOM, 15 variáveis com valores reais checkbox, Ordem Fase3
- [docs/CONTRIBUTING.md](file:///g:/ic/docs/CONTRIBUTING.md) — Padrões código, Conventional Commits, SOLID, checklist Code Review
- [docs/CHANGELOG.md](file:///g:/ic/docs/CHANGELOG.md) — Este arquivo

### Arquivos Modificados
- [config/constants.py](file:///g:/ic/config/constants.py) — Adicionado bloco segurança: `URL_WHITELIST`, `WATCHDOG_TIMEOUT_GLOBAL_S`
- [config/settings.py](file:///g:/ic/config/settings.py) — Integração SEG-4 (sanitize ValidationError) + SEG-5 (check_env_file_permissions pós-load_dotenv)
- [pages/parametros_page.py](file:///g:/ic/pages/parametros_page.py) — Rewrite total `preencher_variaveis` + helper novo `_validar_tokens_variaveis`
- [infrastructure/browser/actions.py](file:///g:/ic/infrastructure/browser/actions.py) — Rewrite `_ajustar_checkboxes_js` (fallback container robusto + try/catch global JS). Refatorado `marcar_radiobutton_primefaces` (4 trechos) para `arguments[0..N]` sem concatenação
- [main.py](file:///g:/ic/main.py) — Integra Lock + Watchdog + Whitelist checks + Sanitize exceptions (entry point rewritten < 200 linhas)

### Arquivos Excluídos (Limpeza)
- `.pipeline.lock` — Lock obsoleto execução interrompida
- `diag_sem_datatable.png` — Screenshot temporário diagnóstico antigo
- `.pytest_cache/` inteiro — Cache pytest recriado automaticamente
- Todos `**/__pycache__/` nas 7 camadas — Bytecode antigo (foi causa anterior de TypeError `passo()`)

### Corrigido
- SyntaxWarning `_escapar_id_para_css` actions.py L1337: docstring agora raw string `r"""..."""` (escape `\\:` válido em Python 3.14)
- Retorno `None` silencioso `_ajustar_checkboxes_js`: agora script JS tem `try { } catch(eGlobal) { return -999 }` com retorno explícito; Python wrapper loga ERRO_JS_INTERNO ou EXCEPTION_py com stack trace qualitativo

---

## [2026.09.15a] — Refatoração Monólito → Clean Architecture 7 Camadas (anterior no mesmo dia)

### Primeira Refatoração Estrutural do Dia
- **Monólito `main_monolith_backup.py` (~2900 linhas num único arquivo)** → Quebrado em **30 arquivos, 7 camadas**:
  1. `config/` (settings Pydantic + constants)
  2. `core/` (errors hierarchy + @with_retry exponential backoff)
  3. `domain/` (PesquisaParams frozen Pydantic + validators + mappings VAR_COD_POR_VALUE 31 entries)
  4. `infrastructure/browser/` (Chrome driver custom + waits 6 perfis polling AJAX + actions helpers JS)
  5. `pages/` POM (5 Page Objects: base, login, menu, parametros, resultados; locators privados By.ID)
  6. `services/` (AuthService F1 + NavigationService F2 + PesquisaService F3+4, todos @with_retry ≥ 3)
  7. `main.py` entry point fino
- **Testes unitários iniciais:** 18 testes pytest offline (`test_core_errors`:7, `test_core_retry`:3, `test_domain_models`:8)
- **Fail-fast:** `get_settings()` valida CNI_USER/CNI_PASSWORD ANTES de abrir Chrome
- **Correção Ordem Fase 3 implementada:** 5 filtros → Estrato → Variáveis → Radios → Orientação
- **POM:** IDs JSF com dois-pontos `:` usam `By.ID` (evita InvalidSelectorException). `_locator_to_css` quando CSS necessário tem escape dupla barra.
- **Helpers PrimeFaces extraídos:** `abrir_selectcheckboxmenu_primefaces`, `fechar_painel_selectcheckboxmenu`, `_ajustar_checkboxes_js` (modo preferencia/todas/lista_valores), `marcar_radiobutton_primefaces` (descobre NAME real via JS fallback IDs dinâmicos), `valor_campo_jah_correto` (early return JS nativo evita 56s em campos já corretos).

### Arquivos Criados
- Todas as 7 camadas (30 arquivos .py iniciais), pasta `tests/` com 3 arquivos de teste, `.env.example` template, `requirements.txt`
- Backup preservado: `main_monolith_backup.py` (NUNCA modificado, referência)

### Segurança Parcial (antes da melhoria 2026.09.15b)
- Apenas `@with_retry` + `Pydantic frozen`; 6 pilares completos só vieram na 2026.09.15b.

---

## [Unreleased] — Próximas Melhorias Planejadas

### TODO Backlog
- [ ] **Testes unitários core/security.py + core/lock.py:** hoje 0% coverage (ALTO RISCO — adição prioridade máxima próxima refatoração).
- [ ] **Testes integração pages parametros_page com mock Selenium:** valida `preencher_variaveis` sem abrir Chrome real.
- [ ] **Relatório Excel comparativo:** Automatizar comparação de planilhas baixadas com o backup monólito (matriz evidência: colunas X linhas iguais?).
- [ ] **Armazenamento estruturado downloads:** Mover Excel baixado de `~/Downloads/` para `g:\ic\downloads\<TIMESTAMP>_export.xlsx` com nome controlado.
- [ ] **Logging estruturado JSON:** Trocar `print(flush=True)` por `python-json-logger` / `structlog` para ingestão ELK/Datadog.
- [ ] **Healthcheck pipeline:** endpoint / arquivo `status.json` com `{status: RUNNING|SUCCESS|FAILED, fase, progresso_pct, ultima_msg, duracao_s}` para monitoramento externo.
- [ ] **Docs Swagger/API:** Se alguma futura camada expuser endpoints FastAPI para automação sob demanda.

---

## Notas de Rodagem de Referência

| Data | Build | Pipeline Resultado | Tempo Total | Observação |
|---|---|---|---|---|
| 2026-09-15 (antes das melhorias do dia) | Monólito backup | SUCESSO | 442.6s | Primeira rodada bem-sucedida confirmada; base para as melhorias |
| 2026-09-15 | 2026.09.15a (Clean Arch) | SUCESSO | ~430s | Refatoração equivalente em paridade; 18 testes pytest 18 passed |
| 2026-09-15 | 2026.09.15b (Variáveis + Segurança) | VALIDAR SMOKES | — | py_compile 0 erros + pytest 18/18 passed. Pipeline completo Chrome Selenium validar em próximo run. |
