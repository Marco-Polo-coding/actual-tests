from drivers.webdrivers.WebdriverFactory import WebdriverFactory

driver = WebdriverFactory.create_from_properties()
base_url = WebdriverFactory.get_param("url")  # o "base_url" si lo cambias


def main():
    try:
        driver.get(base_url)
        
    finally:
        driver.quit()