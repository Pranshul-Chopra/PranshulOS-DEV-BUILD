"""
download_fonts.py — run this ONCE to bundle IBM Plex fonts locally.
Fetches woff2 files from Google Fonts and saves them to static/fonts/.
After this, PranshulOS loads fonts from disk — no network needed.

Usage:
    python download_fonts.py
"""
import urllib.request
import os
from pathlib import Path

OUT = Path(__file__).parent / "static" / "fonts"
OUT.mkdir(parents=True, exist_ok=True)

# Ask Google Fonts CSS API for the woff2 URLs (modern browser UA gets woff2)
CSS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=IBM+Plex+Sans:wght@300;400;500"
    "&family=IBM+Plex+Mono:wght@400;500"
    "&display=swap"
)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)

print("Fetching font CSS from Google Fonts...")
req = urllib.request.Request(CSS_URL, headers={"User-Agent": UA})
with urllib.request.urlopen(req) as r:
    css = r.read().decode()

# Extract woff2 URLs
import re
urls = re.findall(r"url\((https://fonts\.gstatic\.com/[^)]+\.woff2)\)", css)
print(f"Found {len(urls)} font files.")

for url in urls:
    filename = url.split("/")[-1]  # e.g. zYXgKVElMYYaJe8b...woff2
    out_path = OUT / filename
    if out_path.exists():
        print(f"  skip (exists): {filename}")
        continue
    print(f"  downloading: {filename}")
    req2 = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req2) as r2, open(out_path, "wb") as f:
        f.write(r2.read())

# Generate the @font-face CSS file
print("\nGenerating static/fonts/ibmflex.css ...")

# Map: parse font-family + font-weight from CSS blocks
blocks = re.findall(
    r"(/\*.*?\*/\s*)?@font-face\s*\{([^}]+)\}",
    css,
    re.DOTALL
)

face_rules = []
for comment, body in blocks:
    family_m = re.search(r"font-family:\s*'([^']+)'", body)
    weight_m  = re.search(r"font-weight:\s*(\d+)", body)
    style_m   = re.search(r"font-style:\s*(\w+)", body)
    url_m     = re.search(r"url\((https://fonts\.gstatic\.com/([^)]+\.woff2))\)", body)
    if not (family_m and weight_m and url_m):
        continue
    family   = family_m.group(1)
    weight   = weight_m.group(1)
    style    = style_m.group(1) if style_m else "normal"
    woff2_url = url_m.group(1)
    local_filename = woff2_url.split("/")[-1]
    face_rules.append(
        f"@font-face {{\n"
        f"  font-family: '{family}';\n"
        f"  font-style: {style};\n"
        f"  font-weight: {weight};\n"
        f"  font-display: swap;\n"
        f"  src: url('/static/fonts/{local_filename}') format('woff2');\n"
        f"}}"
    )

css_out = "\n\n".join(face_rules)
(OUT / "ibmflex.css").write_text(css_out, encoding="utf-8")
print("Done! static/fonts/ibmflex.css written.")
print(f"\nFont files in {OUT}:")
for f in sorted(OUT.iterdir()):
    print(f"  {f.name}  ({f.stat().st_size // 1024} KB)")
