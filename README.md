# Automação CNI — Pesquisas Conjunturais Industriais

Automação **RPA resiliente** para extração de dados do portal **Pesquisas Conjunturais da CNI** (Sondagem Industrial → Consultas → Resultados/Índices → Federação → Por Atividade). Construída em **Clean Architecture + Page Object Model (POM)** com foco em **SOLID**, tratamento de erro robusto, 6 pilares de segurança e validação de 15 variáveis exatas.

---

## Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.12+ |
| Automação Browser | Selenium 4.49 + Chrome / ChromeDriver |
| Validação Modelos | Pydantic v2 (`PesquisaParams` frozen) |
| Carregamento .env | python-dotenv + Pydantic BaseSettings |
| Retry / Backoff | `@with_retry` custom com exponential backoff + jitter (≥3 tentativas) |
| Testes Unitários | pytest 9.1 (18 testes) |
| Segurança | 6 pilares integrados (ver [SECURITY.md](file:///g:/ic/docs/SECURITY.md)) |
| Princípios | Clean Code, SOLID, DDD tático, Page Object Model, Fail Fast |

---

## Fluxo da Automação (5 Fases)

```
FASE 0  →  Carrega .env fail-fast (Pydantic valida CNI_USER/CNI_PASSWORD ANTES de abrir Chrome)
FASE 1  →  Abre Chrome → GET URL_BASE_LOGIN → Autentica com credenciais (AuthService @with_retry)
FASE 2  →  Navega menus: Sondagem Industrial → Consultas → Resultados/Índices → Federação → Por Atividade
FASE 3  →  Preenche formulário selectForm (ORDEM RÍGIDA):
            Filtros Básicos (5) → Estrato → 15 Variáveis → Radios TipoEstimativa/Exibição → Orientação
FASE 4  →  Clica em "Pesquisar" → Aguarda Datatable → Clica em "Exportar para Excel"
```

---

## Pré-requisitos

1. **Python ≥ 3.12** (recomendado 3.14 / igual ambiente virtual)
2. **Google Chrome** instalado (versão recente; Selenium baixa ChromeDriver automaticamente)
3. **Credenciais válidas** da Federação CNI para `pesquisasconjunturais.cni.com.br`
4. Windows / Linux (lock single-instance cross-platform; ACL .env validado em ambos)

---

## Instalação Rápida (passo a passo)

Execute EXATAMENTE esses comandos em um PowerShell novo:

```powershell
# 1) Entrar na pasta do projeto
cd g:\ic

# 2) Criar e ativar ambiente virtual (feito 1 vez só)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3) Instalar dependências (feito 1 vez só, ou quando requirements.txt mudar)
pip install -r requirements.txt

# 4) Copiar template de credenciais e preencher
Copy-Item .env.example .env
# Agora abra g:\ic\.env no editor e preencha as linhas:
#   CNI_USER=seu_usuario_da_federacao_cni
#   CNI_PASSWORD=sua_senha
```

---

## Execução - Comando completo (copiar e colar)

Use SEMPRE esse comando em PowerShell (garante UTF-8 no console, evita caracteres quebrados em logs):

```powershell
# Modo padrão (Chrome visível, headless=False) - recomendado para validar visualmente
chcp 65001 ; $env:PYTHONIOENCODING="utf-8" ; python main.py
```

Isso executa TODO o pipeline com Chrome visível (acompanhe passo a passo):
1. Carrega `.env` e valida credenciais (fail-fast)
2. Abre Chrome visível → faz login
3. Navega menus (Sondagem Industrial → Consultas → Resultados/Índices → Federação → Por Atividade)
4. Preenche **5 filtros** → **Estrato** → **15 Variáveis** → **Radios** → **Orientação** (ORDEM RÍGIDA)
5. Clica **Pesquisar** → aguarda Datatable → clica **Exportar para Excel**
6. O Excel cai na pasta `Downloads` do seu usuário Windows.

### Como habilitar / desabilitar o acompanhamento visual

- **Padrão = acompanhamento LIGADO (Chrome visível):** a flag atual em [main.py](file:///g:/ic/main.py#L88-L90) é `headless=False`.
- **Desligar o acompanhamento (modo silencioso / servidor):** troque para `headless=True` no mesmo trecho.
- Implementação da flag em [driver.py::create_driver](file:///g:/ic/infrastructure/browser/driver.py#L21-L66).

### Comandos auxiliares

```powershell
# Rodar todos os 18 testes unitários
chcp 65001 ; $env:PYTHONIOENCODING="utf-8" ; pytest tests\ -v --tb=short

# Limpar cache Python (resolve erros de bytecode antigo / "passo() missing fn")
Get-ChildItem -Recurse -Directory -Filter __pycache__ g:\ic |
  Where-Object { $_.FullName -notmatch '\\\.venv\\' } |
  Remove-Item -Recurse -Force

# Verificar sintaxe de todos os 64 arquivos .py do projeto
python -c "import os, py_compile, sys;
pastas=['config','core','domain','infrastructure','pages','services','tests','.'];
erros=0; total=0
for p in pastas:
    for r,_,a in os.walk(p):
        if '.venv' in r or '__pycache__' in r: continue
        for f in a:
            if f.endswith('.py'):
                total+=1
                cam=os.path.join(r,f)
                try: py_compile.compile(cam, doraise=True)
                except Exception as e: erros+=1; print(f'ERRO: {cam}: {e}')
print(f'Total={total}  Erros={erros}'); sys.exit(0 if erros==0 else 1)"
```

### Resultado esperado após rodar `python main.py`

- Terminal imprime uma linha por fase (finaliza com `SUCESSO: pipeline completo finalizado em X.Xs.`).
- Chrome fica ABERTO e visível o tempo todo (você acompanha tudo).
- Ao final, o arquivo Excel do export cai na pasta **`Downloads`** do seu usuário Windows
  (exemplo: `C:\Users\Jardheson\Downloads\Indices_da_Sondagem_Industrial_*.xlsx`).

---

## Estrutura do Projeto (7 Camadas)

```
g:\ic\
├── main.py                       # Entry point < 200 linhas (Lock + Watchdog + Whitelist)
├── config/                       # Fail-fast .env e constantes
│   ├── settings.py               #   CfgSettings Pydantic + validação permissões .env
│   └── constants.py              #   IDs PrimeFaces, mapeamentos, URL Whitelist
├── core/                         # Hierarquia erros + retry + segurança + lock
│   ├── errors.py                 #   AppError / RetryableError / NavigationError / TimeoutError
│   ├── retry.py                  #   Decorator @with_retry (exponential backoff ≥3x)
│   ├── security.py               #   6 pilares: sanitize/whitelist/watchdog/env-perms
│   └── lock.py                   #   SingleInstanceLock cross-platform ms-vcrt/fcntl/fallback PID
├── domain/                       # Entidades + regras de domínio (sem Selenium)
│   ├── models.py                 #   PesquisaParams frozen Pydantic + validators
│   ├── validators.py             #   Validações mês/ano/coorte/variáveis/orientação
│   └── mappings.py               #   VAR_COD_POR_VALUE (31 códigos ↔ 15 variáveis)
├── infrastructure/               # Drivers técnicos Selenium
│   └── browser/
│       ├── driver.py             #   create_driver/teardown_driver (Chrome options custom)
│       ├── waits.py              #   6 perfis polling AJAX + passo(fn) obrigatório
│       └── actions.py            #   JS batch checkboxes, marcar radio, helpers PrimeFaces
├── pages/ (POM)                  # Page Objects (locators PRIVADOS By.ID)
│   ├── base_page.py
│   ├── login_page.py
│   ├── menu_page.py
│   ├── parametros_page.py        #   preencher_variaveis com interseção + validação tokens
│   └── resultados_page.py
├── services/                     # Casos de uso @with_retry (NUNCA importam By/find_element)
│   ├── auth_service.py           #   FASE 1.2: logar()
│   ├── navigation_service.py     #   FASE 2: navegar_para_form_parametros()
│   └── pesquisa_service.py       #   FASE 3+4: pesquisar_exportar_excel()
├── tests/                        # 18 testes unitários pytest
│   ├── test_core_errors.py       #   7 testes
│   ├── test_core_retry.py        #   3 testes
│   └── test_domain_models.py     #   8 testes (validações PesquisaParams)
├── docs/                         # Documentação detalhada (ver abaixo)
├── .env / .env.example           # Credenciais e template
└── requirements.txt              # Dependências pip
```

---

## Documentação Detalhada

| Documento | Link |
|---|---|
| Arquitetura Clean (7 camadas, SOLID, fluxo Fases) | [ARCHITECTURE.md](file:///g:/ic/docs/ARCHITECTURE.md) |
| 6 Pilares de Segurança (JS arguments, Whitelist, Watchdog, Sanitize, .env-perms, Lock) | [SECURITY.md](file:///g:/ic/docs/SECURITY.md) |
| Mapa Técnico de Campos (IDs PrimeFaces, 15 Variáveis, Ordem Rígida) | [AUTOMACAO_MAPA_CAMPOS.md](file:///g:/ic/docs/AUTOMACAO_MAPA_CAMPOS.md) |
| Deploy + Variáveis Ambiente + Troubleshooting | [DEPLOYMENT.md](file:///g:/ic/docs/DEPLOYMENT.md) |
| Testes Pytest (18 testes / como rodar / adicionar) | [TESTING.md](file:///g:/ic/docs/TESTING.md) |
| Padrões Código / Commits / Fluxo PR | [CONTRIBUTING.md](file:///g:/ic/docs/CONTRIBUTING.md) |
| Histórico de Mudanças | [CHANGELOG.md](file:///g:/ic/docs/CHANGELOG.md) |

---

## Solução de Problemas Comuns

| Sintoma | Causa Provável | Solução |
|---|---|---|
| `ValidationError: CNI_USER/CNI_PASSWORD ausentes` | `.env` não existe ou credenciais vazias | Copie `.env.example` → `.env` e preencha com credenciais válidas da federação. |
| `TypeError: passo() missing required positional argument: 'fn'` | Bytecode `__pycache__` antigo divergente do `.py` atual | `Get-ChildItem -Recurse -Directory -Filter __pycache__ g:\ic | Remove-Item -Recurse -Force` |
| `InvalidSelectorException` em IDs com `:` | IDs PrimeFaces JSF `selectForm:coorte` tem dois-pontos inválido para CSS não escapado | Use `By.ID` (automático no POM atual; By.CSS exige escape `\\:`). |
| `RetryableError: Nenhuma variável marcada` | Painel SelectCheckboxMenu não sincronizou widget com input checked | Ver defaults ativos na tela; a automação aplica interseção + remarque forcado por tokens. |
| `URLWhitelistError` | Navegação saiu do domínio autorizado | Ajuste `URL_WHITELIST` em [constants.py](file:///g:/ic/config/constants.py) (padrão só `pesquisasconjunturais.cni.com.br`). |
| Timeout global Watchdog (padrão 60 min) | Execução travou em loop infinito / AJAX pendente | Ajuste `WATCHDOG_TIMEOUT_GLOBAL_S` em [constants.py](file:///g:/ic/config/constants.py). |
| `SingleInstanceLockError` | Outra instância do pipeline já rodando em background | Encerre a outra execução ou remova `.pipeline.lock` se travamento antigo. |
| Login "usuário não encontrado" | Credencial recusada PELA FEDERAÇÃO CNI, não é bug de código | Valide credencial manualmente no navegador; mensagem = federação recusou autenticação. |

---

## Hard Constraint: Ordem de Preenchimento FASE 3

```
5 FILTROS BÁSICOS (Coorte → Mês/Ano Início → Mês/Ano Fim)
    ↓
ESTRATO (SelectCheckboxMenu MULTISELECT)
    ↓   ← AJAX dispara carregamento de Variáveis; NUNCA inverter!
15 VARIÁVEIS (SelectCheckboxMenu MULTISELECT)
    ↓
RÁDIOS (TipoEstimativa → Exibição → Orientação LINHA/COLUNA)
    ↓
BOTÃO PESQUISAR
    ↓
DATATABLE RESULTADOS
    ↓
EXPORTAR PARA EXCEL
```

**Essa ordem é IMPOSTA pelo widget PrimeFaces (dependências AJAX) e NÃO pode ser alterada.**
