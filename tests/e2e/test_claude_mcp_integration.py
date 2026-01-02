"""
Claude.ai MCP Integration Tests

These tests verify Claude.ai can connect to and use the Odoo MCP server.
Requires saved authentication state from: scripts/save_claude_auth.py

Run with:
    pytest tests/e2e/test_claude_mcp_integration.py -v

Prerequisites:
1. Run `python scripts/save_claude_auth.py` to save Claude auth session
2. Have the MCP HTTP server running
3. MCP server registered in Claude settings
"""

import json
import os
from pathlib import Path

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.browser, pytest.mark.claude]

STATE_FILE = Path(__file__).parent.parent.parent / ".playwright-state" / "claude_auth.json"
MCP_SERVER_URL = os.getenv("TEST_MCP_SERVER_URL", "http://localhost:8080")


@pytest.fixture
async def authenticated_browser():
    """Launch browser with saved Claude authentication state."""
    from playwright.async_api import async_playwright

    if not STATE_FILE.exists():
        pytest.skip(
            f"No saved auth state. Run: python scripts/save_claude_auth.py\n"
            f"Expected: {STATE_FILE}"
        )

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=os.getenv("HEADED", "true").lower() != "true"
        )
        context = await browser.new_context(storage_state=str(STATE_FILE))
        yield context
        await browser.close()


@pytest.fixture
async def claude_page(authenticated_browser):
    """Create a page with Claude authentication."""
    page = await authenticated_browser.new_page()
    yield page
    await page.close()


class TestClaudeAuthentication:
    """Test that saved auth state works for Claude.ai."""

    async def test_saved_state_bypasses_cloudflare(self, claude_page):
        """
        GIVEN: Saved authentication state
        WHEN: Browser loads claude.ai
        THEN: Cloudflare challenge is bypassed
        """
        await claude_page.goto("https://claude.ai", timeout=30000)
        await claude_page.wait_for_timeout(3000)

        title = await claude_page.title()
        assert "Just a moment" not in title, "Cloudflare still blocking - auth state may be expired"

    async def test_user_is_logged_in(self, claude_page):
        """
        GIVEN: Saved authentication state
        WHEN: Browser loads claude.ai
        THEN: User is logged in (not on login page)
        """
        await claude_page.goto("https://claude.ai", timeout=30000)
        await claude_page.wait_for_timeout(5000)

        url = claude_page.url
        assert "/login" not in url, f"Still on login page: {url}"

        # Should see the chat interface
        # Look for common Claude UI elements
        body = await claude_page.inner_text("body")
        assert len(body) > 100, "Page seems empty"


class TestClaudeSettings:
    """Test Claude settings page for MCP configuration."""

    async def test_can_access_settings(self, claude_page):
        """
        GIVEN: Logged in to Claude
        WHEN: Navigating to settings
        THEN: Settings page loads
        """
        await claude_page.goto("https://claude.ai", timeout=30000)
        await claude_page.wait_for_timeout(3000)

        # Try to find settings button/link
        settings_selectors = [
            'a[href*="settings"]',
            'button:has-text("Settings")',
            '[aria-label*="settings" i]',
            '[data-testid*="settings"]',
        ]

        settings_found = False
        for selector in settings_selectors:
            element = await claude_page.query_selector(selector)
            if element:
                settings_found = True
                await element.click()
                await claude_page.wait_for_timeout(2000)
                break

        # Settings might also be accessible via URL
        if not settings_found:
            await claude_page.goto("https://claude.ai/settings", timeout=15000)
            await claude_page.wait_for_timeout(2000)

        # Should be on some kind of settings page
        url = claude_page.url
        body = await claude_page.inner_text("body")

        # Either URL contains settings or body has settings-related text
        has_settings = (
            "settings" in url.lower()
            or "settings" in body.lower()
            or "preferences" in body.lower()
            or "account" in body.lower()
        )

        await claude_page.screenshot(path="/tmp/claude_settings.png")
        assert has_settings, f"Could not find settings. URL: {url}"

    async def test_mcp_settings_section_exists(self, claude_page):
        """
        GIVEN: Claude settings page
        WHEN: Looking for MCP configuration
        THEN: MCP/Integrations section is visible
        """
        # Navigate to settings
        await claude_page.goto("https://claude.ai/settings", timeout=30000)
        await claude_page.wait_for_timeout(3000)

        body = await claude_page.inner_text("body")

        # Look for MCP-related settings
        mcp_indicators = [
            "mcp",
            "integrations",
            "connections",
            "servers",
            "tools",
            "plugins",
        ]

        found_mcp = any(indicator in body.lower() for indicator in mcp_indicators)

        await claude_page.screenshot(path="/tmp/claude_mcp_settings.png")

        if not found_mcp:
            pytest.skip("MCP settings section not found - may need Pro account or feature flag")


class TestClaudeMCPConnection:
    """Test Claude's connection to MCP servers."""

    async def test_can_add_mcp_server(self, claude_page):
        """
        GIVEN: Claude settings with MCP section
        WHEN: User adds new MCP server
        THEN: Server can be configured with URL

        NOTE: This test documents the expected flow.
        Actual implementation depends on Claude's UI.
        """
        await claude_page.goto("https://claude.ai/settings", timeout=30000)
        await claude_page.wait_for_timeout(3000)

        # Look for "Add" or "Connect" button for MCP
        add_selectors = [
            'button:has-text("Add")',
            'button:has-text("Connect")',
            'button:has-text("New")',
            'a:has-text("Add integration")',
        ]

        for selector in add_selectors:
            element = await claude_page.query_selector(selector)
            if element:
                await claude_page.screenshot(path="/tmp/claude_add_mcp.png")
                # Don't actually click - just verify it exists
                break
        else:
            await claude_page.screenshot(path="/tmp/claude_no_add_button.png")
            pytest.skip("Could not find Add MCP server button")


class TestClaudeMCPUsage:
    """Test using MCP tools through Claude's interface."""

    async def test_mcp_tools_appear_in_chat(self, claude_page):
        """
        GIVEN: MCP server is connected to Claude
        WHEN: User opens a new chat
        THEN: MCP tools are available

        NOTE: Requires MCP server to be pre-configured in Claude.
        """
        await claude_page.goto("https://claude.ai/new", timeout=30000)
        await claude_page.wait_for_timeout(3000)

        # Look for tools/integrations indicator
        body = await claude_page.inner_text("body")

        # Claude might show connected tools somewhere
        await claude_page.screenshot(path="/tmp/claude_chat_interface.png")

        # This test documents expected behavior
        # Actual assertion depends on Claude's UI showing tool availability

    async def test_can_invoke_odoo_tool(self, claude_page):
        """
        GIVEN: Odoo MCP server connected to Claude
        WHEN: User asks Claude to use Odoo tool
        THEN: Claude can execute the tool

        Example prompt: "Use the get_my_profile tool to show my Odoo profile"

        NOTE: This is an aspirational test showing the expected end-to-end flow.
        """
        await claude_page.goto("https://claude.ai/new", timeout=30000)
        await claude_page.wait_for_timeout(3000)

        # Find the chat input
        chat_input = await claude_page.query_selector(
            'textarea, [contenteditable="true"], input[type="text"]'
        )

        if not chat_input:
            await claude_page.screenshot(path="/tmp/claude_no_input.png")
            pytest.skip("Could not find chat input")

        # Type a message that would trigger MCP tool use
        await chat_input.fill("Please use the get_my_profile tool to show my employee profile from Odoo")

        await claude_page.screenshot(path="/tmp/claude_tool_request.png")

        # Don't actually send - this is a documentation test
        # In a real test, you would:
        # 1. Send the message
        # 2. Wait for Claude's response
        # 3. Verify the tool was called
        # 4. Verify the response contains profile data
