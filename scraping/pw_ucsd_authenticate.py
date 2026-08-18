import json
from dotenv import load_dotenv
import os
from bs4 import BeautifulSoup
import math
import time

import asyncio
from playwright.async_api import async_playwright, Playwright


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

# Update w/ Playwright
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

# Update w/ Playwright
async def run(UCSD_USERNAME, UCSD_PASSWORD, playwright):
    chromium = playwright.chromium
    browser = await chromium.launch(
        headless=False, 
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
    


    # replace with implicit waits
    time.sleep(15000)

async def main(UCSD_USERNAME, UCSD_PASSWORD):
    async with async_playwright() as playwright:
        await run(UCSD_USERNAME, UCSD_PASSWORD, playwright)

# Update w/ Playwright
if __name__ == "__main__":
    load_dotenv()
    UCSD_USERNAME = os.environ.get("UCSD_USERNAME", "No username found")
    UCSD_PASSWORD = os.environ.get("UCSD_PASSWORD", "No password found")

    asyncio.run(main(UCSD_USERNAME, UCSD_PASSWORD))