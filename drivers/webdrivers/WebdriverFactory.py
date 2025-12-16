from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Literal

from selenium import webdriver
from selenium.common.exceptions import NoSuchDriverException, WebDriverException

from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.firefox.service import Service as FirefoxService


Browser = Literal["chrome", "edge", "firefox"]
log = logging.getLogger(__name__)


class WebdriverFactory:
    """
    Factory para crear drivers en local:

    Plan A (preferido): Selenium Manager (webdriver.Chrome()/Edge()/Firefox()).
    Plan B (fallback): usar ejecutables locales en /drivers vía Service(executable_path=...).

    La forma correcta (Selenium 4) de pasar una ruta de driver local es mediante Service. :contentReference[oaicite:3]{index=3}
    """

    @staticmethod
    def _find_repo_root() -> Path:
        here = Path(__file__).resolve()
        # Busca un padre que contenga /tests y /drivers
        for p in [here] + list(here.parents):
            if (p / "tests").is_dir() and (p / "drivers").is_dir():
                return p
        # fallback razonable (webdrivers -> drivers -> repo)
        return here.parents[2]

    @staticmethod
    def _local_driver_path(root: Path, browser: Browser) -> Path:
        if browser == "chrome":
            return root / "drivers" / "chromedriver-win64" / "chromedriver.exe"
        if browser == "edge":
            return root / "drivers" / "edge" / "msedgedriver.exe"
        if browser == "firefox":
            return root / "drivers" / "firefox" / "geckodriver.exe"
        raise ValueError("browser debe ser: chrome | edge | firefox")

    @staticmethod
    def create_driver(
        browser: Browser = "chrome",
        *,
        headless: bool = False,
        prefer_manager: bool = True,
        implicit_wait_s: float = 0,
        page_load_timeout_s: float | None = None,
        script_timeout_s: float | None = None,
    ) -> webdriver.Remote:
        """
        Crea un driver listo para usar.

        Consejo: deja implicit_wait_s=0 y usa solo esperas explícitas (WebDriverWait).
        Selenium advierte que no se mezclen implicit + explicit. :contentReference[oaicite:4]{index=4}
        """
        browser = browser.lower()  # type: ignore
        root = WebdriverFactory._find_repo_root()
        driver_path = WebdriverFactory._local_driver_path(root, browser)

        # Opciones + constructores (Plan A y Plan B)
        if browser == "chrome":
            options = webdriver.ChromeOptions()
            if headless:
                options.add_argument("--headless=new")
            manager_ctor = lambda: webdriver.Chrome(options=options)
            local_ctor = lambda: webdriver.Chrome(
                service=ChromeService(executable_path=str(driver_path)),
                options=options,
            )

        elif browser == "edge":
            options = webdriver.EdgeOptions()
            if headless:
                options.add_argument("--headless=new")
            manager_ctor = lambda: webdriver.Edge(options=options)
            local_ctor = lambda: webdriver.Edge(
                service=EdgeService(executable_path=str(driver_path)),
                options=options,
            )

        elif browser == "firefox":
            options = webdriver.FirefoxOptions()
            if headless:
                options.add_argument("-headless")
            manager_ctor = lambda: webdriver.Firefox(options=options)
            local_ctor = lambda: webdriver.Firefox(
                service=FirefoxService(executable_path=str(driver_path)),
                options=options,
            )
        else:
            raise ValueError("browser debe ser: chrome | edge | firefox")

        # --- Plan A: Selenium Manager
        if prefer_manager:
            try:
                d = manager_ctor()
                WebdriverFactory._apply_timeouts(
                    d,
                    implicit_wait_s=implicit_wait_s,
                    page_load_timeout_s=page_load_timeout_s,
                    script_timeout_s=script_timeout_s,
                )
                return d
            except (NoSuchDriverException, WebDriverException) as e:
                log.warning(
                    "Selenium Manager falló (%s). Fallback a driver local: %s",
                    e.__class__.__name__,
                    driver_path,
                )

        # --- Plan B: driver local
        if not driver_path.exists():
            raise FileNotFoundError(f"No encuentro el driver local para {browser}: {driver_path}")

        d = local_ctor()
        WebdriverFactory._apply_timeouts(
            d,
            implicit_wait_s=implicit_wait_s,
            page_load_timeout_s=page_load_timeout_s,
            script_timeout_s=script_timeout_s,
        )
        return d

    @staticmethod
    def _apply_timeouts(
        driver: webdriver.Remote,
        *,
        implicit_wait_s: float,
        page_load_timeout_s: float | None,
        script_timeout_s: float | None,
    ) -> None:
        if implicit_wait_s:
            driver.implicitly_wait(implicit_wait_s)
        if page_load_timeout_s is not None:
            driver.set_page_load_timeout(page_load_timeout_s)
        if script_timeout_s is not None:
            driver.set_script_timeout(script_timeout_s)

    @staticmethod
    def create_from_env(default: Browser = "chrome") -> webdriver.Remote:
        """
        Env vars:
          - BROWSER=chrome|edge|firefox
          - HEADLESS=1|0
          - SELENIUM_PREFER_MANAGER=1|0
          - IMPLICIT_WAIT_S=0 (recomendado)
        """
        browser = os.getenv("BROWSER", default).lower()
        if browser not in ("chrome", "edge", "firefox"):
            browser = default

        headless = os.getenv("HEADLESS", "0") in ("1", "true", "True")
        prefer_manager = os.getenv("SELENIUM_PREFER_MANAGER", "1") not in ("0", "false", "False")

        implicit_wait_s = float(os.getenv("IMPLICIT_WAIT_S", "0"))

        return WebdriverFactory.create_driver(
            browser, headless=headless, prefer_manager=prefer_manager, implicit_wait_s=implicit_wait_s
        )
