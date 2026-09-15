"""
Gerenciamento do ciclo de vida do WebDriver (Chrome Selenium).

- SEM estado global: driver é criado, passado por DI e destruído explicitamente.
- Wraps exceções do Selenium em core.errors.BrowserError (retryable).
- BrowserDriver context manager opcional para uso com `with`.

Compatibilidade: Selenium 4.49.0 (pinado em requirements.txt).
"""
from __future__ import annotations

from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.webdriver import WebDriver as ChromeWebDriver

from core.errors import BrowserError


def create_driver(
    *,
    headless: bool = False,
    extra_options: Optional[list[str]] = None,
) -> ChromeWebDriver:
    """
    Cria uma instância do Chrome WebDriver com opções padrão de automação.

    Args:
        headless: Se True, roda sem interface gráfica (--headless=new).
        extra_options: Lista de argumentos adicionais para o Chrome.

    Returns:
        Instância pronta de webdriver.Chrome.

    Raises:
        BrowserError: Se ocorrer qualquer erro ao instanciar o driver.
    """
    try:
        options = ChromeOptions()

        # Flags de desempenho e estabilidade para automação RPA
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--start-maximized")
        options.add_argument("--remote-allow-origins=*")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        if headless:
            options.add_argument("--headless=new")

        if extra_options:
            for opt in extra_options:
                options.add_argument(opt)

        driver = webdriver.Chrome(options=options)
        driver.maximize_window()
        return driver

    except Exception as exc:  # noqa: BLE001 - queremos wrapar TUDO em BrowserError
        raise BrowserError(
            "Falha ao criar instância do Chrome WebDriver",
            cause=exc,
        ) from exc


def teardown_driver(driver: Optional[ChromeWebDriver]) -> None:
    """
    Encerra o WebDriver de forma segura, sem lançar exceções.

    Ideal para bloco `finally:` — garante que o navegador fecha
    mesmo em caso de erro na pipeline.
    """
    if driver is None:
        return
    try:
        driver.quit()
    except Exception:  # noqa: BLE001 - melhor esforço, ignore erros no quit
        pass


class BrowserDriver:
    """
    Context manager conveniente para criar e destruir o driver automaticamente.

    Uso:
        with BrowserDriver() as driver:
            driver.get(URL_BASE)
            ...
    """

    def __init__(
        self,
        *,
        headless: bool = False,
        extra_options: Optional[list[str]] = None,
    ):
        self._headless = headless
        self._extra_options = extra_options
        self._driver: Optional[ChromeWebDriver] = None

    def __enter__(self) -> ChromeWebDriver:
        self._driver = create_driver(
            headless=self._headless,
            extra_options=self._extra_options,
        )
        return self._driver

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        teardown_driver(self._driver)
        self._driver = None


__all__ = [
    "create_driver",
    "teardown_driver",
    "BrowserDriver",
]
