"""
Testes unitários @with_retry decorator (core/retry.py — TR11).

Cenário: função que levanta BrowserError (retryable DEFAULT_RETRY_ON)
         na 1a tentativa, retorna 42 na 2a. Decorated com max_attempts=3.
Resultado esperado: retorna 42; time.sleep chamado ≤2 vezes (1o delay entre 1a→2a;
                    não há 3a tentativa pois sucesso na 2a).
"""
from __future__ import annotations

import time
import pytest

from core.retry import with_retry
from core.errors import BrowserError


def test_with_retry_sucesso_segunda_tentativa(monkeypatch):
    sleep_calls: list[float] = []

    def fake_sleep(d: float) -> None:
        sleep_calls.append(d)

    monkeypatch.setattr(time, "sleep", fake_sleep)

    contagem = {"n": 0}

    @with_retry(max_attempts=3, initial_delay=0.05, backoff_factor=2.0, jitter=0.0)
    def instavel() -> int:
        contagem["n"] += 1
        if contagem["n"] < 2:
            raise BrowserError("simulando browser transient")
        return 42

    resultado = instavel()

    assert resultado == 42
    assert contagem["n"] == 2
    assert len(sleep_calls) <= 2, (
        f"esperado ≤2 sleep (1 delay antes da 2a tentativa); "
        f"tiveram {len(sleep_calls)}: {sleep_calls}"
    )


def test_with_retry_esgota_tentativas_levanta_ultimo(monkeypatch):
    sleep_calls: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda d: sleep_calls.append(d))

    @with_retry(max_attempts=3, initial_delay=0.01, backoff_factor=1.5, jitter=0.0)
    def sempre_falha() -> int:
        raise BrowserError("sempre bad")

    with pytest.raises(BrowserError) as exc_info:  # type: ignore[name-defined]
        sempre_falha()
    assert "sempre bad" in str(exc_info.value)
    assert len(sleep_calls) == 2  # delays entre tentativas 1→2 e 2→3 (após 3a falha: retorna)


def test_validation_error_nao_retry(monkeypatch):
    """ValidationError não está em DEFAULT_RETRY_ON → NÃO retentar."""
    from core.errors import ValidationError

    tentativas = {"n": 0}
    sleep_calls: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda d: sleep_calls.append(d))

    @with_retry(max_attempts=3)
    def falha_validacao() -> int:
        tentativas["n"] += 1
        raise ValidationError("campo ruim — não retry")

    with pytest.raises(ValidationError):  # type: ignore[name-defined]
        falha_validacao()
    assert tentativas["n"] == 1, f"ValidationError NÃO devia retentar; tentou {tentativas['n']}x"
    assert sleep_calls == []
