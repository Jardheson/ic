# Contribuindo: Padrões de Código e Fluxo

> Regras obrigatórias para contribuições no projeto. Siga rigorosamente os padrões abaixo para manter Clean Architecture, SOLID e segurança 6 pilares.

---

## 1. Regra de Ouro Nº 1

> **"NÃO INVENTE."**
> - Siga o escopo definido. Se houver ambiguidade, **pergunte ao usuário** ANTES de implementar qualquer mudança não especificada.
> - Nenhuma dependência nova é adicionada sem necessidade explícita.
> - IDs PrimeFaces são extraídos do DOM real (DevTools da página) → NUNCA advinhe IDs.

---

## 2. Padrão de Commits (Conventional Commits)

Toda mensagem de commit deve seguir o padrão:
```
<tipo>(<escopo>): <descrição curta em português>

[corpo: detalhamento técnico em português, se necessário]
```

### Tipos Permitidos
| Tipo | Quando Usar |
|---|---|
| `feat` | Nova feature / funcionalidade nova (ex.: `feat(seguranca): adiciona URL whitelist em navigation`) |
| `fix` | Correção de bug (ex.: `fix(variaveis): corrige interseção defaults e valida tokens`) |
| `docs` | Mudança APENAS em documentação (README, docs/*) |
| `refactor` | Refatoração sem mudar comportamento (ex.: extrai função, renomeia variável, move módulo) |
| `perf` | Melhoria de performance (ex.: `perf(actions): substitui selenium select por early JS return 56s`) |
| `test` | Adiciona ou corrige testes unitários |
| `chore` | Tarefas de build/dependências/configuração CI, limpeza arquivos temporários |

### Exemplos Válidos
```
fix(parametros_page): corrige TypeError passo() passando fn= obrigatório
feat(seguranca): adiciona SEG-6 SingleInstanceLock cross-platform msvcrt/fcntl/PID
docs(readme): adiciona troubleshooting passo() + __pycache__
refactor(actions): migra marcar_radiobutton para arguments[0..2] sem concatenação
test(domain): adiciona 8 testes negativos PesquisaParams frozen
perf(variaveis): seleção JS batch 31 checkboxes em 1 chamada execute_script
chore(limpeza): remove __pycache__, .pytest_cache, diag_sem_datatable.png
```

---

## 3. Padrões de Código (Clean Code + SOLID)

### 3.1 Nomenclatura
| Item | Convenção | Exemplo |
|---|---|---|
| Módulos `.py` | `snake_case` | `pesquisa_service.py`, `parametros_page.py` |
| Classes | `PascalCase` | `PesquisaParams`, `PesquisaService`, `SingleInstanceLock` |
| Métodos / Funções | `snake_case` | `preencher_variaveis()`, `marcar_radiobutton_primefaces()` |
| Constantes | `UPPER_SNAKE_CASE` | `URL_WHITELIST`, `WATCHDOG_TIMEOUT_GLOBAL_S` |
| Locators privados Page Object | `_LOCATOR_<NOME>` | `_LOCATOR_COORTE_INPUT = (By.ID, "...")` |
| Variáveis privadas classe | `_variavel_privada` prefixo `_` | `_driver`, `_params` |

### 3.2 Formatação
- Máximo de ~120 chars por linha (ajustar se precisar mas evite >160).
- 2 linhas em branco entre funções nível módulo.
- 1 linha em branco antes de `return`; 1 linha entre blocos `if/try/for`.
- Strings em `duplas aspas` por padrão; `aspas simples` só se necessário (ex.: string interna JS).
- **f-strings** para interpolação; NÃO usar `%s` ou `+` para concatenar mensagens de log (exceto concatenação de grande performance).
- `typing`: use **type hints** em TODO parâmetro de função e retorno público.
```python
# Correto
def marcar_radiobutton_primefaces(
    driver: webdriver.Chrome,
    table_id: str,
    value_alvo: str | int,
    timeout_geral: int = 20,
) -> bool:
    ...

# Ruim
def MarcarRadio(driver, tableId, valorAlvo, timeoutGeral=20):
    ...
```

---

## 4. Regras Arquiteturais Obrigatórias (Clean Arch)

### 4.1 Estrutura de Camadas (NÃO QUEBRAR)
```
main.py (entry)
    ↓ usa
services/ (Casos de Uso)
    ↓ usa (NUNCA By/find_element!)
pages/ (Page Object) + domain/ (entidades Selenium-free) + config/ + core/
    ↓ usa
infrastructure/browser/ (driver técnico Selenium)
```

### 4.2 Regras Por Camada

#### PROIBIDO EM services/
```python
# NUNCA faça isso em services
from selenium.webdriver.common.by import By
driver.find_element(By.ID, "selectForm:pesquisar").click()
```
#### PERMITIDO EM services/
```python
# Delega para Page Object
pesquisa_page.clicar_pesquisar()
```

#### PROIBIDO EM domain/
```python
# NUNCA importe Selenium na camada de domínio
from selenium import webdriver
```
Camada domain deve ser 100% offline testável sem Chrome/Selenium.

#### PROIBIDO EM pages/ (POM)
```python
# Locators NÃO são públicos!
LOCATOR_COORTE = ...  # público → viola POM; services NÃO deve saber locators
```
#### PADRÃO POM
```python
# Locators PRIVADOS prefixo _LOCATOR_; métodos públicos de ALTO NÍVEL
class ParametrosPage(BasePage):
    _LOCATOR_COORTE_INPUT = (By.ID, constants.LOCATOR_PARAM_COORTE_INPUT)

    def preencher_coorte(self, valor: str) -> None:
        selecionar_valor(self._driver, self._LOCATOR_COORTE_INPUT, valor, ...)
```

---

## 5. Hard Constraints Quebráveis Apenas Com Aprovação

| Restrição | Justificativa |
|---|---|
| **Ordem FASE 3: 5 filtros → Estrato → Variáveis → Radios → Orientação** | AJAX do PrimeFaces carrega opções de Variáveis SÓ após Estrato ser selecionado. Inverter = valores vazios, erro 404 pesquisa. |
| **`passo(fn: Callable)` espera função posicional.** | Implementação atual registra tempo só quando há fn callable real. Chamar `passo(driver, "título", "não-função")` → `TypeError`. |
| **`PesquisaParams` frozen Pydantic** | Objeto imutável = thread-safe + nenhum serviço altera parâmetros no meio do pipeline. |
| **@with_retry ≥ 3 em todos métodos service.** | Portais JSF/PrimeFaces têm AJAX inconsistente; 1 tentativa = taxa falha ~30%. 3 tentativas = < 1%. |
| **`By.ID` para IDs JSF `selectForm:XXX`.** | IDs com dois-pontos `:` em CSS exigem escape `\\:`. By.ID é nativo, não precisa. |
| **SEG-1: NENHUMA concatenação Python→JS.** | Risco injeção de código. Todo `execute_script` usa `arguments[0..N]`. Ver [SECURITY.md](file:///g:/ic/docs/SECURITY.md). |

---

## 6. Fluxo de Alteração Recomendado

Sempre que alterar algo, siga os passos nesta ordem:
```mermaid
flowchart LR
    A[1. Analisar DOM Real<br/>DevTools se mudar IDs] --> B[2. Alterar constants.py<br/>se novo ID]
    B --> C[3. Implementar na camada<br/>correta (Page/Infra/Service/Core)]
    C --> D[4. Limpar __pycache__]
    D --> E[5. py_compile sintaxe<br/>todos arquivos]
    E --> F[6. pytest tests<br/>18/18 passed]
    F --> G[7. Rodar main.py pipeline<br/>completo 1x]
    G --> H[8. Validar saídas:<br/>logs TOKENS 15/15 + Excel baixado]
    H --> I[9. Commit mensagem<br/>Conventional Commits]
```

### Comandos Passo 4-6 (Copiar/Colar)
```powershell
# (4) Limpa __pycache__ (evita TypeError passo)
Get-ChildItem -Recurse -Directory -Filter __pycache__ . | Remove-Item -Recurse -Force

# (5) Compilação sintática
python -m compileall -q .

# (6) Testes unitários offline
pytest tests/ -v --tb=short
```

---

## 7. Variáveis / Indicadores Novos

Se for adicionar **nova variável de produção nova** (hoje: 15 da p1..p11):
1. Abra Chrome DevTools no site real → Encontre `<input type=checkbox>` da variável nova → copie `value` real (ex.: `9XX`).
2. Mapeie código interno (ex.: `p12`) no `VAR_COD_POR_VALUE` de [mappings.py](file:///g:/ic/domain/mappings.py).
3. Adicione na lista `DEFAULT_VARIAVEIS_CODIGOS` de [constants.py](file:///g:/ic/config/constants.py) se for padrão.
4. Rode `pytest tests/test_domain_models.py` para validar `codigos_variaveis` não quebrando.
5. Rode pipeline completo 1x e confira: `TOKENS ✅ 16/16` ou quantia nova.

**NUNCA** crie valores de checkbox fictícios. Todos valores de `value` devem ser extraídos do HTML real.

---

## 8. Segurança em PRs

Antes de abrir uma alteração, confira a checklist de segurança:
- [ ] **SEG-1:** Todo novo `execute_script` usa `arguments[0..N]`? Nenhuma f-string ou `+ var +` em string JS?
- [ ] **SEG-2:** Nova navegação `driver.get` tem `assert_url_whitelist` depois?
- [ ] **SEG-4:** Todo `print(exc)` passa por `sanitize_log_message()` antes de exibir?
- [ ] **SEG-5:** Novo método de leitura `.env` não faz `print` de `CNI_PASSWORD` real?
- [ ] **SEG-6:** Se alterar entry point, mantém `SingleInstanceLock` context manager?
- [ ] Nenhum segredo hard-coded no código? (Tudo vem de `.env`.)

Se algum item acima for `NÃO`, **corrija antes de commitar.**

---

## 9. Code Review Checklist (antes de "aprovado")

1. **Arquitetura:** Mudança está na camada correta? Services não importam By/find_element?
2. **Tipagem:** Funções públicas tem type hints?
3. **Testes:** Validadores/domain novos têm teste positivo e negativo?
4. **Segurança:** Passou checklist 8 acima?
5. **Documentação:** Mudança requer atualização de README / AUTOMACAO_MAPA_CAMPOS / SECURITY?
6. **Smokes:** `py_compile` exit 0 + `pytest 18 passed` na máquina do autor?
7. **Commit:** Mensagem segue Conventional Commits tipo(escopo): descrição pt-BR?
