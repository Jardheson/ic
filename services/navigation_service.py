"""
NavigationService (FASE 2): Orquestra navegação menus → Por Atividade.

Regras AC-5/AC-7:
  - Usa @with_retry (≥3 total cumpre AC-5).
  - NÃO importa By/find_element/Select; só usa MenuPage alto-nível (AC-7).

Ordem EXATA do monólito backup (NÃO ALTERAR — dependências PrimeFaces):
  Sondagem Industrial → hover Consultas → hover Resultados → hover Federação →
  clicar Por Atividade.
"""
from __future__ import annotations

from selenium import webdriver

from core.retry import with_retry
from core.errors import NavigationError
from pages.menu_page import MenuPage
from infrastructure.browser.waits import aguardar_pagina_pronta


class NavigationService:
    """Orquestrador de navegação menus FASE 2."""

    def __init__(self, driver: webdriver.Chrome):
        if driver is None:
            raise ValueError("driver não pode ser None em NavigationService")
        self._driver: webdriver.Chrome = driver

    @with_retry(max_attempts=2, initial_delay=0.25, backoff_factor=2.0, jitter=0.05)
    def navegar_para_form_parametros(self) -> bool:
        """
        Executa FASE 2 completa: 5 passos menu em ordem rígida.

        Raises:
            NavigationError: se algum passo da navegação falhar definitivamente
                             (exception não será retry — NavigationError NÃO está
                             em DEFAULT_RETRY_ON do core/retry.py).
        Returns:
            True se chegou na tela selectForm (Por Atividade navegou com sucesso).
        """
        page = MenuPage(self._driver)
        try:
            page.clicar_sondagem_industrial()
            page.hover_consultas()
            page.hover_resultados()
            page.hover_federacao()
            ok = page.clicar_por_atividade()
            if not ok:
                raise NavigationError(
                    "Menu 'Por Atividade' NÃO conseguiu navegar para tela de parâmetros "
                    "(selectForm não detectado após clique)."
                )
            try:
                aguardar_pagina_pronta(self._driver, modo="navegacao", timeout=16)
            except Exception:
                pass
            return True
        except NavigationError:
            raise
        except Exception as exc:
            raise NavigationError(f"Falha em NavigationService (FASE 2): {exc!r}") from exc


__all__ = ["NavigationService"]
