import json
from dotenv import load_dotenv
import os
from bs4 import BeautifulSoup
import math
import asyncio
from playwright.async_api import async_playwright
import sys

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


async def login(UCSD_USERNAME, UCSD_PASSWORD, page):
    username_field = page.locator("#ssousername")
    password_field = page.locator("#ssopassword")

    await username_field.fill(UCSD_USERNAME)
    await password_field.fill(UCSD_PASSWORD)

    login_button = page.locator("""button[type="submit"]""")
    await login_button.click()


async def duo_login(page):
    user_device_button = page.get_by_text(r"No, other people use this device")
    await user_device_button.click()


async def search_all(page):
    transaction_start_field = page.locator("#ctl00_MainContent_BeginRadDateTimePicker_dateInput")
    await transaction_start_field.fill("1/1/2000 12:00 AM")

    search_button = page.locator("#MainContent_ContinueButton")
    await search_button.click()


def get_page_href(pid, max_pid):
    """
    Args:
        pid: 1-indexed
    """
    # continue instead of re-reading first page (this is the same page as the previous page list from `...`)
    ctl_num = 2*pid 
    if pid > 11:
        # account for leading ... and repeated 11, 21, 31, etc. from trailiing ... on previous page
        ctl_num = (ctl_num - 22) + 4 
        # iterate on trailing ...
        ctl_num = (ctl_num - 6) % 20 + 6 


    shift = 10 * math.ceil(max_pid / 10) - max_pid
    if pid > 11 and max_pid - pid < 10 - shift - 1:
        full_shift = shift * 2
        ctl_num = (ctl_num+full_shift-6) % 20 + 6

    # print(f"pid = {pid}, ctl_num = {ctl_num}")
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

    offset = math.ceil((page_end - 11) / 10) 

    return offset


async def wait_for_table_update(page, page_href):
    page_field = page.locator("#ctl00_MainContent_ResultRadGrid_ctl00")
    page_content = await page_field.inner_html()

    next_page_field = page.locator(f"""a[href="{page_href}"]""")
    await next_page_field.click()

    await page.wait_for_function(
        """
        oldHTML => {
            const grid = document.querySelector("#ctl00_MainContent_ResultRadGrid_ctl00");
            return grid && grid.innerHTML !== oldHTML;
        }
        """,
        arg=page_content
    )


async def get_page_list(page_start: int, page_end: int, max_page: int, page):
    """
    Retrieve a set of pages based on absolute starting and ending page numbers

    Args:
        page_start: start page number (1-indexed)
        page_end: end page number (1-indexed)
                  Assumes page_start and page_end are properly assigned when passed

    Returns:
        pages_subset: a dictionary containing up to 11 page numbers
    """
    offset = get_offset(page_start, page_end)

    # go to new page list
    for list_pid in range(offset):
        if list_pid == 0:
            curr_page_href = get_page_href(11, max_page) # no leading previous page element on first list
        else:
            curr_page_href = get_page_href(10*list_pid+11, max_page) # offset 1 to account for leading previous page list `...`

        # wait for table to fill to update before continuing
        await wait_for_table_update(page, curr_page_href)

    pages_subset = dict()

    # scrape page list (i.e. a set of pages)
    for pid in range(page_start, page_end+1):
        # if the page number is page_start, then the page will stall as the table has already been loaded and will not update
        if pid != 1 and (offset != 0 or pid > page_start):
            curr_page_href = get_page_href(pid, max_page)
            print(f"Visiting page: {pid}")
            # print(f"Visiting page: {pid}. href = {curr_page_href}")
            await wait_for_table_update(page, curr_page_href)
            
        grid_locator = page.locator("#ctl00_MainContent_ResultRadGrid_ctl00")
        pages_subset[pid] = await grid_locator.inner_html()

    return pages_subset


def get_page_range(page_seq, total_num_pages):
    if page_seq == 0:
        if total_num_pages <= 11:
            start, end = 1, total_num_pages
        else:
            start, end = 1, 11
    else:
        start, end = 10*page_seq + 2, min(10*page_seq + 11, total_num_pages)
    return start, end


async def process_sequence(page_seq, num_pages, context, url, semaphore):
    async with semaphore:
        tab = await context.new_page()
        try:
            await tab.goto(url)
            await search_all(tab)
            start, end = get_page_range(page_seq, num_pages)
            curr_page_list = await get_page_list(start, end, num_pages, tab)
            return curr_page_list
        finally:
            await tab.close()


async def run(UCSD_USERNAME, UCSD_PASSWORD, playwright, n_tabs):
    chromium = playwright.chromium
    browser = await chromium.launch(
        headless=True, 
        args = [
            "--start-maximized",
        ],
    )
    context = await browser.new_context(no_viewport=True)
    page = await context.new_page()

    url = load_url()
    await page.goto(url)

    await login(UCSD_USERNAME, UCSD_PASSWORD, page)
    await duo_login(page)

    # Search for all transactions
    await search_all(page)

    # # Pull data for all pages
    pages = dict()

    # page number
    pages_field = page.locator(".rgWrap.rgInfoPart")
    pages_html = await pages_field.inner_html()
    pages_soup = BeautifulSoup(pages_html, features="html.parser")
    try:
        # total number of pages
        num_pages = int(pages_soup.find_all("strong")[1].text)
    except Exception as e:
        print("Failed to parse number of pages")
        raise e

    print(f"There are {num_pages} pages")
    num_page_seq = get_offset(0, num_pages) + 1 # first page is not offset
    print(f"There will be {num_page_seq} page lists") 

    # no point in having more workers than pages
    n_tabs = min(n_tabs, num_pages)
    semaphore = asyncio.Semaphore(n_tabs)
    tasks = [
        process_sequence(page_seq, num_pages, context, url, semaphore) for page_seq in range(num_page_seq)
    ]
    results = await asyncio.gather(*tasks)

    pages = dict()
    for page_list in results:
        pages.update(page_list)

    # save all pages
    with open("data/raw.json", "w") as f:
        json.dump(pages, f)


async def main(UCSD_USERNAME, UCSD_PASSWORD, n_tabs=1):
    async with async_playwright() as playwright:
        await run(UCSD_USERNAME, UCSD_PASSWORD, playwright, n_tabs=n_tabs)


if __name__ == "__main__":
    load_dotenv()
    UCSD_USERNAME = os.environ.get("UCSD_USERNAME", "No username found")
    UCSD_PASSWORD = os.environ.get("UCSD_PASSWORD", "No password found")

    # if > 15 workers there may be unrelated errors as there are 10 items per page and ~25 total queries allowed = 15 offset queries => 15 workers produces max degree of parallelism
    n_tabs = min(int(sys.argv[1]), 15)
    asyncio.run(main(UCSD_USERNAME, UCSD_PASSWORD, n_tabs=n_tabs))