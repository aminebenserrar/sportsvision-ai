"""Real browser integration checks; requires Playwright and Microsoft Edge."""
import io
import json
import zipfile
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'test_artifacts'
OUT.mkdir(exist_ok=True)
photos = [ROOT / 'report_assets' / (sport + '.jpg') for sport in ('basketball', 'football', 'tennis')]

with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    context = browser.new_context(viewport={'width': 1440, 'height': 900}, device_scale_factor=1)
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://127.0.0.1:8001', wait_until='networkidle')
    page.evaluate('document.fonts.ready')
    page.locator('#file-input').set_input_files(str(photos[1]))
    expect(page.get_by_role('button', name='Analyze Image', exact=True)).to_be_enabled(timeout=30000)
    page.get_by_role('button', name='Analyze Image', exact=True).click()
    expect(page.locator('#predicted-sport')).to_have_text('Football', timeout=120000)
    payloads = [{'name': path.name, 'mimeType': 'image/jpeg', 'buffer': path.read_bytes()} for path in photos]
    payloads.append({'name': 'corrupted.png', 'mimeType': 'image/png', 'buffer': b'corrupted'})
    page.get_by_label('Select images to organize', exact=True).set_input_files(payloads)
    page.get_by_role('button', name='Organize Images', exact=False).click()
    expect(page.locator('#batch-status')).to_have_text('3 of 4 images organized. 1 skipped.', timeout=120000)
    expect(page.locator('.organized-card')).to_have_count(3)
    expect(page.locator('#batch-failure-list li')).to_have_count(1)
    for sport in ('basketball', 'football', 'tennis'):
        expect(page.locator(f'[data-sport="{sport}"] .category-count')).to_have_text('1')
        expect(page.locator(f'[data-sport="{sport}"] .organized-card')).to_have_count(1)
    # The batch feature must leave the single-image result untouched.
    expect(page.locator('#predicted-sport')).to_have_text('Football')
    page.locator('#organizer').scroll_into_view_if_needed()
    page.wait_for_timeout(500)
    page.locator('#organizer').screenshot(path=str(OUT / 'organization_desktop.png'))
    with page.expect_download(timeout=120000) as pending:
        page.get_by_role('button', name='Download Organized ZIP', exact=True).click()
    pending.value.save_as(OUT / 'organized.zip')
    expect(page.locator('#batch-status')).to_contain_text('3 images organized, 1 skipped.', timeout=120000)
    with zipfile.ZipFile(OUT / 'organized.zip') as archive:
        for index, path in enumerate(photos):
            sport = path.stem
            assert archive.read(f'{sport}/{index + 1:03d}_{sport}.jpg') == path.read_bytes()
    page.set_viewport_size({'width': 390, 'height': 844})
    page.locator('#organizer').scroll_into_view_if_needed()
    page.wait_for_timeout(500)
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.locator('#organizer').screenshot(path=str(OUT / 'organization_mobile.png'))
    page.get_by_role('button', name='Clear collection', exact=True).click()
    expect(page.locator('.organized-card')).to_have_count(0)
    expect(page.get_by_role('button', name='Download Organized ZIP', exact=True)).to_be_disabled()
    # All-invalid batches must leave no stale success results or enabled download.
    page.get_by_label('Select images to organize', exact=True).set_input_files([payloads[-1]])
    page.get_by_role('button', name='Organize Images', exact=False).click()
    expect(page.locator('#batch-status')).to_have_text('0 of 1 images organized. 1 skipped.', timeout=120000)
    expect(page.get_by_role('button', name='Download Organized ZIP', exact=True)).to_be_disabled()
    assert not errors, errors
    print('Browser checks passed: single classification, real batch, partial failure, counts, ZIP, mobile, clear, all-invalid batch; no JavaScript errors.')
    browser.close()
