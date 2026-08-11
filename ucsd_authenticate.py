import json
from dotenv import load_dotenv
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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

# replacing with a class would be cleaner
# driver --> this.driver
# username/password --> this.username, this.password

def login(UCSD_USERNAME, UCSD_PASSWORD, driver):
    username_field = driver.find_element(By.ID, "ssousername")
    password_field = driver.find_element(By.ID, "ssopassword")

    driver.execute_script(f"arguments[0].value = '{UCSD_USERNAME}'", username_field)
    driver.execute_script(f"arguments[0].value = '{UCSD_PASSWORD}'", password_field)
    password_field.send_keys(Keys.ENTER)

def search_all(driver):
    transaction_start_field = driver.find_element(By.ID, "ctl00_MainContent_BeginRadDateTimePicker_dateInput")
    driver.execute_script("arguments[0].value = '1/1/2000 12:00 AM'", transaction_start_field)

    search_button = driver.find_element(By.ID, "MainContent_ContinueButton")
    search_button.click()

def get_page_href(pid):
    """
    Args:
        pid: 1-indexed
    """

    # first page list: 1 to 10, 11
        # I want to grab 1 through 11 (11 pages)
        # ctl02-ctl22
    # middle page list: 10, 11 to 20, 21
        # I want to grab 12 through 21 (10 pages)
        # ctl06 - ctl24
    # middle page list: 20, 21 to 30, 31
        # I want to grab 22 through 31 (10 pages)
        # ctl06 - ctl24
    # middle page list: etc. (10 pages)
    # last page: _0 _1 to __ (< 10 pages)
    # 22 - 6, 32 - 26
    # 23 - 8, 33 - 28
    # 24 - 10, 34 - 30
    # 25 - 12, 35 - 32
    # 26 - 14, 36 - 34
    # 27 - 16, 37 - 36
    # 28 - 18, 38 - 38
    # 29 - 20, 39 - 40
    # 30 - 22, 40 - 42
    # 31 - 24, 41 - 44

    ctl_num = 2*pid
    if pid > 11:
        ctl_num = (ctl_num - 22) + 4 # account for leading ... and re-reading ctl04, which was already shown from the prior ctl24

        ctl_num = (ctl_num - 6) % 20 + 6 # iterate on trailing ...

    return rf"javascript:__doPostBack('ctl00$MainContent$ResultRadGrid$ctl00$ctl03$ctl01$ctl{ctl_num:02}','')"


def main(UCSD_USERNAME, UCSD_PASSWORD, options=Options()):
    with webdriver.Chrome(options) as driver:
        url = load_url()
        driver.get(url)

        login(UCSD_USERNAME, UCSD_PASSWORD, driver)

        # replace with implicit waits
        time.sleep(15)

        # Search for all transactions
        search_all(driver)

        # replace with implicit waits
        time.sleep(5)

        # Pull data for all pages
        pages = dict()
        pid = 1

        # page number
        curr_page_href = get_page_href(pid)

        
        pages_field = driver.find_element(By.CSS_SELECTOR, ".rgWrap.rgInfoPart")
        pages_html = pages_field.get_attribute("innerHTML")
        pages_soup = BeautifulSoup(pages_html)
        try:
            # total number of pages
            num_pages = int(pages_soup.find_all("strong")[1].text)
        except Exception as e:
            print("Failed to parse number of pages")
            raise e

        while pid < num_pages:
            print(f"Visiting page: {pid}. href = {curr_page_href}")
            # save current page
            page_field = driver.find_element(By.ID, "ctl00_MainContent_ResultRadGrid_ctl00")
            page_content = page_field.get_attribute("innerHTML")
            pages[pid] = page_content

            #update to next page
            pid += 1
            curr_page_href = get_page_href(pid)
            next_page_field = driver.find_element(By.XPATH, f"""//a[@href="{curr_page_href}"]""")
            try:
                next_page_field.click()
                # url doesn't change, but data takes a few seconds to update
                # try replacing with implicit wait 
                time.sleep(5) 
            except Exception as e:
                print(e)


        # save all pages
        with open("data/raw.json", "w") as f:
            json.dump(pages, f)

        time.sleep(2000)

if __name__ == "__main__":
    load_dotenv()
    UCSD_USERNAME = os.environ.get("UCSD_USERNAME", "No username found")
    UCSD_PASSWORD = os.environ.get("UCSD_PASSWORD", "No password found")

    options=Options()
    options.add_argument("--start-maximized")
    main(UCSD_USERNAME, UCSD_PASSWORD, options=options)