"""Capture real batch inference and verified ZIP evidence without changing the app."""
import hashlib
import html
import json
import zipfile
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'report_screenshots'
TEMP = ROOT / 'test_artifacts'
TEMP.mkdir(exist_ok=True)
PHOTOS = [ROOT / 'report_assets' / (sport + '.jpg') for sport in ('basketball', 'football', 'tennis')]
BASE = 'http://127.0.0.1:8001'


def select(page):
    page.get_by_label('Select images to organize', exact=True).set_input_files([str(path) for path in PHOTOS])
    expect(page.locator('#batch-selection')).to_contain_text('3 images selected')


def classify(page):
    page.get_by_role('button', name='Organize Images', exact=False).click()
    expect(page.locator('#batch-status')).to_have_text('3 of 3 images organized. 0 skipped.', timeout=120000)
    for sport in ('basketball', 'football', 'tennis'):
        expect(page.locator(f'[data-sport="{sport}"] .category-count')).to_have_text('1')
    page.locator('#batch-gallery').scroll_into_view_if_needed()
    for image in page.locator('.organized-card img').all():
        image.evaluate('(img) => img.decode()')


with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    context = browser.new_context(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1)
    page = context.new_page()
    page.goto(BASE, wait_until='networkidle')
    page.evaluate('document.fonts.ready')
    select(page)
    page.locator('#organizer').screenshot(path=str(OUT / '09_batch_upload.png'))
    with page.expect_response('**/api/organize', timeout=120000) as prediction:
        classify(page)
    results = prediction.value.json()
    (OUT / 'batch_prediction_results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    page.locator('#organizer').screenshot(path=str(OUT / '10_organized_gallery.png'))
    with page.expect_download(timeout=120000) as pending:
        page.get_by_role('button', name='Download Organized ZIP', exact=True).click()
    archive_path = TEMP / 'sportsvision_organized_report.zip'
    pending.value.save_as(archive_path)
    expect(page.locator('#batch-status')).to_contain_text('3 images organized, 0 skipped.', timeout=120000)
    entries = []
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        for item in archive.infolist():
            entries.append({'path': item.filename, 'bytes': item.file_size})
        for index, photo in enumerate(PHOTOS):
            expected = f'{photo.stem}/{index + 1:03d}_{photo.name}'
            assert archive.read(expected) == photo.read_bytes()
    verification = {'archive': archive_path.name, 'sha256': hashlib.sha256(archive_path.read_bytes()).hexdigest(),
                    'original_bytes_verified': True, 'entries': entries}
    (OUT / 'batch_zip_verification.json').write_text(json.dumps(verification, indent=2), encoding='utf-8')

    # Separate evidence viewer: the iframe is the live app, and the sidebar is
    # generated strictly from the downloaded archive's actual central directory.
    folders = []
    for entry in entries:
        if entry['path'].endswith('/'):
            children = [item for item in entries if item['path'].startswith(entry['path']) and not item['path'].endswith('/')]
            rows = ''.join(f'<li>{html.escape(item["path"].split("/")[-1])}<small>{item["bytes"]:,} bytes</small></li>' for item in children)
            folders.append(f'<section><h2>{html.escape(entry["path"])}</h2><ul>{rows}</ul></section>')
    evidence = TEMP / 'zip_evidence.html'
    evidence.write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><title>SportsVision ZIP verification</title>
<style>*{box-sizing:border-box}body{margin:0;font:14px Arial,sans-serif;color:#19382e;background:#f7f8f3}header{height:64px;padding:20px 24px;border-bottom:1px solid #dce2d8;font-weight:700}header span{float:right;font-weight:400;font-size:12px;color:#738077}.layout{display:grid;grid-template-columns:minmax(0,1fr) 330px;height:936px}iframe{width:100%;height:100%;border:0;border-right:1px solid #dce2d8}aside{padding:28px 20px}h1{font-size:22px;line-height:1.3}h2{font-size:17px;margin:0 0 12px}p{line-height:1.7;color:#61746a}section{background:white;border:1px solid #dce2d8;border-radius:12px;padding:18px;margin:18px 0}ul{list-style:none;padding:0;margin:0}li{font-size:13px;overflow-wrap:anywhere}small{display:block;color:#738077;margin-top:8px}.verified{background:#d4f4a5;padding:14px;border-radius:8px;line-height:1.6;font-size:12px}code{font-size:12px;overflow-wrap:anywhere}</style>
<header>SportsVision AI · Download verification<span>Report evidence viewer — not part of the application</span></header>
<div class="layout"><iframe title="Live SportsVision AI application" src="''' + BASE + '''"></iframe><aside><h1>Actual ZIP contents</h1><p>Read from the archive downloaded using the live app button.</p><code>sportsvision_organized.zip</code>''' + ''.join(folders) + '''<div class="verified">Verified: all 3 original images match the downloaded files byte for byte.<br>ZIP integrity check passed.</div><p>Folder names and file sizes come directly from the downloaded ZIP. This panel is report evidence, not an application feature.</p></aside></div></html>''', encoding='utf-8')
    evidence_page = context.new_page()
    evidence_page.goto(evidence.as_uri(), wait_until='networkidle')
    frame = evidence_page.frame_locator('iframe')
    select(frame)
    classify(frame)
    with evidence_page.expect_download(timeout=120000) as actual_download:
        frame.get_by_role('button', name='Download Organized ZIP', exact=True).click()
    second_path = TEMP / 'sportsvision_organized_evidence.zip'
    actual_download.value.save_as(second_path)
    with zipfile.ZipFile(second_path) as archive:
        assert [{'path': item.filename, 'bytes': item.file_size} for item in archive.infolist()] == entries
        for index, photo in enumerate(PHOTOS):
            assert archive.read(f'{photo.stem}/{index + 1:03d}_{photo.name}') == photo.read_bytes()
    expect(frame.locator('#batch-status')).to_contain_text('3 images organized, 0 skipped.', timeout=120000)
    frame.locator('#organizer').evaluate('(element) => window.scrollTo({top: element.offsetTop - 20, behavior: "instant"})')
    evidence_page.screenshot(path=str(OUT / '11_zip_download.png'))
    page.set_viewport_size({'width': 390, 'height': 844})
    page.locator('#batch-gallery').scroll_into_view_if_needed()
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.locator('#organizer').screenshot(path=str(OUT / '12_batch_mobile.png'))
    print(json.dumps({'screenshots': ['09_batch_upload.png', '10_organized_gallery.png', '11_zip_download.png', '12_batch_mobile.png'], 'counts': results['counts'], 'zip_verified': True}))
    browser.close()
