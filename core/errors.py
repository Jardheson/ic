"""
Hierarquia de exceções da aplicação.

AppError(Exception)
├─ RetryableError (erros transitórios passíveis de @with_retry)
│   ├─ BrowserError
│   └─ TimeoutError (sobrecarrega built-in? → NÃO, usamos nome único core.errors.TimeoutError nosso)
├─ ValidationError (NÃO retryable, erro de validação de domínio/config)
└─ NavigationError (quebra de fluxo de tela, NÃO retry via @with_retry por padrão)
"""
from __future__ import annotations

from typing import Optional


class AppError(Exception):
    """Exceção base de nível de aplicação. Todas as exceções específicas herdam daqui."""

    def __init__(self, message: str, *, cause: Optional[BaseException] = None):
        super().__init__(message)
        self.message: str = message
        self.cause: Optional[BaseException] = cause

    def __str__(self) -> str:
        if self.cause is None:
            return self.message
        return f"{self.message} (causa: {type(self.cause).__name__}: {self.cause}"

    def __repr__(self) -> str:
        return f"{type(self).__name__}(message={self.message!r}, cause={self.cause!r})"


class RetryableError(AppError):
    """Erro transitório passível de nova tentativa via decorator @with_retry."""
    pass


class ValidationError(AppError):
    """Erro de validação de entrada/domínio/configuração. NÃO é retryable (retry não vai resolver)."""
    pass


class BrowserError(RetryableError):
    """Erro transitório originado no navegador/DOM (StaleElement, ElementNotInteractable, etc.)."""
    pass


class TimeoutError(RetryableError):  # noqa: A001 - sombreia built-in de propósito; namespace é um AppError
    """Tempo máximo de espera excedido em alguma operação que pode se resolver sozinha."""
    pass


class NavigationError(AppError):
    """Erro no fluxo de navegação/pipeline (não consegue chegar a tela esperada, regra de negócio quebrada etc.)."""
    pass


__all__ = [
    "AppError",
    "RetryableError",
    "ValidationError",
    "BrowserError",
    "TimeoutError",
    "NavigationError",
]
