from drivers.webdrivers.WebdriverFactory import make_driver

driver = make_driver("chrome")  # o "edge" / "firefox"

url = "localhost:3000"

def main():
    try:
        driver.get(url)
        wait = WebDriverWait(driver, 10)
    finally:
        driver.quit()