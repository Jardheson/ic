"""
Decorator @with_retry com backoff exponencial + jitter para ações de navegador transitórias.
Uso:
    @with_retry(max_attempts=3, initial_delay=0.05, backoff_factor=2.0, jitter=0.02,
                retry_on=(RetryableError, StaleElementReferenceException, ...))
    def clicar_algo(...):
        ...
"""
from __future__ import annotations

import functools
import random
import time
from typing import Any, Callable, Iterable, Optional, Tuple, Type

from selenium.common.exceptions import (
    ElementNotInteractableException,
    StaleElementReferenceException,
    TimeoutException as SeleniumTimeoutException,
)

from core.errors import RetryableError


ExcT = Tuple[Type[BaseException], ...] | Type[BaseException]


DEFAULT_RETRY_ON: tuple[type[BaseException], ...] = (
    RetryableError,
    StaleElementReferenceException,
    ElementNotInteractableException,
    SeleniumTimeoutException,
)


def with_retry(
    max_attempts: int = 3,
    initial_delay: float = 0.05,
    backoff_factor: float = 2.0,
    jitter: float = 0.02,
    retry_on: Iterable[type[BaseException]] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator de retry com backoff exponencial + jitter uniforme.

    Parâmetros
    ----------
    max_attempts:
        Número total de tentativas. 3 = 1ª tentativa + 2 retries.
    initial_delay:
        Espera (segundos) na primeira espera (após 1ª falha, antes da 2ª tentativa.
    backoff_factor:
        Multiplicador por tentativa. delay_attempt_k = initial_delay * (backoff_factor ** (k-2)) + jitter_uniforme.
    jitter:
        Range de aleatoriedade adicionada ao backoff (uniform(0, jitter)) p/ evitar thundering herd.
    retry_on:
        Tupla de exceções que disparam retry. Default: RetryableError + Selenium transientes.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts precisa ser >= 1")

    retry_types: tuple[type[BaseException], ...]
    if retry_on is None:
        retry_types = DEFAULT_RETRY_ON
    else:
        retry_types = tuple(retry_on) if not isinstance(retry_on, tuple) else retry_on  # type: ignore[assignment]

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: BaseException | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except BaseException as exc:  # noqa: BLE001 — captura tudo, mas só propaga retry_types
                    # não propaga IMEDIATAMENTE se não for do tipo desejado OU for a última tentativa
                    is_retryable = False
                    try:
                        is_retryable = isinstance(exc, retry_types)
                    except Exception:  # pragma: no cover
                            is_retryable = False
                    if not is_retryable or attempt == max_attempts:
                        raise
                    last_exc = exc
                    # Backoff exponencial + jitter uniforme
                    expoente = max(0, attempt - 1)  # attempt=1 (primeira tentativa não chega aqui)
                    # attempt=2 (2ª tentativa) → expoente=1
                    atraso = (
                        initial_delay * (backoff_factor ** expoente)
                        + random.uniform(0, max(0.0, jitter))
                    )
                    if atraso > 0:
                        time.sleep(atraso)
            # unreachable (última tentativa raise acima sempre)
            raise last_exc  # pragma: no cover

        return wrapper

    return decorator


__all__ = ["with_retry", "DEFAULT_RETRY_ON"]
