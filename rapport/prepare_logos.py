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
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        rgba = im.convert("RGBA")
        canvas = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        im = Image.alpha_composite(canvas, rgba).convert("RGB")
    else:
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

# Use the exact EMSI student login logo supplied by the report author.
try:
    r = requests.get("https://student.emsi.ma/emsi_login_logo.png", headers=HEADERS, timeout=40)
    r.raise_for_status()
    write_png(r.content, DEST / "emsi_logo.png")
except Exception as exc:
    print("EMSI logo unavailable:", exc)

# Original Honoris logo from Wikimedia Commons.
try:
    filename = "Honoris United Universities' Logo.jpg"
    url = "https://commons.wikimedia.org/wiki/Special:Redirect/file/" + quote(filename)
    r = requests.get(url, headers=HEADERS, timeout=40)
    r.raise_for_status()
    write_png(r.content, DEST / "honoris_logo.png")
except Exception as exc:
    print("Honoris logo unavailable:", exc)
