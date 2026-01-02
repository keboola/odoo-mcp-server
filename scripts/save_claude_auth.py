#!/usr/bin/env python3
"""
Save Claude.ai Authentication State

Options:
  1. Use system Chrome (fresh session)
  2. Copy cookies from your running Chrome (no need to close it!)

Setup:
    pip install playwright browser-cookie3
    playwright install

Usage:
    python save_claude_auth.py                     # Fresh Chrome session
    python save_claude_auth.py --copy-cookies      # Copy cookies from running Chrome!
    python save_claude_auth.py --browser msedge    # Use Edge instead
"""

import argparse
import asyncio
import json
import platform
from pathlib import Path

STATE_DIR = Path(__file__).parent / ".playwright-state"
STATE_FILE = STATE_DIR / "claude_auth.json"


def get_chrome_cookies_for_domain(domain: str) -> list:
    """Extract cookies from running Chrome for a specific domain."""
    try:
        import browser_cookie3
    except ImportError:
        print("Install browser_cookie3: pip install browser-cookie3")
        return []

    cookies = []
    try:
        # This works even while Chrome is running!
        chrome_cookies = browser_cookie3.chrome(domain_name=domain)
        for cookie in chrome_cookies:
            cookies.append({
                "name": str(cookie.name),
                "value": str(cookie.value),
                "domain": str(cookie.domain),
                "path": str(cookie.path) if cookie.path else "/",
                "expires": float(cookie.expires) if cookie.expires else -1,
                "httpOnly": bool(cookie.has_nonstandard_attr("HttpOnly")),
                "secure": bool(cookie.secure),
                "sameSite": "Lax",
            })
        print(f"Found {len(cookies)} cookies for {domain}")
    except Exception as e:
        print(f"Could not read Chrome cookies: {e}")
        print("On macOS, grant Terminal 'Full Disk Access' in System Preferences > Security")

    return cookies


def get_cloudflare_cookies() -> list:
    """Get Cloudflare-related cookies from Chrome."""
    cookies = []
    for domain in [".claude.ai", "claude.ai", ".anthropic.com"]:
        cookies.extend(get_chrome_cookies_for_domain(domain))
    return cookies


async def main(browser_channel: str = "chrome", copy_cookies: bool = False):
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("ERROR: pip install playwright")
        return

    STATE_DIR.mkdir(exist_ok=True)

    print("=" * 60)
    print("Claude.ai Session Saver")
    print("=" * 60)
    print(f"Browser: {browser_channel}")
    print(f"Copy cookies: {copy_cookies}")
    print()

    # Get cookies from running Chrome if requested
    existing_cookies = []
    if copy_cookies:
        print("Extracting cookies from your Chrome...")
        existing_cookies = get_cloudflare_cookies()
        if existing_cookies:
            print(f"✅ Got {len(existing_cookies)} cookies from Chrome")
        else:
            print("⚠️  No cookies found, continuing with fresh session")

    async with async_playwright() as p:
        # Launch system browser
        try:
            browser = await p.chromium.launch(
                headless=False,
                slow_mo=50,
                channel=browser_channel,
            )
        except Exception as e:
            print(f"Failed to launch {browser_channel}: {e}")
            print("Falling back to bundled Chromium...")
            browser = await p.chromium.launch(headless=False, slow_mo=50)

        context = await browser.new_context(
            viewport={"width": 1400, "height": 900},
        )

        # Inject cookies from running Chrome
        if existing_cookies:
            print("Injecting cookies into browser...")
            try:
                await context.add_cookies(existing_cookies)
                print("✅ Cookies injected!")
            except Exception as e:
                print(f"Cookie injection error: {e}")

        page = await context.new_page()

        print("\nOpening claude.ai...")
        print("=" * 60)
        if copy_cookies:
            print("Cookies were copied from your Chrome.")
            print("Cloudflare should recognize you!")
        print("  1. Pass Cloudflare if needed")
        print("  2. Log in to Claude")
        print("  3. Press Enter here when done")
        print("=" * 60)

        try:
            await page.goto("https://claude.ai", timeout=60000)
        except Exception as e:
            print(f"Note: {e}")

        await asyncio.sleep(3)
        title = await page.title()
        print(f"\nPage: {title}")
        print(f"URL: {page.url}")

        if "Just a moment" not in title and "/login" not in page.url:
            print("\n🎉 Looks like you're already past Cloudflare!")

        input("\n>>> Press Enter when logged in... ")

        # Save session
        print("\nSaving session...")
        await context.storage_state(path=str(STATE_FILE))

        screenshot = STATE_DIR / "claude.png"
        await page.screenshot(path=str(screenshot))

        print(f"\n✅ Saved: {STATE_FILE}")
        print(f"📸 Screenshot: {screenshot}")
        print("\nCopy .playwright-state/ folder to your server")

        await browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--browser",
        default="chrome",
        help="chrome, msedge, chrome-beta"
    )
    parser.add_argument(
        "--copy-cookies",
        action="store_true",
        help="Copy cookies from running Chrome (no need to close it!)"
    )
    args = parser.parse_args()

    asyncio.run(main(args.browser, args.copy_cookies))
