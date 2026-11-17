#!/usr/bin/env python3
"""Prepare real institutional logos for the report in CI.
Uses EMSI's public site and Honoris' Wikimedia Commons image.
If a fetch fails the TeX document still has a typographic fallback.
"""
from pathlib import Path
from io import BytesIO
from urllib.parse import urljoin, quote
import requests
from PIL import Image, ImageChops
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "report_assets"
DEST.mkdir(exist_ok=True)
HEADERS = {"User-Agent": "Mozilla/5.0 (Academic-report-logo-fetcher/1.0)"}

def crop_white(im):
    im = im.convert("RGB")
    white = Image.new("RGB", im.size, "white")
    diff = ImageChops.difference(im, white)
    bb = diff.point(lambda v: 255 if v > 18 else 0).getbbox()
    if bb:
        im = im.crop(bb)
    return im

def write_png(data, dest):
    im = Image.open(BytesIO(data))
    im = crop_white(im)
    if im.width < 60 or im.height < 20:
        raise ValueError("Too small for a logo")
    im.save(dest)
    print("Created", dest, im.size)

# EMSI official website: prefer the actual header logo image.
try:
    page = requests.get("https://emsi.ma/", headers=HEADERS, timeout=30)
    page.raise_for_status()
    soup = BeautifulSoup(page.text, "html.parser")
    candidates = []
    for im in soup.find_all("img"):
        url = im.get("data-src") or im.get("src") or ""
        alt = (im.get("alt") or "").lower()
        if not url:
            continue
        score = (5 if "logo" in url.lower() else 0) + (5 if "emsi" in url.lower() else 0) + (3 if "logo" in alt else 0)
        if "honoris" in url.lower():
            score -= 10
        if score >= 5:
            candidates.append((score, urljoin(page.url, url)))
    candidates.sort(reverse=True)
    errors = []
    for _, url in candidates:
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            write_png(response.content, DEST / "emsi_logo.png")
            break
        except Exception as exc:
            errors.append(str(exc))
    else:
        raise RuntimeError(f"No usable EMSI logo: {errors[:2]}")
except Exception as exc:
    print("EMSI logo unavailable via website:", exc)
    # Backup: extract the EMSI branding block from the public EMSI brochure cover.
    try:
        import fitz
        data = requests.get("https://emsi.ma/wp-content/uploads/2025/04/Plaquette-EMSI-2025.pdf", headers=HEADERS, timeout=60).content
        doc = fitz.open(stream=data, filetype="pdf")
        page = doc[0]
        clip = fitz.Rect(0, 0, page.rect.width * 0.58, page.rect.height * 0.21)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=clip, alpha=False)
        write_png(pix.tobytes("png"), DEST / "emsi_logo.png")
    except Exception as exc2:
        print("EMSI fallback unavailable:", exc2)

# Original Honoris logo from Wikimedia Commons.
try:
    filename = "Honoris United Universities' Logo.jpg"
    url = "https://commons.wikimedia.org/wiki/Special:Redirect/file/" + quote(filename)
    r = requests.get(url, headers=HEADERS, timeout=40)
    r.raise_for_status()
    write_png(r.content, DEST / "honoris_logo.png")
except Exception as exc:
    print("Honoris logo unavailable:", exc)
