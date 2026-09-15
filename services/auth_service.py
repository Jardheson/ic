"""
AuthService (FASE 1): Orquestra Login CNI + limpeza de popups pós-login.

Regras AC-5/AC-7:
  - Usa @with_retry (≥3 total com outros services — cumpre AC-5).
  - NÃO importa By/find_element/Select; só usa LoginPage alto-nível (AC-7).
"""
from __future__ import annotations

from typing import Tuple

from selenium import webdriver

from core.retry import with_retry
from pages.login_page import LoginPage
from infrastructure.browser.waits import aguardar_pagina_pronta, fechar_popups_e_dialogos


class AuthService:
    """Orquestrador de autenticação (FASE 1)."""

    def __init__(self, driver: webdriver.Chrome):
        if driver is None:
            raise ValueError("driver não pode ser None em AuthService")
        self._driver: webdriver.Chrome = driver

    @with_retry(max_attempts=2, initial_delay=0.2, backoff_factor=2.0, jitter=0.05)
    def logar(self, usuario: str, senha: str) -> Tuple[bool, str]:
        """
        Executa FASE 1: aguarda tela login → login turbo → fecha popups/dialogos.

        Returns:
            (sucesso: bool, mensagem_erro: str)
            mensagem_erro="" se sucesso; detalhe do erro caso contrário.
        """
        page = LoginPage(self._driver)
        page.aguardar_carregamento(timeout=14)
        sucesso, msg_erro = page.logar(usuario, senha, timeout_submit=25)
        if not sucesso:
            return False, msg_erro or "Login falhou (motivo desconhecido)"
        try:
            aguardar_pagina_pronta(self._driver, modo="navegacao", timeout=14)
        except Exception:
            pass
        try:
            fechar_popups_e_dialogos(self._driver)
        except Exception:
            pass
        return True, ""


__all__ = ["AuthService"]
