"""Optional UI-only smoke test against an unconfigured local server.

Run with REALFIT3D_BROWSER pointing to an installed Chromium executable,
or install Playwright Chromium first. Mocking body_status reveals the outfit
page without pretending to run the real GPU pipeline.
"""
import os

from playwright.sync_api import sync_playwright


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        executable_path=os.environ.get('REALFIT3D_BROWSER'), headless=True)
    for width, height in [(1440, 1000), (390, 844)]:
        page = browser.new_page(viewport=dict(width=width, height=height))
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(os.environ.get('REALFIT3D_URL', 'http://127.0.0.1:5000'))
        page.wait_for_load_state('networkidle')
        assert page.locator('#page-body').is_visible()
        page.locator('#body-form button').click()
        page.wait_for_function("document.querySelector('#body-status-msg').textContent.includes('not configured')")
        page.screenshot(path=f'/tmp/realfit3d-body-{width}.png', full_page=True)
        page.route('**/body_status', lambda route: route.fulfill(json=dict(has_body=True)))
        page.reload()
        page.wait_for_load_state('networkidle')
        assert page.locator('#page-outfit').is_visible()
        assert page.locator('.combo-card img').evaluate_all('(images) => images.every(i => i.complete && i.naturalWidth > 0)')
        page.locator('.combo-card').nth(1).click()
        assert page.locator('input[name="upper"]').nth(1).is_checked()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path=f'/tmp/realfit3d-outfit-{width}.png', full_page=True)
        assert not errors, errors
        print(f'{width}x{height}: body, runtime error, catalog images, selection, overflow OK')
        page.close()
    browser.close()
