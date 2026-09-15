# Segurança: 6 Pilares Implementados

> A automação CNI segue 6 pilares de segurança end-to-end, integrados de **fail-fast** (antes de abrir o navegador) até **pipeline execution** (trava, watchdog, whitelist) e **postmortem** (logs sanitizados).
> Código-fonte: [security.py](file:///g:/ic/core/security.py) | [lock.py](file:///g:/ic/core/lock.py) | [main.py](file:///g:/ic/main.py) | [actions.py](file:///g:/ic/infrastructure/browser/actions.py)

---

## Sumário Visual dos 6 Pilares

| # | Pilar | Arquivo Principal | Quando Atua |
|---|---|---|---|
| **SEG-1** | Injeção JS Zero (execute_script com arguments) | [actions.py](file:///g:/ic/infrastructure/browser/actions.py) | Toda injeção de JavaScript |
| **SEG-2** | URL Whitelist (apenas domínios autorizados) | [security.py](file:///g:/ic/core/security.py) `assert_url_whitelist()` | Após GET login, pós-login, pós-navegação menus, pós-Pesquisar |
| **SEG-3** | Watchdog Global Timeout (60 min padrão) | [security.py](file:///g:/ic/core/security.py) `start_watchdog/check_watchdog` | Início pipeline + check antes de cada Service |
| **SEG-4** | Sanitização de Logs (senhas/tokens → `***`) | [security.py](file:///g:/ic/core/security.py) `sanitize_log_message()` | Toda `print(exc)` no main e ValidationError Pydantic |
| **SEG-5** | Permissões Arquivo `.env` (não world-readable) | [security.py](file:///g:/ic/core/security.py) `check_env_file_permissions()` | Pós-load_dotenv no settings.py (fail-fast) |
| **SEG-6** | Lock Single-Instance (só 1 pipeline por vez) | [lock.py](file:///g:/ic/core/lock.py) `SingleInstanceLock` | Antes do pipeline começar (main.py context manager) |

---

## SEG-1: Injeção JS Zero Concatenação

### Problema Anterior
Injeção de JavaScript via concatenação/f-strings Python:
```javascript
// RISCO (antigo): se value_alvo tiver aspas/barras → quebra JS ou executa inesperado
"var t = document.getElementById('" + table_id + "');"
```

### Solução (atual, 100% livre concatenação)
Todo `driver.execute_script()` Selenium recebe **código JS estático** + **parâmetros via arguments[0..N]**. O Selenium serializa os argumentos corretamente (escapa aspas, barras, tipos, arrays, null).

Exemplo do batch de checkboxes:
```python
_SCRIPT = r"""
var baseId  = arguments[0];   // base_id widget
var modo    = arguments[1];   // "lista_valores" / "todas" / "preferencia"
var valores = arguments[2];   // array de valores reais
var labels  = arguments[3];   // array labels lowercase
(... resto do código JS estático ...)
"""
res = driver.execute_script(
    _SCRIPT,           // código JS 100% estático (NENHUMA interpolação Python)
    base_id,           // arg0 → arguments[0]
    modo,              // arg1 → arguments[1]
    valores_arr,       // arg2 → arguments[2]
    labels_arr,        // arg3 → arguments[3]
)
```

### Escopo Abrangente
- `_ajustar_checkboxes_js` (3 modos, 31 checkboxes) em [actions.py](file:///g:/ic/infrastructure/browser/actions.py#L488-L626)
- `marcar_radiobutton_primefaces` (early return + helper checado + marcar universal + diag fallback) em [actions.py](file:///g:/ic/infrastructure/browser/actions.py#L1415-L1844)
- Etapa defaults de variáveis (interseção) em [parametros_page.py](file:///g:/ic/pages/parametros_page.py#L232-L245)
- Helper `_validar_tokens_variaveis` em [parametros_page.py](file:///g:/ic/pages/parametros_page.py#L98-L129)

---

## SEG-2: URL Whitelist Assertiva

### Por quê?
Se por qualquer motivo (redirect inesperado, phishing, XSS forward) o navegador sair do domínio autorizado, a automação **aborta imediatamente ANTES** de continuar com credenciais/preenchimento/dados exportados.

### Implementação
Arquivo: [security.py](file:///g:/ic/core/security.py) — função `assert_url_whitelist(driver, allowed_hosts: Iterable[str])`

```python
URL_WHITELIST = {"pesquisasconjunturais.cni.com.br"}  # constants.py
```

A função usa `urllib.parse.urlparse(driver.current_url).hostname` e aceita:
- Domínio exato: `pesquisasconjunturais.cni.com.br` 
- Subdomínios (endswith `.X`): `qualquer.coisa.pesquisasconjunturais.cni.com.br` 
- **Qualquer outro domínio:** levanta `URLWhitelistError` (herda de `AppError`, não-retry por padrão) 

### Pontos de Verificação (main.py)
```
1. Após driver.get(URL_BASE_LOGIN)
2. Pós-login bem-sucedido (AuthService)
3. Pós-navegação menus Por Atividade (NavigationService)
4. Pós-clique em Pesquisar + Datatable pronta (PesquisaService)
```

### Como Adicionar Novo Domínio (se necessário)
Edite [constants.py](file:///g:/ic/config/constants.py):
```python
URL_WHITELIST: set[str] = {
    "pesquisasconjunturais.cni.com.br",
    "login.cni.gov.br",  # exemplo novo domínio
}
```

---

## SEG-3: Watchdog Global Timeout Monotônico

### Por quê?
Evita pipelines "zumbis" que rodam infinitamente (loop polling infinito, AJAX não concluído, diálogo modal esquecido, rede travada).

### Implementação
Arquivo: [security.py](file:///g:/ic/core/security.py) — funções `start_watchdog / check_watchdog / watchdog_remaining_s`.

```python
WATCHDOG_TIMEOUT_GLOBAL_S: int = 60 * 60  # constants.py = 3600s = 1 hora
```

- Usa `time.monotonic()` (NÃO usa `time.time()`) → imune a ajustes de relógio do sistema / NTP.
- `start_watchdog(N)`: marca deadline = `monotonic() + N`.
- `check_watchdog(label)`:
  - Se faltar **≤ 300s (5 min):** emite WARNING `"Watchdog: faltam Xs para timeout (em Y)"`.
  - Se **exceder deadline:** levanta `TimeoutError` core (herda de `RetryableError` mas o loop de retry acaba rapidamente pois continuará excedendo).

### Pontos de Verificação (main.py)
- Antes de `AuthService` → `check_watchdog("login")`
- Antes de `NavigationService` → `check_watchdog("navegacao")`
- Antes de `PesquisaService` → `check_watchdog("pesquisa+export")`

### Como Ajustar
Edite `WATCHDOG_TIMEOUT_GLOBAL_S` em [constants.py](file:///g:/ic/config/constants.py).

---

## SEG-4: Sanitização de Logs (Nunca Mostra Senha/Token)

### Por quê?
Evita que credenciais `.env`, tokens de sessão ou segredos apareçam em `print`, logs de console, arquivos de log, traceback de Exception.

### Implementação
Arquivo: [security.py](file:///g:/ic/core/security.py) — função `sanitize_log_message(msg: object) -> str`

#### Palavras-chave Sensíveis (regex heurística)
A função detecta padrões `KEY=valor`, `KEY : valor`, `KEY "valor"` e substitui o valor por `***` se a palavra-chave contiver (case-insensitive):
```
PASSWORD, SENHA, PASSWD, PASSWD, TOKEN, SECRET, CHAVE, API_KEY, APIKEY, CNI_USER, CNI_PASSWORD, CLIENT_SECRET, ACCESS_TOKEN, AUTH
```

#### Exemplos
| Entrada | Saída |
|---|---|
| `"Erro login: usuário u=fulano senha=Senha123!"` | `"Erro login: usuário u=fulano senha=***"` |
| `"ValidationError: CNI_PASSWORD field required; CNI_USER='a***'"` | `"ValidationError: CNI_PASSWORD field required; CNI_USER=***"` |

### Pontos Aplicados
1. **Pydantic ValidationError** → `model_validate_env` em [settings.py](file:///g:/ic/config/settings.py) levanta `ValidationError(sanitize_log_message(msg))`.
2. **Fallback dataclass settings** em [settings.py](file:///g:/ic/config/settings.py).
3. **main.py except Exception:** `_msg = sanitize_log_message(str(exc))` e `_repr = sanitize_log_message(repr(exc))` ANTES de imprimir.
4. **main.py except lock:** exc_lock passa por sanitize também.

---

## SEG-5: Permissões Arquivo `.env` (não World-Readable)

### Por quê?
Se `.env` for legível por todos usuários do sistema (Linux `0644`, ou Windows ACL "Everyone:Read"), qualquer processo/usuário lembra credenciais. Deve ser legível só pelo dono (Linux `0600`, Windows ACL restrita).

### Implementação
Arquivo: [security.py](file:///g:/ic/core/security.py) — função `check_env_file_permissions(env_path: Path) -> Tuple[bool, str]`

#### POSIX / Linux / macOS:
- `stat.S_IMODE(os.stat(env_path).st_mode) & 0o077 == 0` → `0o600` (rw-------) → OK.
- Caso contrário: WARNING no console com sugestão `chmod 600 .env`.

#### Windows:
- Tenta ajustar / checar ACL via `advapi32.ConvertStringSidToSidW + GetNamedSecurityInfoW` (ctypes).
- Se falhar (biblioteca não disponível): retorna OK sem warning (não bloqueia execução; só avisa se tiver certeza).

### Ponto de Aplicação
`_carregar_dotenv_se_ainda_nao()` em [settings.py](file:///g:/ic/config/settings.py) chama logo após `load_dotenv`. Se warning, só printa; **não bloqueia** execução (pois algumas implantações de container realmente precisam de 0644 e opt-in).

---

## SEG-6: Lock Single-Instance Cross-Platform

### Por quê?
Evita **2+ execuções simultâneas** do pipeline: ambas disputam mesma sessão Chrome, mesmo `.pipeline.lock`, mesma pasta Downloads e enviam múltiplas pesquisas para CNI podendo causar rate limit.

### Implementação
Arquivo: [lock.py](file:///g:/ic/core/lock.py) — classe `SingleInstanceLock` (context manager).

#### 3 Estratégias Cross-Platform (primeiro que vencer = ok)
1. **Windows:** `msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)` (lock não-bloqueante de 1 byte).
2. **POSIX (Linux/macOS):** `fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)`.
3. **Fallback universal:** `os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR)` (cria arquivo exclusivo) + escreve PID. Se `FileExistsError`, verifica se PID dono ainda existe.

#### Timeout PID obsoleto (stale check):
- Lock fallback arquivo PID tem `stale_timeout_s=30` padrão. Se arquivo PID tem mais de 30s e PID não existe mais → considera obsoleto e remove.

#### Como usar (main.py):
```python
lock_path = Path(__file__).resolve().parent / ".pipeline.lock"
with SingleInstanceLock(lock_path):
    _pipeline_completo()
```

Se outra instância estiver rodando → levanta `SingleInstanceLockError` (apropriado, NÃO retorna false silenciosamente).

---

## Resumo: Como Testar Cada Pilar (Auto-Check)

| Pilar | Passo de Auto-Validação |
|---|---|
| SEG-1 | No `actions.py`, grep por concatenação `' + var + '` dentro de strings JS — deve retornar 0. |
| SEG-2 | Temporariamente edite `URL_BASE_LOGIN` para `"https://google.com"`. Execute main.py — deve levantar `URLWhitelistError` pós-GET. |
| SEG-3 | Ajuste `WATCHDOG_TIMEOUT_GLOBAL_S = 2` em constants.py. Execute — deve levantar `TimeoutError` antes de concluir. |
| SEG-4 | Teste `sanitize_log_message("CNI_PASSWORD=abc123 e TOKEN=xyz")` → `"CNI_PASSWORD=*** e TOKEN=***"`. |
| SEG-5 | Linux: `chmod 644 .env` → warning ao rodar main.py. |
| SEG-6 | Abra 2 terminais simultâneos em g:\ic. Execute `python main.py` em ambos → 2º terminal levanta `SingleInstanceLockError`. |
