"""
BasePage: base para todos os Page Objects do padrão POM.

Regras:
- `self._driver` é PRIVADO (underscore prefix) e NUNCA é exposto para services.
- Locators são atributos de classe `_LOCATOR_XXX` também privados.
- Métodos públicos de alto nível operam em cima de helpers internos.
- Pages NUNCA devem ser instanciadas sem um driver válido.
"""
from __future__ import annotations

from typing import Optional, Tuple

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    StaleElementReferenceException,
    ElementNotInteractableException,
    TimeoutException as SeleniumTimeoutException,
)

from infrastructure.browser.waits import (
    _elemento_habilitado,
    aguardar_pagina_pronta,
    esperar_estavel,
)


class BasePage:
    """Classe base para todos os Page Objects."""

    _DEFAULT_TIMEOUT: int = 12

    def __init__(self, driver: webdriver.Chrome):
        if driver is None:
            raise ValueError("driver não pode ser None em BasePage")
        self._driver: webdriver.Chrome = driver
        self._wait: WebDriverWait = WebDriverWait(driver, self._DEFAULT_TIMEOUT)
        self._short_wait: WebDriverWait = WebDriverWait(driver, 5)
        self._ultra_short_wait: WebDriverWait = WebDriverWait(driver, 3, poll_frequency=0.02)

    # ------------------------------------------------------------------
    # Helpers internos de baixo nível (usados só pelas subclasses)
    # ------------------------------------------------------------------

    def _find(self, locator, *, many: bool = False):
        """Localiza elemento(s) com retry leve contra stale."""
        last_err = None
        for _ in range(2):
            try:
                if many:
                    return self._driver.find_elements(*locator)
                return self._driver.find_element(*locator)
            except StaleElementReferenceException as exc:
                last_err = exc
                import time
                time.sleep(0.05)
        raise last_err if last_err else RuntimeError(f"_find falhou: {locator}")

    def _find_safe(self, locator, *, many: bool = False):
        """Versão segura (sem exceção) de _find; retorna None/lista vazia."""
        try:
            return self._find(locator, many=many)
        except Exception:
            return [] if many else None

    def _click_by_id(self, element_id: str) -> None:
        """Clica via `By.ID` (evita problema CSS `:` em JSF)."""
        loc = (By.ID, element_id)
        esperar_estavel(self._driver, loc, timeout=4)
        for tent in range(3):
            try:
                el = self._ultra_short_wait.until(EC.element_to_be_clickable(loc))
                if not _elemento_habilitado(el):
                    import time
                    time.sleep(0.05)
                    continue
                try:
                    self._driver.execute_script(
                        "try { arguments[0].click(); return true; } catch(e){ return false; }",
                        el,
                    )
                    return
                except Exception:
                    el.click()
                    return
            except (StaleElementReferenceException, ElementNotInteractableException, SeleniumTimeoutException):
                import time
                time.sleep(0.05)
        raise RuntimeError(f"BasePage._click_by_id falhou: {element_id}")

    def _aguardar_pronta(self, modo: str = "normal", **kw) -> None:
        aguardar_pagina_pronta(self._driver, modo=modo, **kw)

    def _wait_presence(self, locator, timeout: Optional[int] = None):
        t = timeout if timeout is not None else self._DEFAULT_TIMEOUT
        return WebDriverWait(self._driver, t).until(EC.presence_of_element_located(locator))

    def _wait_visible(self, locator, timeout: Optional[int] = None):
        t = timeout if timeout is not None else self._DEFAULT_TIMEOUT
        return WebDriverWait(self._driver, t).until(EC.visibility_of_element_located(locator))

    def _wait_clickable(self, locator, timeout: Optional[int] = None):
        t = timeout if timeout is not None else self._DEFAULT_TIMEOUT
        return WebDriverWait(self._driver, t).until(EC.element_to_be_clickable(locator))


__all__ = ["BasePage"]
