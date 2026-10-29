"""Shared look of the briefs: Stephany Alves Design System (SIGNAL & STRUCTURE). Tokens, CSS, footer and A4 rendering."""
import io, glob, asyncio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
for _f in glob.glob(_os.path.join(ROOT, "fonts", "*.ttf")):
    font_manager.fontManager.addfont(_f)

# design system tokens
C = dict(page="#F5F4EC", card="#FFFFFF", sunken="#E8E9E5", accent="#E4ECE7", forest900="#0B302B", forest700="#1E5246",
         forest500="#4A8574", sage500="#8FA99D", sage300="#B8C9C0", signal="#35D58A", signal700="#16804F",
         ink="#101714", ink2="#454C48", ink3="#5E6561", border="#D6D8D2", border_subtle="#E8E9E5",
         good="#1F7A4F", good_bg="#DCEFE3", warn="#9A6412", warn_bg="#F4E8CF", bad="#A63A2A", bad_bg="#F4DFD9",
         context="#D6D8D2", grid="#E8E9E5", axis="#5E6561", baseline="#BDC1BB",
         cat=["#1E5246", "#8FA99D", "#4F6D8A", "#C49A45", "#B4694A", "#7A6A85", "#5E6561"])

plt.rcParams.update({"font.family": "IBM Plex Sans", "font.size": 8, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.spines.left": False, "axes.edgecolor": C["baseline"], "xtick.color": C["axis"], "ytick.color": C["axis"],
                     "text.color": C["ink"], "axes.labelcolor": C["axis"], "axes.grid": False, "svg.fonttype": "path"})

def svg(fig):
    b = io.StringIO(); fig.savefig(b, format="svg", transparent=True); plt.close(fig)
    s = b.getvalue(); return s[s.find("<svg"):]

def rows_grid(ax):
    ax.yaxis.grid(True, color=C["grid"], linewidth=0.8); ax.set_axisbelow(True); ax.tick_params(length=0)

MONO = ('<svg viewBox="0 0 58 48" width="{w}" height="{h}" aria-label="SA"><g fill="none" stroke="{c}" stroke-width="5" stroke-linejoin="miter">'
        '<path d="M22 8.5H10.5a4 4 0 0 0-4 4V20a4 4 0 0 0 4 4h5a4 4 0 0 1 4 4v7.5a4 4 0 0 1-4 4H4"/><path d="M15.5 24H44"/></g>'
        '<path fill="{c}" d="M25.4 42 37.6 6h4.8l12.2 36h-5.3L40 14.5 30.7 42z"/></svg>')

def mono(w=20, color="#0B302B"):
    return MONO.format(w=w, h=round(w * 48 / 58, 1), c=color)

CSS = """
@page { size: A4; margin: 0; }
* { box-sizing: border-box; }
html, body { margin: 0; background: %(page)s; }
body { font-family: 'IBM Plex Sans', Arial, sans-serif; color: %(ink)s; font-feature-settings: 'tnum' 1; font-size: 8pt; }
.page { width: 210mm; height: 297mm; padding: 9mm 11mm 7mm; display: flex; flex-direction: column; gap: 3.2mm; background: %(page)s; }
.page > * { flex-shrink: 0; }
.hdr { background: %(forest900)s; color: %(page)s; border-radius: 1.1mm; padding: 5mm 6mm 5.5mm; position: relative; overflow: hidden; }
.hdr .grid { position: absolute; inset: 0; background-image: linear-gradient(rgba(185,232,207,.06) 1px, transparent 1px), linear-gradient(90deg, rgba(185,232,207,.06) 1px, transparent 1px); background-size: 8mm 8mm; }
.hdr .in { position: relative; display: flex; justify-content: space-between; gap: 6mm; align-items: flex-start; }
.eyebrow { font-family: 'IBM Plex Mono', monospace; font-weight: 500; font-size: 7pt; letter-spacing: .08em; text-transform: uppercase; color: %(sage300)s; display: flex; align-items: center; gap: 2mm; }
.eyebrow .node { width: 1.6mm; height: 1.6mm; background: %(signal)s; display: inline-block; }
.hdr h1 { font-size: 15.5pt; line-height: 1.2; font-weight: 500; letter-spacing: -.01em; margin: 2.2mm 0 0; }
.hdr .side { text-align: right; flex: none; }
.hdr .side .big { font-size: 12pt; font-weight: 500; margin-top: 1mm; }
.hdr .side .sm { font-family: 'IBM Plex Mono', monospace; font-size: 6.5pt; letter-spacing: .08em; text-transform: uppercase; color: %(sage300)s; }
.lead { font-size: 9.5pt; line-height: 1.5; color: %(ink2)s; margin: 0; }
.kpis { display: grid; gap: 3mm; }
.kpi { background: %(card)s; border: 1px solid %(border)s; border-radius: 1.1mm; padding: 3mm 3.2mm; }
.kpi.inv { background: %(forest900)s; border-color: %(forest900)s; color: %(page)s; }
.kpi .lb { font-family: 'IBM Plex Mono', monospace; font-size: 6.2pt; letter-spacing: .08em; text-transform: uppercase; color: %(ink3)s; }
.kpi.inv .lb { color: %(sage300)s; }
.kpi .v { font-size: 17pt; font-weight: 500; letter-spacing: -.02em; margin-top: 1.2mm; line-height: 1; }
.kpi .d { font-size: 7pt; margin-top: 1.4mm; line-height: 1.3; color: %(ink3)s; }
.kpi.inv .d { color: %(sage300)s; }
.bad { color: %(bad)s !important; } .good { color: %(good)s !important; } .warn { color: %(warn)s !important; }
.card { background: %(card)s; border: 1px solid %(border)s; border-radius: 1.1mm; padding: 3mm 3.4mm; }
.card svg { width: 100%%; height: auto; display: block; }
.sec { border-top: 1.5px solid %(forest900)s; padding-top: 1.6mm; margin-bottom: 2mm; display: flex; align-items: baseline; gap: 3mm; }
.sec .no { font-family: 'IBM Plex Mono', monospace; font-size: 6.5pt; letter-spacing: .08em; color: %(ink3)s; }
.sec h2 { margin: 0; font-size: 10pt; font-weight: 500; }
.sec .r { margin-left: auto; font-family: 'IBM Plex Mono', monospace; font-size: 6.2pt; letter-spacing: .08em; text-transform: uppercase; color: %(ink3)s; }
.ct { font-size: 8pt; font-weight: 500; margin: 0 0 .6mm; }
.cs { font-size: 6.8pt; color: %(ink3)s; margin: 0 0 1.4mm; }
ol.imp { margin: 0; padding-left: 4.5mm; font-size: 8.4pt; line-height: 1.45; } ol.imp li { margin-bottom: 1.5mm; }
table.t { width: 100%%; border-collapse: collapse; font-size: 7.6pt; }
table.t th { font-family: 'IBM Plex Mono', monospace; font-weight: 500; font-size: 6.2pt; letter-spacing: .08em; text-transform: uppercase; color: %(ink3)s; text-align: right; padding: 0 1.2mm 1mm; border-bottom: 1px solid %(border)s; background: %(sunken)s; }
table.t td { padding: 1mm 1.2mm; border-bottom: 1px solid %(border_subtle)s; text-align: right; }
table.t th:first-child, table.t td:first-child { text-align: left; }
.foot { margin-top: auto; border-top: 1px solid %(border)s; padding-top: 2mm; display: flex; gap: 5mm; align-items: flex-start; }
.foot .brand { display: flex; align-items: center; gap: 2mm; flex: none; }
.foot .wm { font-family: 'Newsreader', Georgia, serif; font-weight: 400; font-size: 10pt; color: %(forest900)s; }
.foot .ss { font-family: 'IBM Plex Mono', monospace; font-size: 5.8pt; letter-spacing: .1em; color: %(ink3)s; border-left: 1px solid %(border)s; padding-left: 2mm; }
.foot .src { font-size: 6.2pt; color: %(ink3)s; line-height: 1.4; }
""" % C

def footer(src):
    return (f'<div class="foot"><div class="brand">{mono(18)}<span class="wm">Stephany Alves</span><span class="ss">SIGNAL &amp; STRUCTURE</span></div>'
            f'<div class="src">{src}</div></div>')

def page(body, title, lang="en"):
    code = "pt-BR" if lang == "pt" else "en"
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
    ".page { gap: 2.3mm; padding-top: 7.5mm; padding-bottom: 6mm; } .lead { font-size: 8.7pt; line-height: 1.45; } .hdr h1 { font-size: 14.5pt; } .hdr { padding: 4mm 6mm 4.5mm; } ol.imp { font-size: 7.9pt; line-height: 1.4; } .kpi { padding: 2.4mm 3mm; } .kpi .v { font-size: 15pt; } .card { padding: 2.4mm 3mm; } .sec { margin-bottom: 1.3mm; }",
    ".page { gap: 2mm; padding-top: 7mm; padding-bottom: 5.5mm; } .lead { font-size: 8.4pt; line-height: 1.4; } .hdr h1 { font-size: 13.5pt; } .hdr { padding: 3.6mm 5.5mm 4mm; } ol.imp { font-size: 7.7pt; line-height: 1.38; } ol.imp li { margin-bottom: .8mm; } .kpi { padding: 2.2mm 2.8mm; } .kpi .v { font-size: 14pt; } .card { padding: 2.2mm 2.8mm; } .sec { margin-bottom: 1.1mm; } ul.pc { font-size: 7.4pt; } table.t td { padding: .8mm 1.2mm; }",
    ".page { gap: 1.7mm; padding-top: 6.5mm; padding-bottom: 5mm; } .lead { font-size: 8.4pt; line-height: 1.4; } .hdr h1 { font-size: 13.5pt; } .hdr { padding: 3.6mm 5.5mm 4mm; } ol.imp { font-size: 7.7pt; line-height: 1.38; } ol.imp li { margin-bottom: .8mm; } .kpi { padding: 2.2mm 2.8mm; } .kpi .v { font-size: 14pt; } .card { padding: 2.2mm 2.8mm; } .sec { margin-bottom: 1.1mm; } ul.pc { font-size: 7.4pt; } table.t td { padding: .7mm 1.2mm; } .foot .src { font-size: 5.8pt; line-height: 1.3; }",
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
