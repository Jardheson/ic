# Melhoria da Automação: Correção de Variáveis + Implementação de Segurança

## Repository Research

### A. Bugs Confirmados na Seleção de Variáveis

**B-VAR-1 (HIGH) — Verificação Defaults Incompleta (parametros_page.py#L144-178):**
- A etapa atual verifica APENAS `qtd_default >= _alvo_min` (quantidade), SEM checar **QUAIS** values dos checkbox estão realmente marcados.
- A imagem 5 confirma que 15 defaults estão corretos para 1 tela do usuário, mas em outras telas, coortes, períodos ou sessões o JSF pode inicializar defaults DIFERENTES.
- Resultado: automação considera "ok" 32 checkboxes marcados, mas as 15 do usuário podem estar PARCIALMENTE DESMARCADAS.
- **Solução:** Comparar INTERSEÇÃO (set intersection) entre `valores_desejados` e `_debug_values_checked` da etapa defaults. Se interseção < len(valores_desejados), cai no marcar JS lote para ACERTAR os faltantes.

**B-VAR-2 (HIGH) — Validação por Tokens (Fonte de Verdade Visual img6):**
- A imagem6 mostra que os chips ativos (`ul.ui-selectcheckboxmenu-token-container li[data-item-value]`) são a **fonte de verdade FINAL** renderizada pelo PrimeFaces. O usuário confere visualmente os chips, não os checkboxes internos.
- A automação atualmente NÃO lê nem compara tokens. Se o JS marcar checkbox mas o widget não renderizar chip, a pesquisa vai com variáveis erradas.
- **Solução:** Após fechar painel, fazer uma etapa extra de **VERIFICAÇÃO TOKENS** comparando `data-item-value` dos li com `valores_desejados`. Se houver delta, reabrir painel, desmarcar tudo, remarcar modo=lista_valores (force).

**B-VAR-3 (MEDIUM) — Etapa Defaults não aceita argumento valores desejados:**
- `preencher_variaveis` atualmente tem `len_ref = len(valores_desejados)` mas a contagem de defaults usa `qtd_default >= _alvo_min` numérico. Interseção é obrigatória para garantir assertividade.

**B-VAR-4 (MEDIUM) — Mapeamento VAR_COD_POR_VALUE key string sem coerção:**
- Em `mappings.py`, VAR_COD_POR_VALUE keys são `str`. Em `actions.py L492` `valores_js = str([str(x) for x in (valores_desejados or [])])` — OK, mas codigos_para_values retorna list[str]. Preciso garantir que getAttribute('value') (que sempre retorna string) bata exato.

### B. Lacunas de Segurança Confirmadas

**SEG-1 (HIGH) — Injeção de JS por concatenação de strings:**
- Múltiplos locais: `_ajustar_checkboxes_js`, `preencher_variaveis` etapa defaults, `marcar_radiobutton_primefaces` (todos usam `+ "stringJS" + variavel_python + "..."`).
- Se alguma constante ou entrada de usuário contiver aspas, `\`, script tag → quebra o JS e pode levar a execução de código inesperado no navegador.
- **Solução:** Migrar TODAS as injeções de JS que recebem variáveis Python para `driver.execute_script(script, arg1, arg2, ...)` e acessar via `arguments[0]`, `arguments[1]` no lado JS.

**SEG-2 (HIGH) — Ausência de URL Whitelist:**
- `driver.get(URL_BASE_LOGIN)` usa constante fixa (OK), mas não há validação pós-navegação que garanta que NÃO houve redirect malicioso.
- **Solução:** Adicionar helper `_assert_url_whitelist(driver, whitelist)` em `core/` que valida `document.location.hostname` pertence a `{pesquisasconjunturais.cni.com.br}`. Chamar após login, após navegação menus, após clicar Pesquisar.

**SEG-3 (MEDIUM) — Sem Watchdog / Timeout Global do pipeline:**
- Com retry @with_retry e loops polling, pode ocorrer loop infinito (ex: se o servidor da CNI cair no meio do pipeline, a automação pode ficar retentando para sempre).
- **Solução:** No `main.py`, criar `_WATCHDOG_TIMEOUT_GLOBAL = 30 * 60  # 30 minutos` e, dentro de _pipeline_completo, checar tempo decorrido em pontos-chave (antes de cada retry decorator fazer raise em vez de retry se já passou do limite).

**SEG-4 (MEDIUM) — Sem Sanitização de Logs para Credenciais:**
- Em settings.py, se ValidationError for levantado e traceback for logado acidentalmente com `os.environ` dump, pode expor CNI_PASSWORD.
- **Solução:** Adicionar `SECURE_LOG_KEYWORDS = ["PASSWORD", "SENHA", "SECRET", "TOKEN"]` em core/ e substituir esses valores por `***` em qualquer mensagem que contenha chaves/senhas.

**SEG-5 (LOW) — Sem Validação de Permissões de .env:**
- Em ambientes Linux, o .env deve ter permissão 600. Em Windows, checar se o arquivo NÃO é legível por "Todos".
- **Solução:** No settings.py `_carregar_dotenv_se_ainda_nao()`, adicionar checagem de permissões (Windows: try GetAccessControl; Linux: stat 0o600) e emitir WARNING se estiver world-readable.

**SEG-6 (MEDIUM) — Sem Lock de Instância Única (single-instance):**
- Se o usuário rodar o main.py duas vezes concorrentemente, as duas sessões do Chrome podem baixar Excel concorrente e/ou sobrecarregar o servidor CNI.
- **Solução:** Criar `core/lock.py` com lock de arquivo (ex: `g:\ic\.pipeline.lock`) usando `msvcrt.locking` (Windows) ou `fcntl.flock` (Linux). Main adquire lock no início, libera no finally.

---

## Files and Modules

| Arquivo | Mudança Esperada |
|---|---|
| `g:\ic\pages\parametros_page.py` | Reescrever `preencher_variaveis`: checar INTERSEÇÃO defaults vs desejados, adicionar VALIDAÇÃO TOKENS pós-fechamento, adicionar retry interno force-remarcação |
| `g:\ic\infrastructure\browser\actions.py` | Migrar `_ajustar_checkboxes_js` + `marcar_radiobutton_primefaces` para `execute_script` com `arguments[0..N]` (não concatenação strings) |
| `g:\ic\config\constants.py` | Adicionar `URL_WHITELIST = {"pesquisasconjunturais.cni.com.br"}` + `WATCHDOG_TIMEOUT_GLOBAL` + `SECURE_LOG_KEYWORDS` |
| `g:\ic\core\security.py` (NOVO) | Helpers de segurança: `sanitize_log_message`, `assert_url_whitelist`, `check_env_permissions`, `_WATCHDOG_STATE` |
| `g:\ic\core\lock.py` (NOVO) | Lock de arquivo single-instance cross-platform |
| `g:\ic\config\settings.py` | Chamar `check_env_permissions` no load_dotenv, sanitizar mensagens de erro de credenciais |
| `g:\ic\main.py` | 1. Adquirir lock de instância única 2. Inicializar watchdog global 3. Validar URL whitelist após login/navegação 4. Sanitizar exception messages antes de print |
| `g:\ic\tests\test_*` (se necessário) | Adicionar testes unitários para `sanitize_log_message`, VAR_COD_POR_VALUE e `codigos_para_values` |

---

## Implementation Steps (Ordem de Dependência)

1. **Step 1 — Core Security Helpers (primeiro, sem dependências):**
   - Criar `g:\ic\core\security.py` com:
     - `SECURE_LOG_KEYWORDS = [...]` + `sanitize_log_message(msg: str) -> str`
     - `URLWhitelistError extends AppError` + `assert_url_whitelist(driver, allowed_hosts: set)`
     - `check_env_file_permissions(env_path: Path) -> Tuple[bool, str]` (OK? / mensagem warning)
     - Watchdog state: `_WATCHDOG_START: float | None = None`, `start_watchdog(timeout_s: int)`, `check_watchdog(operation_label: str)` (levanta TimeoutError se passou do limite)
   - Criar `g:\ic\core\lock.py` com:
     - `SingleInstanceLock(path: Path)` — context manager, usa msvcrt.locking Windows + fcntl Linux, fallback para create+check PID.
   - Exportar ambos em `core/__init__.py` (se existir) ou manter imports diretos.

2. **Step 2 — Constants e Settings integrar segurança:**
   - `constants.py`: adicionar `URL_WHITELIST`, `WATCHDOG_TIMEOUT_GLOBAL_S = 30*60`, `SECURE_LOG_KEYWORDS` (remover duplicatas, manter centralizado constants ou security).
   - `settings.py`: chamar `check_env_file_permissions` no final de `_carregar_dotenv_se_ainda_nao()` (emitir print amarelo se permissões erradas); sanitizar mensagens de erro de credenciais (nunca incluir a senha real, só `***`).

3. **Step 3 — Corrigir Seleção de Variáveis (MUDANÇA MAIS IMPORTANTE):**
   - `parametros_page.py` `preencher_variaveis`:
     - (a) Criar `valores_desejados = codigos_para_values(lista_codigos_variaveis)` NO TOPO, antes de abrir painel, como list[str] garantida.
     - (b) Etapa defaults: além de contar, calcular `intersecao = len(set(valores_desejados) & set(_debug_values_checked))`. Se `intersecao >= len(valores_desejados)` → considera OK (passo). Caso contrário (e defaults >= algum), **registra delta e cai no marcar JS lote para ACERTAR**.
     - (c) Modo fallback `_ajustar_checkboxes_js`: garantir que `modo=lista_valores` executa com `valores_desejados` os 15 corretos.
     - (d) **ETAPA NOVA VALIDAÇÃO TOKENS:** Após `fechar_painel_selectcheckboxmenu`, rodar JS para extrair `document.querySelectorAll("#selectForm\\:variavel ul.ui-selectcheckboxmenu-token-container li.ui-selectcheckboxmenu-token")` e obter `.getAttribute('data-item-value')` de cada. Comparar set(tokens) com set(valores_desejados). Se NÃO baterem (delta > 0), reabrir painel, rodar `_ajustar_checkboxes_js` com modo=lista_valores FORÇADO (mesmo que defaults estivessem bons), fechar e revalidar tokens (até 2 tentativas).
     - (e) Logar **claramente** no console a lista dos values desejados e os tokens finais para debug do usuário.

4. **Step 4 — Refatorar actions.py para execute_script com arguments (evitar injeção JS):**
   - `_ajustar_checkboxes_js`:
     - Passar `base_id`, `modo`, `valores_desejados`, `labels_preferidas` como `arguments[0..3]` do execute_script, não interpolar strings.
     - Remover toda concatenação `+ valores_js +` de dentro do JS; usar `arguments[2]` (array) diretamente.
   - `marcar_radiobutton_primefaces`:
     - Refatorar trechos de injeção `_js_early` + scripts de validação para usar `arguments[0..N]`.
     - Especialmente cuidado com `value_alvo_str` — passar via `arguments[1]` no execute_script.
   - Todos os outros execute_script pequenos (ex: etapa defaults parametros_page) → migrar para arguments.

5. **Step 5 — Main integrar Lock + Watchdog + URL Whitelist:**
   - `main.py` `_pipeline_completo()`:
     - (1) Abrir `with SingleInstanceLock(Path(".pipeline.lock")):` no início.
     - (2) Chamar `start_watchdog(constants.WATCHDOG_TIMEOUT_GLOBAL_S)`.
     - (3) Após `driver.get(URL_BASE_LOGIN)`, após logar, após navegar menus, após clicar pesquisar → chamar `assert_url_whitelist(driver, constants.URL_WHITELIST)` cada vez.
     - (4) Capturar `Exception as exc` e antes de raise: chamar `sanitize_log_message(str(exc))` no print FALHA.
     - (5) Chamar `check_watchdog` antes de cada serviço grande (login, nav, pesquisa).

6. **Step 6 — Smokes e Validações:**
   - Limpar `__pycache__` sempre antes.
   - `py_compile` todos os 30+ arquivos.
   - `pytest tests/` — 18 passed + novos tests se adicionar.
   - Rodar **pipeline curto** (ou pelo menos rodar até FASE 3.1 para validar interseção e tokens).

---

## Dependencies and Considerations

- **Python 3.14 + Selenium 4.49**: Stack confirmada. Nenhuma dependência nova é OBRIGATÓRIA (lock e security usam stdlib). Para lock, usamos `msvcrt` / `fcntl` da stdlib; para permissões Windows usamos `ctypes` ou `os.stat` st_mode bits.
- **Não inverter ordem Hard Constraint**: 5 filtros → Estrato → Variáveis → Radios → Orientação → Pesquisar. Step 3 preserva isso 100%.
- **Backward Compatibilidade**: todos os métodos públicos mantêm a mesma assinatura; novas chamadas de segurança são transparentes.
- **Logging em pt-BR**: manter padrão atual (print `flush=True`), com novos steps de tokens e segurança explicitos.
- **SEG-1 migrate para arguments[0]**: cuidado especial com o `panel_sel` — ID com dois-pontos, precisa ser válido como selector CSS.

---

## Validation

- **Validação B-VAR (variáveis corretas)**: No output do console, etapa Variáveis deve logar:
  - `Defaults: interseção=15/15 (pulo marcar JS)` **OU** `Defaults: interseção=X/15 → marcando delta via JS lote.`
  - `Tokens pós-fechamento: 15/15 (corretos). Values: [948, 955, 969, 970, 961, 956, 962, 957, 963, 958, 965, 966, 964, 967, 968]`.
  - **NÃO** pode ocorrer `Tokens: 14/15 (faltam=[948]) — reabrindo painel para remarcar (1/2).`.
- **Validação SEG-1 JS injection**: Procurar por `+ var` dentro de strings JS do código. Deve haver ZERO concatenações de variáveis Python em scripts (apenas arguments).
- **Validação SEG-2 Whitelist**: Se eu mudar URL_BASE_LOGIN para `google.com`, `assert_url_whitelist` deve levantar `URLWhitelistError`.
- **Validação py_compile + pytest**: `EXIT_COMPILE=0 30/30` e `18+ passed`.
- **Validação final pipeline**: Rodar `python main.py` e conferir que Datatable apareceu < 50s e Excel baixou.

---

## Risks

- **R1: Refatorar JS para arguments pode quebrar lógica existente (ex: valores_js ou labels_js)**. Mitigação: testar isoladamente cada script JS refatorado rodando `execute_script` com arguments em script de teste antes de integrar.
- **R2: Lock de arquivo .pipeline.lock pode ser deixado aberto em crash anterior**. Mitigação: no `__enter__` do SingleInstanceLock, checar se o PID escrito no lock ainda está em execução; se não estiver, remover e adquirir.
- **R3: Watchdog muito agressivo (30 min pode ser pouco para 2 retries)**. Mitigação: valor inicial 60 min; fazer com que o check_watchdog emita WARNING 5 min antes de levantar exceção.
- **R4: Validação Tokens pode disparar falsos negativos (ex: o token é renderizado com algum value formatado diferente)**. Mitigação: logar tanto tokens extraídos quanto valores_desejados na íntegra para diagnóstico; permitir até 2 tentativas de remarcação antes de levantar erro.
