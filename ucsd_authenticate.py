import json
from dotenv import load_dotenv
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import math
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

def get_page_href(pid, max_pid):
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

    # pid=122 with max_pid=127
    # ctl_num = (144-22)+4 = 126
    # ctl_num = (126-6)%20 + 6 = 6
    # => ctl_num = 6
    # shift = (130 - 127) * 2 = 6
    # => ctl_num = 12

    ctl_num = 2*pid
    if pid > 11:
        ctl_num = (ctl_num - 22) + 4 # account for leading ... and re-reading ctl04, which was already shown from the prior ctl24

        ctl_num = (ctl_num - 6) % 20 + 6 # iterate on trailing ...


    shift = 10 * math.ceil(max_pid / 10) - max_pid
    if pid > 11 and max_pid - pid < 10 - shift - 1:
        full_shift = shift * 2
        print(f"full_shift = {full_shift}")
        print(f"ctl_num originally = {ctl_num}")
        ctl_num = (ctl_num+full_shift-6) % 20 + 6
        print(f"ctl_num now = {ctl_num}")

    return rf"javascript:__doPostBack('ctl00$MainContent$ResultRadGrid$ctl00$ctl03$ctl01$ctl{ctl_num:02}','')"

def get_offset(page_start: int, page_end:int) -> int:
    """
    Skips the lists of pages which do not contain page_start or page_end

        Args:
        page_start: start page number (1-indexed)
        page_end: end page number (1-indexed)
                  page_end - page_start <= 10 when page_end >11

    Returns:
        offset: integer number of pages to skip (0-indexed)
    """
    if page_start <= page_end <= 11:
        return 0

    offset = math.ceil((page_end - 11) / 10) + 1 # not in first page of 11

    return offset

    

def get_page_list(page_start: int, page_end: int, max_page: int, driver):
    """
    Retrieve a set of pages based on absolute starting and ending page numbers

    Args:
        page_start: start page number (1-indexed)
        page_end: end page number (1-indexed)
                  Assumes page_start and page_end are properly assigned when passed

    Returns:
        pages_subset: a dictionary containing up to 11 page numbers
    """
    # offset can be functionalized
    offset = get_offset(page_start, page_end)

    # go to new page list
    for list_pid in range(offset):
        if list_pid == 0:
            curr_page_href = get_page_href(10, max_page) # no leading previous page element on first list
        else:
            curr_page_href = get_page_href(10*list_pid+1, max_page) # offset 1 to account for leading previous page list `...`

        page_field = driver.find_element(By.XPATH, f"""//a[@href="{curr_page_href}"]""")
        page_field.click()

        time.sleep(5)

    pages_subset = dict()

    # scrape page list
    for pid in range(page_start, page_end+1):
        curr_page_href = get_page_href(pid, max_page)
        print(f"Visiting page: {pid}. href = {curr_page_href}")
        # save current page
        page_field = driver.find_element(By.ID, "ctl00_MainContent_ResultRadGrid_ctl00")
        page_content = page_field.get_attribute("innerHTML")
        pages_subset[pid] = page_content

        # update to next page
        next_page_field = driver.find_element(By.XPATH, f"""//a[@href="{curr_page_href}"]""")
        try:
            next_page_field.click()
            # url doesn't change, but data takes a few seconds to update
            # try replacing with implicit wait 
            time.sleep(5) 
        except Exception as e:
            print(e)

    return pages_subset


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

        # page number
        pages_field = driver.find_element(By.CSS_SELECTOR, ".rgWrap.rgInfoPart")
        pages_html = pages_field.get_attribute("innerHTML")
        pages_soup = BeautifulSoup(pages_html)
        try:
            # total number of pages
            num_pages = int(pages_soup.find_all("strong")[1].text)
        except Exception as e:
            print("Failed to parse number of pages")
            raise e

        print(f"There are a total of {num_pages} pages")
        num_page_seq = get_offset(0, num_pages)
        print(f"There will be {num_page_seq} page lists")
        for page_seq in range(0,num_page_seq):
            # Restart 25 viewings counter in new window
            driver.switch_to.new_window('tab')
            driver.get(url)
            time.sleep(5)
            search_all(driver)
            time.sleep(5)

            if page_seq == 0:
                if num_pages <= 11:
                    start, end = 1, num_pages
                else:
                    start, end = 1, 11
            else:
                start, end = 10*page_seq + 2, min(10*page_seq + 11, num_pages)

            print(f"Start = {start}, End = {end}")
            curr_page_list = get_page_list(start, end, num_pages, driver)
            # pages have unique identifiers so update is lossless
            pages.update(curr_page_list)

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