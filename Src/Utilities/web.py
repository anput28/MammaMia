import os.path
from urllib.parse import urlparse

import httpx
from playwright.async_api import async_playwright

from Src.Utilities.config import SC_DOMAIN

chromium_path = "/usr/bin/chromium"
#chromium_path = os.path.join(os.getcwd(), "chrome-win", "chrome.exe")


class RequestManager:
    def __init__(self, with_cookie: bool = True):
        self.with_cookie = with_cookie
        self.cookies = None
        self.cookies_header = None

    async def __fetch_cookies(self):
        print("Fetch new cookies")
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True,
                                                   executable_path=chromium_path,
                                                   args=["--no-sandbox", '--disable-gpu', '--disable-dev-shm-usage'])

        context = await browser.new_context()

        await context.request.get(f"https://streamingcommunity.{SC_DOMAIN}")
        self.cookies = await context.cookies()
        self.cookies_header = "; ".join(f"{cookie['name']}={cookie['value']}" for cookie in self.cookies)

        await browser.close()
        await playwright.stop()

    async def get(self, api: str, more_headers: dict = None, get_json: bool = True):
        if (not self.cookies_header) and self.with_cookie:
            await self.__fetch_cookies()

        async with httpx.AsyncClient() as client:
            parsed_url = urlparse(api)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
                "Accept": "application/json" if get_json else "text/html",
                "Referer": base_url,
                "Origin": base_url,
            }

            if self.with_cookie:
                headers.update({"Cookie": self.cookies_header, })

            if more_headers is not None:
                headers.update(more_headers)

            response = await client.get(api, headers=headers)

            if self.with_cookie:
                if response.status_code == 401 or response.status_code == 403:
                    await self.__fetch_cookies()
                    return await self.get(api, more_headers, get_json)

            return response.json() if get_json else response.text
