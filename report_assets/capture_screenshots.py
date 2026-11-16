"""Capture the unchanged local application with real browser uploads/inference."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'report_screenshots'
ASSETS = ROOT / 'report_assets'
records = []

with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    context = browser.new_context(viewport={'width': 1440, 'height': 900}, device_scale_factor=1)
    page = context.new_page()
    page.goto('http://127.0.0.1:8000', wait_until='networkidle')
    page.evaluate('document.fonts.ready')
    page.screenshot(path=str(OUT / '01_homepage.png'), full_page=True)
    page.screenshot(path=str(OUT / '01_homepage_viewport.png'))
    page.get_by_role('link', name='Classifier', exact=True).click()
    page.wait_for_timeout(700)  # Let the existing smooth-scroll animation finish.
    page.screenshot(path=str(OUT / '02_upload.png'))

    for sport, number in [('football', '04'), ('basketball', '05'), ('tennis', '06')]:
        page.locator('#file-input').set_input_files(str(ASSETS / f'{sport}.jpg'))
        expect(page.get_by_role('button', name='Analyze Image')).to_be_enabled()
        expect(page.locator('#preview')).to_be_visible()
        if sport == 'football':
            page.screenshot(path=str(OUT / '03_image_preview.png'))
        with page.expect_response('**/api/predict', timeout=120000) as response:
            page.get_by_role('button', name='Analyze Image').click()
        result = response.value.json()
        records.append({'input': f'{sport}.jpg', 'http_status': response.value.status, 'result': result})
        print(json.dumps(records[-1]), flush=True)
        expect(page.locator('#result-status')).to_have_text('ANALYSIS COMPLETE', timeout=120000)
        page.evaluate("window.scrollTo({top: document.querySelector('#classifier').offsetTop - 32, behavior: 'instant'})")
        page.wait_for_timeout(700)  # Finish probability-bar transition before capture.
        actual = result.get('predicted_sport')
        name = f'{number}_{sport}_prediction.png' if actual == sport else f'{number}_{sport}_actual_{actual}.png'
        page.screenshot(path=str(OUT / name))

    page.get_by_role('button', name='Remove', exact=True).click()
    page.get_by_role('link', name='How it works', exact=False).click()
    page.wait_for_timeout(700)
    page.screenshot(path=str(OUT / '07_model_information.png'))

    mobile = browser.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=1, is_mobile=True, has_touch=True)
    mobile_page = mobile.new_page()
    mobile_page.goto('http://127.0.0.1:8000', wait_until='networkidle')
    mobile_page.evaluate('document.fonts.ready')
    mobile_page.screenshot(path=str(OUT / '08_mobile_view.png'), full_page=True)
    mobile_page.screenshot(path=str(OUT / '08_mobile_viewport.png'))
    (ASSETS / 'prediction_results.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
    browser.close()
