from __future__ import annotations

import os
from typing import Tuple, Optional

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


Locator = Tuple[str, str]  # (By.ID, "foo") etc.

DEFAULT_TIMEOUT = int(os.getenv("SELENIUM_TIMEOUT", "10"))
DEFAULT_POLL = float(os.getenv("SELENIUM_POLL", "0.2"))


class AuxiliaryMethods:
    """
    Helpers “reusables” de Selenium basados en esperas explícitas:
    WebDriverWait + expected_conditions. :contentReference[oaicite:5]{index=5}
    """

    @staticmethod
    def wait(driver: WebDriver, timeout: int = DEFAULT_TIMEOUT) -> WebDriverWait:
        return WebDriverWait(driver, timeout=timeout, poll_frequency=DEFAULT_POLL)

    @staticmethod
    def wait_present(driver: WebDriver, locator: Locator, timeout: int = DEFAULT_TIMEOUT) -> WebElement:
        return AuxiliaryMethods.wait(driver, timeout).until(EC.presence_of_element_located(locator))

    @staticmethod
    def wait_visible(driver: WebDriver, locator: Locator, timeout: int = DEFAULT_TIMEOUT) -> WebElement:
        return AuxiliaryMethods.wait(driver, timeout).until(EC.visibility_of_element_located(locator))

    @staticmethod
    def wait_clickable(driver: WebDriver, locator: Locator, timeout: int = DEFAULT_TIMEOUT) -> WebElement:
        return AuxiliaryMethods.wait(driver, timeout).until(EC.element_to_be_clickable(locator))

    @staticmethod
    def wait_invisible(driver: WebDriver, locator: Locator, timeout: int = DEFAULT_TIMEOUT) -> bool:
        return AuxiliaryMethods.wait(driver, timeout).until(EC.invisibility_of_element_located(locator))

    @staticmethod
    def click(driver: WebDriver, locator: Locator, timeout: int = DEFAULT_TIMEOUT) -> None:
        el = AuxiliaryMethods.wait_clickable(driver, locator, timeout)
        el.click()

    @staticmethod
    def type_text(
        driver: WebDriver,
        locator: Locator,
        text: str,
        *,
        clear: bool = True,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        el = AuxiliaryMethods.wait_visible(driver, locator, timeout)
        if clear:
            el.clear()
        el.send_keys(text)

    @staticmethod
    def get_text(driver: WebDriver, locator: Locator, timeout: int = DEFAULT_TIMEOUT) -> str:
        el = AuxiliaryMethods.wait_visible(driver, locator, timeout)
        return el.text

    @staticmethod
    def exists(driver: WebDriver, locator: Locator, timeout: int = 2) -> bool:
        try:
            AuxiliaryMethods.wait_present(driver, locator, timeout)
            return True
        except TimeoutException:
            return False

    @staticmethod
    def wait_url_contains(driver: WebDriver, fragment: str, timeout: int = DEFAULT_TIMEOUT) -> bool:
        return AuxiliaryMethods.wait(driver, timeout).until(EC.url_contains(fragment))
