"""Shared look of the briefs: Stephany Alves Design System 2.0 (SIGNAL & STRUCTURE). Tokens, CSS, header symbol, footer and A4 rendering."""
import io, glob, asyncio, re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
for _f in glob.glob(_os.path.join(ROOT, "fonts", "*.ttf")):
    font_manager.fontManager.addfont(_f)

# design system 2.0 tokens; key names kept from v1 so the brief modules need no renames
C = dict(page="#FBF9F4", card="#F6F3E8", sunken="#E7E2D9", accent="#E7E2D9", forest900="#06402B", forest700="#06402B",
         forest500="#6F857A", sage500="#8FAF9E", sage300="#C5D3CB", signal="#C97A3A", signal700="#8A4A1C",
         ink="#2B2F2E", ink2="#4F615A", ink3="#4F615A", border="#E7E2D9", border_subtle="#E7E2D9",
         good="#235F46", good_bg="#DDE8E1", warn="#795300", warn_bg="#F3E8CF", bad="#9B3434", bad_bg="#F3DEDC",
         context="#A6B0A9", grid="#E7E2D9", axis="#4F615A", baseline="#A6B0A9",
         warm_ivory="#F6F3E8",
         cat=["#06402B", "#8FAF9E", "#376C8C", "#C97A3A", "#705477", "#8A4A1C", "#A6B0A9"])

plt.rcParams.update({"font.family": "IBM Plex Sans", "font.size": 8, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.spines.left": False, "axes.edgecolor": C["baseline"], "xtick.color": C["axis"], "ytick.color": C["axis"],
                     "text.color": C["ink"], "axes.labelcolor": C["axis"], "axes.grid": False, "svg.fonttype": "path"})

def svg(fig):
    b = io.StringIO(); fig.savefig(b, format="svg", transparent=True); plt.close(fig)
    s = b.getvalue(); return s[s.find("<svg"):]

def rows_grid(ax):
    ax.yaxis.grid(True, color=C["grid"], linewidth=0.8); ax.set_axisbelow(True); ax.tick_params(length=0)

# Official C2 symbol files from the design system, placed unchanged (no recolor, crop or redraw).
def _symbol(name):
    s = open(_os.path.join(ROOT, "briefs", "brand", name), encoding="utf-8").read()
    s = s[s.find("<svg"):]
    return re.sub(r'\s(width|height)="\d+"', "", s, count=2)

SYMBOL_ON_DARK = _symbol("c2-editorial-reversed.svg")
SYMBOL_MICRO = _symbol("c2-micro.svg")

def mono(w=20, color=None):
    """C2 symbol at w px: the micro cut up to 24 px; a light `color` asks for the reversed file, for dark surfaces."""
    on_dark = color is not None and color.upper() in {C["page"], C["card"], "#F5F4EC"}
    art = SYMBOL_ON_DARK if on_dark else (SYMBOL_MICRO if w <= 24 else _symbol("c2-editorial.svg"))
    return f'<span class="sym" style="width:{w}px;height:{w}px">{art}</span>'

# Pages are written to editions/<date>/<lang>/; the repo fonts are the fallback when the system has none installed.
FONT_FACES = "".join(
    f"@font-face {{ font-family: '{fam}'; font-weight: {wt}; font-style: {st}; src: local('{fam}'), url('../../../fonts/{file}'); }}\n"
    for fam, wt, st, file in [
        ("IBM Plex Sans", 400, "normal", "IBMPlexSans-Regular.ttf"), ("IBM Plex Sans", 500, "normal", "IBMPlexSans-Medium.ttf"),
        ("IBM Plex Sans", 600, "normal", "IBMPlexSans-SemiBold.ttf"), ("IBM Plex Sans", 700, "normal", "IBMPlexSans-Bold.ttf"),
        ("IBM Plex Mono", 400, "normal", "IBMPlexMono-Regular.ttf"), ("IBM Plex Mono", 500, "normal", "IBMPlexMono-Medium.ttf"),
        ("Newsreader", "300 700", "normal", "Newsreader.ttf"), ("Newsreader", "300 700", "italic", "Newsreader-Italic.ttf")])

CSS = FONT_FACES + """
@page { size: A4; margin: 0; }
* { box-sizing: border-box; }
html, body { margin: 0; background: %(page)s; }
body { font-family: 'IBM Plex Sans', Arial, sans-serif; color: %(ink)s; font-feature-settings: 'tnum' 1; font-size: 8pt; }
.page { width: 210mm; height: 297mm; padding: 9mm 11mm 7mm; display: flex; flex-direction: column; gap: 3.2mm; background: %(page)s; }
.page > * { flex-shrink: 0; }
.sym { display: inline-block; flex: none; line-height: 0; }
.sym svg { width: 100%%; height: 100%%; display: block; }
.hdr { background: %(forest900)s; color: %(page)s; border-radius: 2mm; padding: 5mm 6mm 5.5mm; display: flex; gap: 4.5mm; align-items: flex-start; }
.hdr .hsym { width: 11mm; height: 11mm; margin-top: .4mm; }
.hdr .in { flex: 1; min-width: 0; display: flex; justify-content: space-between; gap: 6mm; align-items: flex-start; }
.eyebrow { font-family: 'IBM Plex Mono', monospace; font-weight: 500; font-size: 7pt; letter-spacing: .08em; text-transform: uppercase; color: %(sage300)s; display: flex; align-items: center; gap: 2mm; }
.eyebrow .node { width: 1.6mm; height: 1.6mm; background: %(signal)s; display: inline-block; }
.hdr h1 { font-family: 'Newsreader', Georgia, serif; font-size: 16pt; line-height: 1.18; font-weight: 400; letter-spacing: -.005em; margin: 2mm 0 0; }
.hdr .side { text-align: right; flex: none; }
.hdr .side .big { font-family: 'Newsreader', Georgia, serif; font-size: 13pt; font-weight: 400; margin-top: 1mm; }
.hdr .syn { color: %(warm_ivory)s; border-color: %(sage500)s; }
.hdr .side .sm { font-family: 'IBM Plex Mono', monospace; font-size: 6.5pt; letter-spacing: .08em; text-transform: uppercase; color: %(sage300)s; }
.lead { font-size: 9.5pt; line-height: 1.5; color: %(ink2)s; margin: 0; }
.kpis { display: grid; gap: 3mm; }
.kpi { background: %(card)s; border: 1px solid %(border)s; border-radius: 2mm; padding: 3mm 3.2mm; }
.kpi.inv { background: %(forest900)s; border-color: %(forest900)s; color: %(page)s; }
.kpi .lb { font-family: 'IBM Plex Mono', monospace; font-size: 6.2pt; letter-spacing: .08em; text-transform: uppercase; color: %(ink3)s; }
.kpi.inv .lb { color: %(sage300)s; }
.kpi .v { font-size: 17pt; font-weight: 500; letter-spacing: -.02em; margin-top: 1.2mm; line-height: 1; }
.kpi .d { font-size: 7pt; margin-top: 1.4mm; line-height: 1.3; color: %(ink3)s; }
.kpi.inv .d { color: %(sage300)s; }
.bad { color: %(bad)s !important; } .good { color: %(good)s !important; } .warn { color: %(warn)s !important; }
.kpi.inv .bad, .kpi.inv .good, .kpi.inv .warn { color: %(page)s !important; }
.card { background: %(card)s; border: 1px solid %(border)s; border-radius: 2mm; padding: 3mm 3.4mm; }
.card svg { width: 100%%; height: auto; display: block; }
.sec { position: relative; border-top: 1px solid %(border)s; padding-top: 1.8mm; margin-bottom: 2mm; display: flex; align-items: baseline; gap: 3mm; }
.sec::before { content: ''; position: absolute; top: -1px; left: 0; width: 12mm; height: 2px; background: %(signal)s; }
.sec .no { font-family: 'IBM Plex Mono', monospace; font-weight: 500; font-size: 6.5pt; letter-spacing: .08em; color: %(signal700)s; }
.sec h2 { margin: 0; font-family: 'Newsreader', Georgia, serif; font-size: 11pt; font-weight: 500; line-height: 1.2; }
.sec .r { margin-left: auto; font-family: 'IBM Plex Mono', monospace; font-size: 6.2pt; letter-spacing: .08em; text-transform: uppercase; color: %(ink3)s; }
.ct { font-size: 8pt; font-weight: 500; margin: 0 0 .6mm; }
.cs { font-size: 6.8pt; color: %(ink3)s; margin: 0 0 1.4mm; }
ol.imp { margin: 0; padding-left: 4.5mm; font-size: 8.4pt; line-height: 1.45; } ol.imp li { margin-bottom: 1.5mm; }
ol.imp li::marker { font-family: 'IBM Plex Mono', monospace; color: %(signal700)s; font-weight: 500; }
table.t { width: 100%%; border-collapse: collapse; font-size: 7.6pt; }
table.t th { font-family: 'IBM Plex Mono', monospace; font-weight: 500; font-size: 6.2pt; letter-spacing: .08em; text-transform: uppercase; color: %(ink3)s; text-align: right; padding: 0 1.2mm 1mm; border-bottom: 1px solid %(forest500)s; background: %(sunken)s; }
table.t td { padding: 1mm 1.2mm; border-bottom: 1px solid %(border_subtle)s; text-align: right; }
table.t th:first-child, table.t td:first-child { text-align: left; }
.foot { margin-top: auto; border-top: 1px solid %(border)s; padding-top: 2mm; display: flex; gap: 5mm; align-items: flex-start; }
.foot .brand { display: flex; align-items: center; gap: 2mm; flex: none; }
.foot .wm { font-family: 'Newsreader', Georgia, serif; font-weight: 400; font-size: 10.5pt; color: %(forest900)s; }
.foot .ss { font-family: 'IBM Plex Mono', monospace; font-weight: 500; font-size: 5.8pt; letter-spacing: .12em; color: %(ink3)s; border-left: 1px solid %(border)s; padding-left: 2mm; }
.foot .src { font-size: 6.2pt; color: %(ink3)s; line-height: 1.4; }
""" % C

def footer(src):
    return (f'<div class="foot"><div class="brand">{mono(18)}<span class="wm">Stephany Alves</span><span class="ss">SIGNAL &amp; STRUCTURE</span></div>'
            f'<div class="src">{src}</div></div>')

HEADER_SYMBOL = f'<span class="sym hsym" aria-hidden="true">{SYMBOL_ON_DARK}</span>'

def page(body, title, lang="en"):
    code = "pt-BR" if lang == "pt" else "en"
    # The brief modules still emit the v1 header grid slot; it now carries the C2 symbol.
    body = body.replace('<div class="grid"></div>', HEADER_SYMBOL)
    return f'<!doctype html><html lang="{code}"><head><meta charset="utf-8"><title>{title}</title><style>{CSS}</style></head><body><div class="page">{body}</div></body></html>'

def render(html_path, pdf_path, png_path=None):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 794, "height": 1123}, device_scale_factor=2)
        pg.goto("file://" + html_path); pg.wait_for_timeout(400)
        pg.pdf(path=pdf_path, format="A4", print_background=True, margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        if png_path: pg.screenshot(path=png_path, full_page=True)
        h = pg.evaluate("document.querySelector('.page').scrollHeight"); b.close()
    return h


FIT_LEVELS = [
    "",
    ".page { gap: 2.6mm; } .lead { font-size: 9pt; } ol.imp { font-size: 8.1pt; } ol.imp li { margin-bottom: 1.1mm; }",
    ".page { gap: 2.3mm; padding-top: 7.5mm; padding-bottom: 6mm; } .lead { font-size: 8.7pt; line-height: 1.45; } .hdr h1 { font-size: 15.5pt; } .hdr { padding: 4mm 6mm 4.5mm; } ol.imp { font-size: 7.9pt; line-height: 1.4; } .kpi { padding: 2.4mm 3mm; } .kpi .v { font-size: 15pt; } .card { padding: 2.4mm 3mm; } .sec { margin-bottom: 1.3mm; }",
    ".page { gap: 2mm; padding-top: 7mm; padding-bottom: 5.5mm; } .lead { font-size: 8.4pt; line-height: 1.4; } .hdr h1 { font-size: 14.5pt; } .hdr { padding: 3.6mm 5.5mm 4mm; } .hdr .hsym { width: 9.5mm; height: 9.5mm; } ol.imp { font-size: 7.7pt; line-height: 1.38; } ol.imp li { margin-bottom: .8mm; } .kpi { padding: 2.2mm 2.8mm; } .kpi .v { font-size: 14pt; } .card { padding: 2.2mm 2.8mm; } .sec { margin-bottom: 1.1mm; } .sec h2 { font-size: 10pt; line-height: 1.1; } .sec { padding-top: 1.3mm; } .eyebrow { letter-spacing: .06em; } ul.pc { font-size: 7.4pt; } table.t td { padding: .8mm 1.2mm; }",
    ".page { gap: 1.7mm; padding-top: 6.5mm; padding-bottom: 5mm; } .lead { font-size: 8.4pt; line-height: 1.4; } .hdr h1 { font-size: 14.5pt; } .hdr { padding: 3.6mm 5.5mm 4mm; } .hdr .hsym { width: 9.5mm; height: 9.5mm; } ol.imp { font-size: 7.7pt; line-height: 1.38; } ol.imp li { margin-bottom: .8mm; } .kpi { padding: 2.2mm 2.8mm; } .kpi .v { font-size: 14pt; } .card { padding: 2.2mm 2.8mm; } .sec { margin-bottom: 1.1mm; } .sec h2 { font-size: 10pt; line-height: 1.1; } .sec { padding-top: 1.3mm; } .eyebrow { letter-spacing: .06em; } ul.pc { font-size: 7.4pt; } table.t td { padding: .7mm 1.2mm; } .foot .src { font-size: 5.8pt; line-height: 1.3; }",
]


def render_fit(body, title, lang, html_path, pdf_path, png_path=None):
    """Renders the page, tightening spacing step by step until it fits one A4 page (1123 px).
    Returns (height, level). A height above 1123 after the last level means the text needs editing."""
    for lvl, extra in enumerate(FIT_LEVELS):
        html = page(f"<style>{extra}</style>" + body if extra else body, title, lang)
        open(html_path, "w").write(html)
        h = render(html_path, pdf_path, png_path)
        if h <= 1123: return h, lvl
    return h, len(FIT_LEVELS) - 1
