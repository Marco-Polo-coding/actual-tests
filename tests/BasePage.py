from drivers.webdrivers.WebdriverFactory import WebdriverFactory
from drivers.webdrivers.AuxiliaryMethods import AuxiliaryMethods as AM

class BasePage:
    def __init__(self, driver=None):
        self.driver = driver or WebdriverFactory.create_from_properties()
        self.base_url = WebdriverFactory.get_param("url")

    def open_home(self):
        self.driver.get(self.base_url)
        return self

    def go_to(self, path: str):
        # path tipo "/login"
        url = self.base_url.rstrip("/") + "/" + path.lstrip("/")
        self.driver.get(url)
        return self

    # Opcional: exponer AM para que tus Pages hagan self.AM.click(...)
    AM = AM

    def quit(self):
        self.driver.quit()
