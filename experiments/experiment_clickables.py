""" <a rel="noopener noreferrer" class="notion-link" style="display: inline; color: inherit; text-decoration: underline; user-select: none; cursor: pointer;">proceed anyway</a>
"""

import asyncio
from playwright.async_api import async_playwright

URL = "https://utat-ss.notion.site/Data-Processing-661606034b8b4598bc5a13a822d27b7c"


async def experiment_proceed_anyway() -> None:
    """Experiment clicking the "proceed anyway" link on a Notion page.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        
        context = await browser.new_context(
            user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                )
        )

        page = await context.new_page()
        await page.goto(URL)

        await asyncio.sleep(2)  # Wait to fully load the page

        # Click the "proceed anyway" link if exists:
        link_to_click = await page.query_selector("text=proceed anyway")
        if link_to_click:
            await link_to_click.click()
            await asyncio.sleep(1000)  # Wait to observe the result
            return
        
        await browser.close()

    print("No 'proceed anyway' link found.")
    return 

if __name__ == "__main__":
    try:
        asyncio.run(experiment_proceed_anyway())
    except KeyboardInterrupt:
        print("Experiment interrupted.")
    