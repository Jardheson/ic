# Testes: Pytest 18 Testes Unitários

> Estratégia de testes unitários offline (Selenium-free, não abre navegador) + regras para adicionar novos testes.

---

## Sumário Atual de Testes (18 / 18)

| Arquivo de Teste | N° Testes | Cobertura |
|---|---|---|
| [test_core_errors.py](file:///g:/ic/tests/test_core_errors.py) | **7** | Hierarquia de erros e encadeamento causa |
| [test_core_retry.py](file:///g:/ic/tests/test_core_retry.py) | **3** | Decorator @with_retry + exponential backoff |
| [test_domain_models.py](file:///g:/ic/tests/test_domain_models.py) | **8** | Validações Pydantic de `PesquisaParams` frozen |
| **TOTAL** | **18** | |

---

## Como Rodar os Testes

### PowerShell (Windows) / Bash (Linux/macOS)
```bash
cd g:\ic
# 1) Ative o ambiente virtual
.\.venv\Scripts\Activate.ps1     # Windows PowerShell
# source .venv/bin/activate      # Linux/macOS

# 2) Rodar todos os 18 testes verbose
pytest tests/ -v --tb=short

# 3) Rodar só 1 arquivo específico
pytest tests/test_domain_models.py -v

# 4) Rodar só 1 teste específico por nome
pytest tests/test_core_retry.py::test_with_retry_sucesso_segunda_tentativa -v

# 5) Gerar relatório de cobertura (se pytest-cov estiver instalado)
pip install pytest-cov
pytest tests/ --cov=config --cov=core --cov=domain --cov-report=term-missing
```

### Saída Esperada
```
============================= test session starts =============================
platform win32 -- Python 3.14.x, pytest-9.1.1
collected 18 items

tests/test_core_errors.py::test_apperror_eh_exception PASSED             [  5%]
tests/test_core_errors.py::test_retryable_error_subclasse_apperror PASSED [ 11%]
tests/test_core_errors.py::test_validation_error_subclasse_apperror PASSED [ 16%]
tests/test_core_errors.py::test_browser_error_subclasse_retryable PASSED  [ 22%]
tests/test_core_errors.py::test_timeout_error_subclasse_retryable PASSED  [ 27%]
tests/test_core_errors.py::test_navigation_error_subclasse_apperror_nao_retry PASSED [ 33%]
tests/test_core_errors.py::test_cause_encadeada_str PASSED                [ 38%]
tests/test_core_retry.py::test_with_retry_sucesso_segunda_tentativa PASSED [ 44%]
tests/test_core_retry.py::test_with_retry_esgota_tentativas_levanta_ultimo PASSED [ 50%]
tests/test_core_retry.py::test_validation_error_nao_retry PASSED          [ 55%]
tests/test_domain_models.py::test_params_valido_sem_erro PASSED           [ 61%]
tests/test_domain_models.py::test_mes_inicio_13_validation_error PASSED   [ 66%]
tests/test_domain_models.py::test_mes_fim_negativo_validation_error PASSED [ 72%]
tests/test_domain_models.py::test_orientacao_invalida_diagonal PASSED     [ 77%]
tests/test_domain_models.py::test_codigos_variaveis_vazio_validation_error PASSED [ 83%]
tests/test_domain_models.py::test_ano_fora_faixa_validation_error PASSED   [ 88%]
tests/test_domain_models.py::test_tipo_estimativa_invalido PASSED         [ 94%]
tests/test_domain_models.py::test_coorte_vazia_validation_error PASSED    [100%]

============================= 18 passed in 0.35s =============================
```

---

## Detalhamento Por Arquivo

### 1. Hierarquia de Erros — 7 testes
Arquivo: [test_core_errors.py](file:///g:/ic/tests/test_core_errors.py)

| Teste | Valida |
|---|---|
| `test_apperror_eh_exception` | `AppError` herda de `Exception`. |
| `test_retryable_error_subclasse_apperror` | `RetryableError` é subclasse de `AppError`. |
| `test_validation_error_subclasse_apperror` | `ValidationError` (core) é subclasse de `AppError`. |
| `test_browser_error_subclasse_retryable` | `BrowserError` é subclasse de `RetryableError`. |
| `test_timeout_error_subclasse_retryable` | `TimeoutError` (core) é subclasse de `RetryableError`. |
| `test_navigation_error_subclasse_apperror_nao_retry` | `NavigationError` é `AppError` mas NÃO é `RetryableError` (não deve retentar falhas de navegação). |
| `test_cause_encadeada_str` | Causa encadeada `raise AppError(...) from exc` aparece no `str()` da exceção. |

---

### 2. Retry / Backoff — 3 testes
Arquivo: [test_core_retry.py](file:///g:/ic/tests/test_core_retry.py)

| Teste | Valida |
|---|---|
| `test_with_retry_sucesso_segunda_tentativa` | Função que falha 1x e depois acerta: decorator retorna sucesso (não levanta). Backoff delay aplica. |
| `test_with_retry_esgota_tentativas_levanta_ultimo` | Função que sempre falha: após N tentativas, **levanta a ÚLTIMA exceção** (não genérica). |
| `test_validation_error_nao_retry` | `ValidationError` não está em `retry_types`: falha na 1ª tentativa, **NÃO retenta** nenhuma vez. |

---

### 3. Validações de Domínio (`PesquisaParams` frozen) — 8 testes
Arquivo: [test_domain_models.py](file:///g:/ic/tests/test_domain_models.py)

| Teste | Valida |
|---|---|
| `test_params_valido_sem_erro` | `PesquisaParams` com valores padrões **válidos**: não levanta erro. |
| `test_mes_inicio_13_validation_error` | `mes_inicio=13` (fora 1..12) → `ValidationError`. |
| `test_mes_fim_negativo_validation_error` | `mes_fim=-1` (fora 1..12) → `ValidationError`. |
| `test_orientacao_invalida_diagonal` | `orientacao="DIAGONAL"` → não é `LINHA/COLUNA` → `ValidationError`. |
| `test_codigos_variaveis_vazio_validation_error` | `codigos_variaveis=[]` vazio → `ValidationError` (pelo menos 1 variável obrigatória). |
| `test_ano_fora_faixa_validation_error` | `ano_inicio=1900` / `ano_fim=9999` → Fora faixa `2010..2100` → `ValidationError`. |
| `test_tipo_estimativa_invalido` | `tipo_estimativa=""` vazio → `ValidationError`. |
| `test_coorte_vazia_validation_error` | `coorte=""` vazio → `ValidationError`. |

---

## Como Adicionar um Novo Teste

### Regras Obrigatórias
1. **Pasta:** `g:\ic\tests\`
2. **Nome arquivo:** `test_<NOME_MODULO>.py`
3. **Nome função:** `test_<O_QUE_VALIDA>` (padrão pytest discovery)
4. **Offline:** Testes NÃO devem abrir Chrome / Selenium. Se precisar de mock Selenium, use `unittest.mock.Mock` para `webdriver.Chrome`.
5. **Cobertura:** Todo novo validator, core error ou retry behavior deve ter teste positivo e negativo.

### Exemplo Template Novo Teste
```python
# tests/test_meu_novo_modulo.py
from core.errors import ValidationError
from domain.validators import minha_validacao_nova

def test_minha_validacao_positiva():
    assert minha_validacao_nova("valor_valido") is True

def test_minha_validacao_negativa():
    try:
        minha_validacao_nova("valor_invalido!!!")
    except ValidationError:
        pass
    else:
        raise AssertionError("Deveria ter levantado ValidationError")
```

---

## Pipeline de Qualidade Recomendado
Antes de executar `python main.py` em produção, sempre rode:
```powershell
# 1) Limpa __pycache__ (evita TypeError passo / divergência bytecode)
Get-ChildItem -Recurse -Directory -Filter __pycache__ . | Remove-Item -Recurse -Force

# 2) Compilação sintática de todos módulos
python -m compileall -q .

# 3) Testes unitários offline
pytest tests/ -v --tb=short

# 4) Se tudo 0 erros → executa pipeline real
chcp 65001 ; $env:PYTHONIOENCODING="utf-8" ; python main.py
```

---

## Cobertura Atual vs. Cobertura Desejada

| Módulo | Cobertura Testes Atual | Alvo Final |
|---|---|---|
| `core/errors.py` | 100% (7 testes) | Fechado |
| `core/retry.py` | 90% (3 testes) | 100% — adicionar teste de jitter, teste de delay |
| `domain/validators.py` | 95% (8 testes indiretos via models) | Fechado |
| `domain/models.py` | 95% (8 testes frozen) | Fechado |
| `core/security.py` | 0% | ALTO RISCO — adicionar testes unitários de sanitize, whitelist parse, permissões |
| `core/lock.py` | 0% | ALTO RISCO — adicionar teste de double lock e stale PID |
| `infrastructure/**` | 0% | Testes de integração com mock Selenium (baixa prioridade) |
| `pages/**` | 0% | Testes de integração com mock Selenium (baixa prioridade) |
| `services/**` | 0% | Testes de unidade com mock Pages (prioridade média) |
