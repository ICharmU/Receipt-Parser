import json
from dotenv import load_dotenv
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.chrome.options import Options
import time


def load_url():
    """
    Load url string from json which requires UCSD SSO redirection
    """
    with open("auth_url.json") as f:
        auth_url = json.load(f)

    url = auth_url["url"]
    return url


def main(UCSD_USERNAME, UCSD_PASSWORD, options=Options()):
    url = load_url()
    driver = webdriver.Chrome(options)
    driver.get(url)

    username_field = driver.find_element(By.ID, "ssousername")
    password_field = driver.find_element(By.ID, "ssopassword")

    driver.execute_script(f"arguments[0].value = '{UCSD_USERNAME}'", username_field)
    driver.execute_script(f"arguments[0].value = '{UCSD_PASSWORD}'", password_field)
    password_field.send_keys(Keys.ENTER)

    time.sleep(200)
    driver.quit()

if __name__ == "__main__":
    load_dotenv()
    UCSD_USERNAME = os.environ.get("UCSD_USERNAME", "No username found")
    UCSD_PASSWORD = os.environ.get("UCSD_PASSWORD", "No password found")

    options=Options()
    options.add_argument("--start-maximized")
    main(UCSD_USERNAME, UCSD_PASSWORD, options=options)