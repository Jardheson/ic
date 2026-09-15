# Deployment e Execução: Ambiente Produção

> Como implantar, configurar variáveis de ambiente, permissões de arquivo e rodar a automação em ambientes Windows Server / Linux headless.
> Leitura complementar: [README.md](file:///g:/ic/README.md) | [SECURITY.md](file:///g:/ic/docs/SECURITY.md)

---

## 1. Pré-requisitos Ambiente

### Windows Server
| Item | Versão Recomendada |
|---|---|
| Sistema Operacional | Windows Server 2019+ ou Windows 10/11 Pro 64 bits |
| Python | 3.12.x ou 3.14.x (64-bit, baixar do python.org) |
| Google Chrome | Última versão estável (instalado em `C:\Program Files\Google\Chrome\Application\chrome.exe`) |
| ChromeDriver | Gerenciado automaticamente por Selenium Manager (não precisa baixar manualmente) |
| PowerShell | 5.1+ ou PowerShell 7.x |
| Pastas downloads | `C:\Users\<USUARIO>\Downloads\` padrão do Chrome |

### Linux Server (Ubuntu 22.04 LTS / Debian 12 — headless=True)
```bash
# 1) Dependências Chrome headless
sudo apt-get update
sudo apt-get install -y wget gnupg ca-certificates curl unzip

# 2) Instala Google Chrome estável
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg
echo "deb [signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt-get update
sudo apt-get install -y google-chrome-stable

# 3) Instala Python 3.12+ e venv
sudo apt-get install -y python3 python3-venv python3-pip python3-dev libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libasound2
```

---

## 2. Variáveis de Ambiente `.env`

### Template Oficial (`.env.example` → `.env`)
Arquivos: [.env.example](file:///g:/ic/.env.example)
Crie `.env` com suas credenciais:
```dotenv
# ============================================================
# AUTOMAÇÃO CNI — PESQUISAS CONJUNTURAIS INDUSTRIAIS
# ============================================================

# Usuário e Senha de acesso à Federação CNI (OBRIGATÓRIO)
CNI_USER=seu_usuario_da_federacao
CNI_PASSWORD=sua_senha_da_federacao

# (Opcional) — se deixar vazio usa valor default do settings.py
# URL_BASE_LOGIN=https://pesquisasconjunturais.cni.com.br/Sondagens/view/index.faces
```

### Carregamento Fail-Fast
- `settings.py` carrega `.env` via `python-dotenv` + Pydantic BaseSettings.
- Se `CNI_USER` ou `CNI_PASSWORD` estiverem **vazios/ausentes**: levanta `ValidationError` ANTES de abrir Chrome/qualquer automação.
- Mensagens de erro de validação **passam por sanitização** antes de serem logadas (nunca expõem senha).

---

## 3. Permissões de Arquivo (SEG-5)

> `.env` NÃO pode ser world-readable! (SEG-5 — permissões seguras para arquivo de credenciais)

### Linux / macOS
```bash
cd g:\ic        # ou caminho Linux
chmod 600 .env
# Resultado esperado:
ls -la .env
# -rw------- 1 usuario grupo  412 set 15 04:00 .env   (apenas dono:rw, grupo e outros: ---)
```
Se permissões forem `644` (world-readable), ao rodar `main.py` aparecerá WARNING:
```
[WARNING PERMISSIONS .env] Arquivo .env está world-readable (0o644). Execute `chmod 600 .env` para corrigir.
```

### Windows
A automação tenta ajustar/checar ACL via `advapi32.dll + ConvertStringSidToSidW` (ctypes). Se a API falhar (biblioteca não disponível / Home Single Language), **não levanta erro** — só emite aviso quando há certeza.

Permissões recomendadas via GUI (se quiser garantir manual):
1. Clique com direito em `.env` → Propriedades → Segurança → Avançado
2. Desative "Herança" → "Converter permissões herdadas em permissões explícitas"
3. Remova grupos: `Todos (Everyone)`, `Usuários Autenticados`, `BUILTIN\Users`
4. Deixe apenas: `SYSTEM`, `<SEU USUÁRIO>`, `Administradores` (todos com Controle Total / Leitura e Gravação)

---

## 4. Instalação de Dependências

### PowerShell (Windows)
```powershell
cd g:\ic
# 1) Cria e ativa o ambiente virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) Instale todas dependências (Selenium + Pydantic + Pytest + dotenv)
pip install --upgrade pip
pip install -r requirements.txt

# 3) Verifique instalação
python -c "import selenium, pydantic, pytest, dotenv; print('deps OK')"
```

### Bash (Linux/macOS)
```bash
cd /caminho/para/ic
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python3 -c "import selenium, pydantic, pytest, dotenv; print('deps OK')"
```

---

## 5. Modos de Execução

### 5.1 Modo Padrão (Chrome visível / headless=False) — Recomendado Validação
Use quando quiser visualizar passo a passo no navegador:
```powershell
chcp 65001                 # Habilita UTF-8 na saída console Windows
$env:PYTHONIOENCODING="utf-8"
python main.py
```

Saída esperada final (4–8 minutos dependendo de AJAX):
```
FASE 0 / FASE 1 Login / FASE 2 Navegação / FASE 3 Preenchimento / FASE 4 Pesquisa + Export
 SUCESSO: pipeline completo finalizado em 442.6s.
```
O Excel é baixado automaticamente na pasta Downloads.

### 5.2 Modo Produção Headless (Chrome invisível, sem janela)
Edite [main.py](file:///g:/ic/main.py) linha:
```python
# ANTES (visual)
driver = create_driver(headless=False)

# DEPOIS (headless / produção)
driver = create_driver(headless=True)
```
Rode o mesmo comando: `python main.py`. Chrome roda em background sem interface.

---

## 6. Troubleshooting Erros Mais Frequentes

| Sintoma / Erro | Causa | Passo a Passo Correção |
|---|---|---|
| `ValidationError: CNI_USER, CNI_PASSWORD ausentes` | `.env` não existe ou campos vazios | Copie `.env.example` → `.env` e preencha com usuário/senha válidos da Federação CNI |
| **`TypeError: passo() missing required positional argument: 'fn'`** | Bytecode antigo `__pycache__` divergente do `.py` atual | `Get-ChildItem -Recurse -Directory -Filter __pycache__ . \| Remove-Item -Recurse -Force` |
| `InvalidSelectorException: ... #selectForm:coorte` | Usou `By.CSS_SELECTOR` com `:` (dois-pontos JSF) sem escape | Mantenha `By.ID` (implementação atual). Se precisar CSS: `selectForm\\:coorte` (escapa dupla barra) |
| Login mensagem `"usuário não encontrado"` | **Credencial recusada pela FEDERAÇÃO CNI** (servidor), NÃO é bug de código | Valide a mesma senha manualmente no site no Chrome. Troque a senha na Federação se necessário. |
| `RetryableError: Nenhuma variável marcada` | Checkbox marcado via JS mas widget PrimeFaces não sincronizou para tokens/chips | Automatically tenta remarcar forcado 2x. Se persistir: abra o painel manualmente e confirme se defaults estão nas 15 vars desejadas. |
| `URLWhitelistError: current URL hostname=google.com não está na whitelist` | Redirecionou para domínio fora da lista. Por padrão só `pesquisasconjunturais.cni.com.br` é permitido. | (1) Se redirect legítimo → adicionar domínio em `URL_WHITELIST` de [constants.py](file:///g:/ic/config/constants.py). (2) Se redirect suspeito → investigar phishing. |
| `TimeoutError: Watchdog global expirou` | Passou de 60 minutos (padrão WATCHDOG_TIMEOUT_GLOBAL_S). Execução provavelmente travou em AJAX. | Aumente `WATCHDOG_TIMEOUT_GLOBAL_S` em [constants.py](file:///g:/ic/config/constants.py) se tiver internet muito lenta. |
| `SingleInstanceLockError` | Outra execução do pipeline ainda rodando em background | Encerre outra janela Chrome/Python. Ou se travamento antigo: delete `.pipeline.lock` manualmente (só se tiver certeza que nenhum processo roda). |
| Datatable não aparece, 0 resultados após Pesquisar | Combinação filtros + coorte + período retorna sem dados. Não é bug código. | Teste manualmente mesma combinação de filtros no site CNI; ajuste período/coorte se não há dados no servidor. |
| `ElementClickInterceptedException: ... would receive the click` | Overlay / modal / header fixo bloqueia o clique. Ações de alto risco usam JS click fallback no código atual. | Se erro persiste em campo novo → adicionar caso no helper `_ajustar_ui` ou usar `driver.execute_script("arguments[0].click();", elemento)`. |

---

## 7. Observabilidade (Logs + Rastreabilidade)

### Logs Atuais
- **Console stdout:** `print(..., flush=True)` em todos passos (FASE, sub-etapas, tempos parciais).
- **Tempo de cada etapa:** cada página / cada campo exibe duração `(XX.Xs)`.
- **Diagnósticos de falha:** `[DIAG marcar_radio]`, `[DIAG VARIÁVEIS qtd=0!]`, `[_ajustar modo=lista]` detalham valores reais encontrados no DOM.
- **Exceções sanitizadas:** `main.py` passa `str(exc)` e `repr(exc)` por `sanitize_log_message()` ANTES de imprimir → **nenhuma senha aparece**.

### Rastreabilidade (Matriz Evidência)
| ID Requisito | Implementação | Evidência / Teste |
|---|---|---|
| R1: 15 variáveis exatas | `preencher_variaveis` + `_validar_tokens_variaveis` em parametros_page | Logs `"TOKENS 15/15"` + values reais `['948','955',...]` |
| R2: Ordem rígida Fase 3 | `pesquisa_service.py` ordem imposta (service decide ordem, não main) | Código fonte + pytest smoke |
| R3: Fail-fast credenciais | `settings.py` Pydantic frozen | `test_domain_models.py` + mensagem `"CNI_USER e/ou CNI_PASSWORD ausentes"` |
| R4: Retry ≥ 3 serviços | `@with_retry(tentativas=3)` em auth/navigation/pesquisa | `test_core_retry.py::test_with_retry_sucesso_segunda_tentativa` |
| R5: SEG 6 pilares | `security.py` + `lock.py` + `main.py` integração | [SECURITY.md](file:///g:/ic/docs/SECURITY.md) auto-check passos |

---

## 8. Execução Agendada (Task Scheduler / Cron)

### Windows Task Scheduler (recomendado diário)
1. Abrir "Agendador de Tarefas" → Criar Tarefa Básica
2. **Trigger:** Diariamente às 07:00
3. **Ação:** Iniciar um programa
   - Programa/script: `C:\Caminho\Para\g:\ic\.venv\Scripts\python.exe`
   - Adicionar argumentos: `main.py`
   - Iniciar em: `g:\ic`
4. **Configurações gerais:** Marque "Executar mesmo que usuário não esteja conectado" (precisa headless=True + credenciais Windows)
5. **Histórico:** Habilite "Histórico de Tarefas" para ver sucesso/falha.

### Linux Cron
Edite `crontab -e`:
```cron
# Diariamente às 07:00, log em arquivo com sanitização
0 7 * * * cd /caminho/para/ic && . .venv/bin/activate && python main.py >> /var/log/cni-pipeline.log 2>&1
```

**Não esqueça:** Para ambos (Windows/Linux agendado), use `create_driver(headless=True)`. Task Scheduler sem sessão desktop ativa NÃO consegue exibir janela Chrome.
