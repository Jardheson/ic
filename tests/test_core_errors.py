"""
Testes unitários hierarquia core.errors (6 asserts isinstance subclass — TR11).

Cobertura:
  AppError base            → é Exception
  RetryableError           → subclasse de AppError (retryable)
  ValidationError          → subclasse de AppError (não retry)
  BrowserError             → subclasse de RetryableError (browser transient)
  core.errors.TimeoutError → subclasse de RetryableError (timeout transient)
  NavigationError          → subclasse de AppError (não retry)
"""
from __future__ import annotations

import pytest

from core import errors as cerr


def test_apperror_eh_exception():
    exc = cerr.AppError("mensagem base")
    assert isinstance(exc, Exception)
    assert isinstance(exc, cerr.AppError)


def test_retryable_error_subclasse_apperror():
    exc = cerr.RetryableError("erro retryável")
    assert isinstance(exc, cerr.AppError)
    assert isinstance(exc, cerr.RetryableError)


def test_validation_error_subclasse_apperror():
    exc = cerr.ValidationError("erro validação — NÃO retry")
    assert isinstance(exc, cerr.AppError)
    assert isinstance(exc, cerr.ValidationError)
    assert not isinstance(exc, cerr.RetryableError)


def test_browser_error_subclasse_retryable():
    exc = cerr.BrowserError("stale / overlay / não interagível")
    assert isinstance(exc, cerr.AppError)
    assert isinstance(exc, cerr.RetryableError)
    assert isinstance(exc, cerr.BrowserError)


def test_timeout_error_subclasse_retryable():
    exc = cerr.TimeoutError("esperou demais por um elemento")
    assert isinstance(exc, cerr.AppError)
    assert isinstance(exc, cerr.RetryableError)
    assert isinstance(exc, cerr.TimeoutError)


def test_navigation_error_subclasse_apperror_nao_retry():
    exc = cerr.NavigationError("menu Por Atividade não navegou")
    assert isinstance(exc, cerr.AppError)
    assert not isinstance(exc, cerr.RetryableError)
    assert isinstance(exc, cerr.NavigationError)


def test_cause_encadeada_str():
    root = ValueError("raiz")
    exc = cerr.AppError("wrap", cause=root)
    txt = str(exc)
    assert "wrap" in txt
    assert "raiz" in txt
