"""
LoginPage: Tela de autenticação CNI (FASE 1).

Encapsula preenchimento de usuário/senha e submissão do formulário.
Usa o helper `fazer_login_turbo` de infrastructure/browser/actions.py
(3 estratégias de preenchimento, 2 tentativas, detecção de erro de credencial).
"""
from __future__ import annotations

from typing import Tuple

from selenium.webdriver.common.by import By

from pages.base_page import BasePage
from infrastructure.browser.waits import (
    aguardar_tela_inicial,
)
from infrastructure.browser.actions import fazer_login_turbo


class LoginPage(BasePage):
    """Tela de login da CNI (form loginForm)."""

    # Locators são privados! Services NUNCA vêem esses valores.
    _LOCATOR_FORM = (By.ID, "loginForm")

    # ------------------------------------------------------------------
    # API pública de alto nível
    # ------------------------------------------------------------------

    def aguardar_carregamento(self, timeout: int = 14) -> None:
        """Espera DOM interativo + presença do campo senha."""
        aguardar_tela_inicial(self._driver, timeout=timeout)

    def logar(self, usuario: str, senha: str, *, timeout_submit: int = 25) -> Tuple[bool, str]:
        """
        Executa login usando `fazer_login_turbo` (3 estratégias).

        Returns:
            (sucesso: bool, mensagem_erro: str)
        """
        return fazer_login_turbo(self._driver, usuario, senha, timeout_submit=timeout_submit)


__all__ = ["LoginPage"]
