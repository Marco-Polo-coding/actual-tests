from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def main():
    # Si tienes Chrome instalado:
    # driver = webdriver.Chrome()  # Selenium Manager se encarga del driver
    # Alternativas:
    # driver = webdriver.Edge()
    driver = webdriver.Firefox()

    try:
        # driver.get("https://the-internet.herokuapp.com/")
        driver.get("https://www.imdb.com/es-es/")

        # Espera explícita (evita time.sleep)
        wait = WebDriverWait(driver, 60)

        # Ejemplo: click en "Form Authentication"
        # link = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Form Authentication")))
        # link.click()

        # Validación simple
        # header = wait.until(EC.visibility_of_element_located((By.TAG_NAME, "h2")))
        # assert "Login Page" in header.text

        print("OK: navegación y aserción pasaron.")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
