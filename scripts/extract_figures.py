"""Extract paper figures from PAPER.ko.html and rasterize them with headless Chrome."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "docs" / "PAPER.ko.html").read_text(encoding="utf-8")
OUT = ROOT / "docs" / "figures"
OUT.mkdir(exist_ok=True)
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

BASE_CSS = """
:root{--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--ink3:#8a887f;--line:#dedcd5;
--panel:#f3f2ee;--blue:#2a78d6;--blue-d:#1c5cab;--aqua:#1baf7a;--yellow:#eda100;
--green:#008300;--red:#e34948;--violet:#4a3aa7;}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:#ffffff;font-family:'Malgun Gothic','Apple SD Gothic Neo',sans-serif;padding:10px;}
svg{width:100%;height:auto;display:block;}
svg text{font-family:'Malgun Gothic','Apple SD Gothic Neo',sans-serif;}
.tiles{display:flex;gap:14px;}
.tile{flex:1 1 200px;border:1px solid #dedcd5;border-radius:10px;padding:14px 16px;background:#fff;}
.tile .t-label{font-size:13px;color:#52514e;margin-bottom:6px;}
.tile .t-before{font-size:13.5px;color:#8a887f;}
.tile .t-before b{color:#e34948;font-weight:700;}
.tile .t-after{font-size:26px;font-weight:800;color:#1c5cab;line-height:1.3;}
.tile .t-unit{font-size:14px;font-weight:600;color:#52514e;}
"""

svgs = re.findall(r"<svg class=\"fig-svg\".*?</svg>", HTML, re.DOTALL)
tiles = re.search(r"<div class=\"tiles\">.*?(?=<figcaption)", HTML, re.DOTALL)
if tiles is None:
    raise SystemExit("tiles block not found")
tiles_html = tiles.group(0)

# figure order in the document: fig1(arch), fig2(chart), fig3(inflation),
# tiles(fig4), fig5(junctions), fig6(gap), fig7(alignment)
# fig4 renders as a vertical stack (column) so the tile labels stay legible
# at book width; see the extra CSS below.
FIG4_CSS = (
    ".tiles{flex-direction:column;max-width:560px;gap:12px;}"
    ".tile{flex:0 0 auto;}"
    "body{overflow:hidden;}"
)
jobs: list[tuple[str, str, int, int, str]] = []
heights = [330, 300, 250, 260, 230, 250]
for index, svg in enumerate(svgs):
    number = index + 1 if index < 3 else index + 2  # tiles take slot 4
    jobs.append((f"fig{number}", svg, heights[index], 1400, ""))
jobs.append(("fig4", tiles_html, 170, 600, FIG4_CSS))

for name, body, height, width, extra_css in jobs:
    page = OUT / f"{name}.html"
    page.write_text(
        f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<style>{BASE_CSS}{extra_css}</style></head><body>{body}</body></html>",
        encoding="utf-8",
    )
    png = OUT / f"{name}.png"
    window = f"--window-size={width},{int(height * 2.06) + 40}"
    subprocess.run(
        [
            CHROME,
            "--headless=new",
            "--disable-gpu",
            "--force-device-scale-factor=2",
            f"--screenshot={png}",
            window,
            page.as_uri(),
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )
    print(name, "->", png.name, png.stat().st_size, "bytes")
