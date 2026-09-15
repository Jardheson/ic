"""
MenuPage: Tela de navegação pós-login (FASE 2).

Fluxo de menus exatamente como no monólito:
  Sondagem Industrial (botão) → hover Consultas → hover Resultados →
  hover Federação → clicar Por Atividade (turbo com Function.call).

Usa helpers de actions/waits para cada passo (hover_em, clicar_por_atividade_turbo).
"""
from __future__ import annotations

from selenium.webdriver.common.by import By

from pages.base_page import BasePage
from infrastructure.browser.waits import (
    passo_hover_menu,
    passo_clique_menu,
    aguardar_pagina_pronta,
    aguardar_navegacao,
)
from infrastructure.browser.actions import (
    clicar_com_retry,
    hover_em,
    clicar_por_atividade_turbo,
)
from config.constants import (
    LOCATOR_MENU_SONDAGEM_INDUSTRIAL,
    LOCATOR_MENU_CONSULTAS,
    LOCATOR_MENU_RESULTADOS,
    LOCATOR_MENU_FEDERACAO,
)


def _parse_locator(loc):
    """Converte (tipo, valor) de constants.py para tupla By.XXX pronta."""
    by_str, val = loc
    mapping = {
        "css": By.CSS_SELECTOR,
        "xpath": By.XPATH,
        "id": By.ID,
    }
    return (mapping.get(by_str.lower(), By.CSS_SELECTOR), val)


class MenuPage(BasePage):
    """Tela do menu principal após login (FASE 2)."""

    _LOCATOR_SONDAGEM_BTN = _parse_locator(LOCATOR_MENU_SONDAGEM_INDUSTRIAL)
    _LOCATOR_CONSULTAS = _parse_locator(LOCATOR_MENU_CONSULTAS)
    _LOCATOR_RESULTADOS = _parse_locator(LOCATOR_MENU_RESULTADOS)
    _LOCATOR_FEDERACAO = _parse_locator(LOCATOR_MENU_FEDERACAO)

    # ------------------------------------------------------------------
    # API pública: uma função por passo da FASE 2
    # ------------------------------------------------------------------

    def clicar_sondagem_industrial(self) -> None:
        passo_clique_menu(
            self._driver,
            "Selecionar pesquisa → Sondagem Industrial",
            lambda: clicar_com_retry(self._driver, self._LOCATOR_SONDAGEM_BTN, tentativas=3),
            depois_nav=False,
        )

    def hover_consultas(self) -> None:
        passo_hover_menu(
            self._driver,
            "Hover → Consultas",
            lambda: hover_em(self._driver, self._LOCATOR_CONSULTAS, tentativas=3),
            locator_proximo=self._LOCATOR_RESULTADOS,
        )

    def hover_resultados(self) -> None:
        passo_hover_menu(
            self._driver,
            "Hover → Resultados / Índices",
            lambda: hover_em(self._driver, self._LOCATOR_RESULTADOS, tentativas=3),
            locator_proximo=self._LOCATOR_FEDERACAO,
        )

    def hover_federacao(self) -> None:
        passo_hover_menu(
            self._driver,
            "Hover → Federação",
            lambda: hover_em(self._driver, self._LOCATOR_FEDERACAO, tentativas=3),
            locator_proximo=None,
        )

    def clicar_por_atividade(self) -> bool:
        """
        Clica em "Por Atividade" (ultimo passo da FASE 2).
        Usa `clicar_por_atividade_turbo` com Function.call(window) no onclick handler.

        Returns:
            True se navegação ocorreu (campos selectForm existem na próxima tela).
        """
        print("Clicar Por Atividade (submit menuForm) ...", flush=True)
        t0 = __import__("time").time()
        ok = clicar_por_atividade_turbo(self._driver, timeout_geral=20)
        dt = __import__("time").time() - t0
        if ok:
            print(f"Por Atividade ({dt:.2f}s) → navegou para tela de parâmetros.", flush=True)
        else:
            print(f"Por Atividade ({dt:.2f}s) → NÃO conseguiu navegar.", flush=True)
        return ok


__all__ = ["MenuPage"]
