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


# Tipado literal para los navegadores soportados
Browser = Literal["chrome", "edge", "firefox"]
# Logger del módulo
log = logging.getLogger(__name__)


class WebdriverFactory:
    """
    Factory para crear instancias de `webdriver.Remote`.

    Estrategia:
      - Plan A: intentar con Selenium Manager (gestiona drivers automáticamente)
      - Plan B: fallback a un driver local situado en la carpeta `drivers/`

    Provee utilidades para leer configuración desde
    `elements/parametrization.properties` y para sobreescribir con
    variables de entorno (útil en CI).
    """

    # Caché de parámetros leídos desde el fichero .properties
    _param_cache: dict[str, str] | None = None

    # ---------- config (.properties) ----------
    @staticmethod
    def _find_repo_root() -> Path:
        # Busca hacia arriba en los padres del archivo hasta encontrar
        # un directorio que contenga tanto `tests` como `drivers`.
        here = Path(__file__).resolve()
        for p in [here] + list(here.parents):
            if (p / "tests").is_dir() and (p / "drivers").is_dir():
                return p
        # Fallback razonable si no encuentra la estructura esperada
        return here.parents[2]

    @staticmethod
    def _properties_path() -> Path:
        # Ruta al fichero de parametrización relativo a la raíz del repo
        root = WebdriverFactory._find_repo_root()
        return root / "elements" / "parametrization.properties"

    @staticmethod
    def _read_properties(path: Path) -> dict[str, str]:
        """
        Parser simple de archivos estilo Java `.properties`.
        - Ignora líneas vacías y comentarios que empiezan por `#` o `;`.
        - Espera pares `key=value` y recorta espacios.
        """
        data: dict[str, str] = {}
        if not path.exists():
            raise FileNotFoundError(f"No existe el fichero de parametrización: {path}")

        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or line.startswith(";"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip()
        return data

    @staticmethod
    def load_parametrization(force_reload: bool = False) -> dict[str, str]:
        # Carga y cachea los parámetros desde el fichero .properties
        if WebdriverFactory._param_cache is None or force_reload:
            WebdriverFactory._param_cache = WebdriverFactory._read_properties(WebdriverFactory._properties_path())
        return WebdriverFactory._param_cache

    @staticmethod
    def get_param(key: str, default: str | None = None) -> str | None:
        # Lectura puntual de un parámetro (usa la caché)
        return WebdriverFactory.load_parametrization().get(key, default)

    @staticmethod
    def _as_bool(v: str | None, default: bool = False) -> bool:
        # Convierte cadenas comunes a booleano
        if v is None:
            return default
        return v.strip().lower() in ("1", "true", "yes", "y", "on")

    @staticmethod
    def _as_float(v: str | None, default: float | None = None) -> float | None:
        # Convierte una cadena a float, respetando un valor por defecto
        if v is None or v.strip() == "":
            return default
        return float(v)

    @staticmethod
    def _overlay_env(params: dict[str, str]) -> dict[str, str]:
        """
        Permite sobreescribir valores del fichero con variables de entorno
        si `CONFIG_PRECEDENCE=env`. Esto facilita la configuración en CI.
        """
        precedence = os.getenv("CONFIG_PRECEDENCE", "file").strip().lower()
        if precedence != "env":
            return params  # hoy manda el .properties

        # Mapeo de keys internas -> nombres de env vars
        mapping = {
            "browser": "BROWSER",
            "url": "BASE_URL",
            "headless": "HEADLESS",
            "prefer_manager": "SELENIUM_PREFER_MANAGER",
            "timeout": "TIMEOUT",
            "page_load_timeout": "PAGE_LOAD_TIMEOUT",
            "script_timeout": "SCRIPT_TIMEOUT",
            "window": "WINDOW",
            "se_proxy": "SE_PROXY",
            "se_cache_path": "SE_CACHE_PATH",
            "se_offline": "SE_OFFLINE",
        }

        merged = dict(params)
        for k, envk in mapping.items():
            val = os.getenv(envk)
            if val is not None and val != "":
                merged[k] = val
        return merged

    # ---------- drivers ----------
    @staticmethod
    def _local_driver_path(root: Path, browser: Browser) -> Path:
        # Devuelve la ruta esperada del ejecutable del driver local según el navegador
        if browser == "chrome":
            return root / "drivers" / "chromedriver-win64" / "chromedriver.exe"
        if browser == "edge":
            return root / "drivers" / "edge" / "msedgedriver.exe"
        if browser == "firefox":
            return root / "drivers" / "firefox" / "geckodriver.exe"
        raise ValueError("browser debe ser: chrome | edge | firefox")

    @staticmethod
    def create_from_properties() -> webdriver.Remote:
        """
        Lee la configuración desde `elements/parametrization.properties`, aplica
        posibles sobreescrituras por env vars y crea el `webdriver` según
        los parámetros (browser, headless, timeouts, window, etc.).
        """
        params = WebdriverFactory.load_parametrization()
        params = WebdriverFactory._overlay_env(params)

        # Determina el navegador a usar, con validación básica
        browser = (params.get("browser", "chrome") or "chrome").lower()
        if browser not in ("chrome", "edge", "firefox"):
            browser = "chrome"
        browser = browser  # type: ignore

        # Flags y preferencias
        headless = WebdriverFactory._as_bool(params.get("headless"), default=False)
        prefer_manager = WebdriverFactory._as_bool(params.get("prefer_manager"), default=True)

        # Timeouts: usa `timeout` como fallback si no se especifican por separado
        timeout_fallback = WebdriverFactory._as_float(params.get("timeout"), default=None)
        page_load_timeout = WebdriverFactory._as_float(params.get("page_load_timeout"), default=timeout_fallback)
        script_timeout = WebdriverFactory._as_float(params.get("script_timeout"), default=timeout_fallback)

        # Configuración de entorno para Selenium Manager (proxy/cache/offline)
        if params.get("se_proxy"):
            os.environ["SE_PROXY"] = params["se_proxy"]
        if params.get("se_cache_path"):
            os.environ["SE_CACHE_PATH"] = params["se_cache_path"]
        if params.get("se_offline"):
            os.environ["SE_OFFLINE"] = params["se_offline"]

        # Crea el driver (puede lanzar si algo falla)
        driver = WebdriverFactory.create_driver(
            browser,  # type: ignore
            headless=headless,
            prefer_manager=prefer_manager,
            implicit_wait_s=0,  # recomendado: usar esperas explícitas con WebDriverWait
            page_load_timeout_s=page_load_timeout,
            script_timeout_s=script_timeout,
        )

        # Opcional: ajustar el tamaño/estado de la ventana según `window` en config
        window = (params.get("window") or "").strip().lower()
        if window == "maximize":
            driver.maximize_window()
        elif "x" in window:
            w, h = window.split("x", 1)
            if w.isdigit() and h.isdigit():
                driver.set_window_size(int(w), int(h))

        return driver

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
        Crea el `webdriver` concreto para el `browser` indicado.

        - Construye opciones específicas por navegador (p.ej. modo headless).
        - Define dos constructorres: `manager_ctor` (Selenium Manager) y
          `local_ctor` (driver local usando `Service(executable_path=...)`).
        - Si `prefer_manager` está activado intenta primero el manager y
          hace fallback al driver local si falla.
        """
        browser = browser.lower()  # type: ignore
        root = WebdriverFactory._find_repo_root()
        driver_path = WebdriverFactory._local_driver_path(root, browser)

        # Configuración por navegador: opciones y constructores
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

        # Intento con Selenium Manager si está preferido
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
                # Si falla el manager, se registra la razón y se continúa con local
                log.warning(
                    "Selenium Manager falló (%s). Fallback a driver local: %s",
                    e.__class__.__name__,
                    driver_path,
                )

        # Verifica que exista el ejecutable local antes de intentar usarlo
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
        # Aplica timeouts al driver si están definidos
        if implicit_wait_s:
            driver.implicitly_wait(implicit_wait_s)
        if page_load_timeout_s is not None:
            driver.set_page_load_timeout(page_load_timeout_s)
        if script_timeout_s is not None:
            driver.set_script_timeout(script_timeout_s)
