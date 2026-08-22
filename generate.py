#!/usr/bin/env python3
"""
Randkuj Static Generator
========================
Użycie:
    python generate.py

Wymaga:
    pip install jinja2

Efekt:
    Generuje dist/index.html + podstrony artykułów + sitemap.xml
"""

import json
import shutil
from datetime import date
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

ROOT           = Path(__file__).parent
TEMPLATES_DIR  = ROOT / "templates"
DIST_DIR       = ROOT / "dist"
DATA_FILE      = ROOT / "artykuly.json"
AFFILIATE_FILE = ROOT.parent / "affiliate_links.json"
BLOG_KEY       = "randkuj-generator"


def load_data() -> dict:
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def load_affiliate() -> dict:
    if AFFILIATE_FILE.exists():
        with open(AFFILIATE_FILE, encoding="utf-8") as f:
            return json.load(f).get(BLOG_KEY, {})
    return {}


def inject_affiliate(data: dict, affiliate: dict) -> None:
    kategorie = affiliate.get("kategorie", {})
    for kat_slug, artykuly in [
        ("rankingi", data.get("rankingi", [])),
        ("recenzje", data.get("recenzje", [])),
        ("poradniki", data.get("poradniki", [])),
    ]:
        linki = kategorie.get(kat_slug, kategorie.get("dating", []))
        for art in artykuly:
            if not art.get("oferty") and linki:
                art["oferty"] = linki


def copy_assets():
    for folder in ["logos-randkuj", "images"]:
        src = ROOT / folder
        dst = DIST_DIR / folder
        if src.exists():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print(f"  skopiowano: {folder}/")


def build():
    DIST_DIR.mkdir(exist_ok=True)
    data = load_data()
    affiliate = load_affiliate()
    inject_affiliate(data, affiliate)
    sidebar_oferty = affiliate.get("sidebar", [])
    meta = data["meta"]
    meta["updated"] = date.today().isoformat()
    site_url = meta["site_url"].rstrip("/")

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    sitemap_urls = [site_url + "/"]

    # ── Strona główna ──────────────────────────────────────────────
    tmpl_index = env.get_template("index.html")
    html = tmpl_index.render(**data, sidebar_oferty=sidebar_oferty)
    (DIST_DIR / "index.html").write_text(html, encoding="utf-8")
    print("  wygenerowano: dist/index.html")

    # ── Podstrony artykułów ────────────────────────────────────────
    tmpl_art = env.get_template("artykul.html")

    kategorie = [
        ("rankingi",  "Rankingi portali"),
        ("recenzje",  "Recenzje portali"),
        ("poradniki", "Poradniki randkowania"),
    ]

    for kat_slug, kat_nazwa in kategorie:
        artykuly = data.get(kat_slug, [])
        for art in artykuly:
            out_dir = DIST_DIR / kat_slug / art["slug"]
            out_dir.mkdir(parents=True, exist_ok=True)
            html = tmpl_art.render(
                art=art, meta=meta, base="../../",
                kategoria=kat_nazwa, kat_slug=kat_slug,
                sidebar_oferty=sidebar_oferty,
            )
            (out_dir / "index.html").write_text(html, encoding="utf-8")
            sitemap_urls.append(f"{site_url}/{kat_slug}/{art['slug']}/")
        print(f"  wygenerowano: {len(artykuly)} podstron {kat_slug}")

    # ── Sitemap XML ────────────────────────────────────────────────
    today_str = meta["updated"]
    sitemap  = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for url in sitemap_urls:
        priority = "1.0" if url == site_url + "/" else "0.8"
        sitemap += f"  <url><loc>{url}</loc><lastmod>{today_str}</lastmod><priority>{priority}</priority></url>\n"
    sitemap += "</urlset>"
    (DIST_DIR / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    print(f"  wygenerowano: sitemap.xml ({len(sitemap_urls)} URL)")

    # ── robots.txt ─────────────────────────────────────────────────
    robots = (
        "User-agent: *\n"
        "Allow: /\n"
        f"\nSitemap: {site_url}/sitemap.xml\n"
    )
    (DIST_DIR / "robots.txt").write_text(robots, encoding="utf-8")
    print("  wygenerowano: robots.txt")

    # ── vercel.json dla clean URLs ──────────────────────────────────
    vercel_cfg = {
        "cleanUrls": True,
        "trailingSlash": True
    }
    (ROOT / "vercel.json").write_text(
        json.dumps(vercel_cfg, indent=2), encoding="utf-8"
    )

    copy_assets()
    print("\nGotowe! Wgraj zawartość folderu dist/ na serwer.")


if __name__ == "__main__":
    print("Randkuj Generator — start\n")
    build()
