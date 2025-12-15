from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Literal, Optional

from selenium import webdriver
from selenium.common.exceptions import NoSuchDriverException, WebDriverException

from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.firefox.service import Service as FirefoxService


Browser = Literal["chrome", "edge", "firefox"]


log = logging.getLogger(__name__)

### Helpers internos
def _find_repo_root() -> Path:
    """
    Encuentra la raíz del repo (donde están /tests y /drivers).
    Tu archivo vive en: actual-tests/drivers/webdrivers/webdrivers.py
    """
    here = Path(__file__).resolve()
    for p in [here] + list(here.parents):
        if (p / "tests").is_dir() and (p / "drivers").is_dir():
            return p
    # fallback razonable
    return here.parents[2]

# --- Path al driver local
def _local_driver_path(root: Path, browser: Browser) -> Path:
    if browser == "chrome":
        return root / "drivers" / "chromedriver-win64" / "chromedriver.exe"
    if browser == "edge":
        return root / "drivers" / "edge" / "msedgedriver.exe"
    if browser == "firefox":
        return root / "drivers" / "firefox" / "geckodriver.exe"
    raise ValueError("browser debe ser: chrome | edge | firefox")

# -- Función principal
def make_driver(
    browser: Browser = "chrome",
    *,
    headless: bool = False,
    prefer_manager: bool = True,
    implicit_wait_s: float = 0,
) -> webdriver.Remote:
    """
    Crea un WebDriver.
    - Primero intenta Selenium Manager (si prefer_manager=True).
    - Si falla (red capada, proxy, etc.), usa el driver local de /drivers.

    Selenium Manager y su configuración (proxy/offline/cache) están documentados por Selenium. :contentReference[oaicite:1]{index=1}
    """
    browser = browser.lower()  # type: ignore
    root = _find_repo_root()
    driver_path = _local_driver_path(root, browser)

    # --- Opciones (headless, etc.)
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

    # --- 1) Intento Selenium Manager
    if prefer_manager:
        try:
            d = manager_ctor()
            if implicit_wait_s:
                d.implicitly_wait(implicit_wait_s)
            return d
        except (NoSuchDriverException, WebDriverException) as e:
            # Esto es el caso típico cuando Selenium Manager no puede descargar por red/proxy. :contentReference[oaicite:2]{index=2}
            log.warning("Selenium Manager falló (%s). Fallback a driver local: %s", e.__class__.__name__, driver_path)

    # --- 2) Fallback local
    if not driver_path.exists():
        raise FileNotFoundError(f"No encuentro el driver local para {browser}: {driver_path}")

    d = local_ctor()
    if implicit_wait_s:
        d.implicitly_wait(implicit_wait_s)
    return d

# -- Helper desde env vars
def make_driver_from_env(default: Browser = "chrome") -> webdriver.Remote:
    """
    Helper: elige navegador desde env var BROWSER=chrome|edge|firefox.
    """
    browser = os.getenv("BROWSER", default).lower()
    if browser not in ("chrome", "edge", "firefox"):
        browser = default
    prefer_manager = os.getenv("SELENIUM_PREFER_MANAGER", "1") not in ("0", "false", "False")
    headless = os.getenv("HEADLESS", "0") in ("1", "true", "True")
    return make_driver(browser, headless=headless, prefer_manager=prefer_manager)
