"""Builds one edition of the three briefs, in English and Brazilian Portuguese.

    python run_edition.py                                  # today's edition, fetching fresh data
    python run_edition.py --date 2026-10-29 --report-cutoff 2026-10-28 --skip-fetch

Steps
1. Fetch public data (BCB, BLS, Comex Stat) unless --skip-fetch. A failing source keeps its last file.
2. Extend the synthetic dataset to the report cutoff (default: last day of the previous month).
3. Build each brief in each language: HTML, PDF (A4) and PNG preview in editions/<date>/<lang>/.
4. Write editions/<date>/manifest.json and refresh the editions index and README previews.
"""
import argparse, json, os, subprocess, sys
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "pipeline"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--report-cutoff", default=None, help="last day covered by the monthly procurement report")
    ap.add_argument("--lang", nargs="+", default=["en", "pt"], choices=["en", "pt"])
    ap.add_argument("--skip-fetch", action="store_true")
    a = ap.parse_args()
    edition = date.fromisoformat(a.date)
    cutoff = date.fromisoformat(a.report_cutoff) if a.report_cutoff else edition.replace(day=1) - timedelta(days=1)

    warnings = []
    if not a.skip_fetch:
        env = dict(os.environ, EDITION_DATE=edition.isoformat())
        subprocess.run([sys.executable, os.path.join(ROOT, "pipeline", "fetch_public.py")], check=True, env=env)
        wf = os.path.join(ROOT, "fetch_warnings.txt")
        if os.path.exists(wf):
            warnings += [f"fetch failed: {s}" for s in open(wf).read().split(",") if s]; os.remove(wf)

    import synthetic
    synthetic.extend(cutoff); synthetic.export(cutoff)

    from briefs import aerospace, procurement, ev
    out = {}
    for lang in a.lang:
        d = os.path.join(ROOT, "editions", edition.isoformat(), lang); os.makedirs(d, exist_ok=True)
        out[lang] = [aerospace.build(edition, lang, d), procurement.build(edition, cutoff, lang, d), ev.build(edition, lang, d)]
        for r in out[lang]:
            if r["height"] > 1123: warnings.append(f"{lang}/{r['name']} overflows A4 ({r['height']} px): shorten the text")
    clean = lambda o: {k: (v if isinstance(v, (str, int, list, dict)) or v is None else float(v)) for k, v in o.items()}
    manifest = dict(edition=edition.isoformat(), report_cutoff=cutoff.isoformat(), warnings=warnings,
                    briefs={l: [clean(r) for r in rs] for l, rs in out.items()})
    json.dump(manifest, open(os.path.join(ROOT, "editions", edition.isoformat(), "manifest.json"), "w"), indent=2, ensure_ascii=False)

    # light PNG previews (the PDF is the deliverable) and README previews of the latest edition
    from PIL import Image
    img = os.path.join(ROOT, "docs", "images"); os.makedirs(img, exist_ok=True)
    for lang, rs in out.items():
        for r, short in zip(rs, ("aerospace", "procurement", "ev")):
            src = os.path.join(ROOT, "editions", edition.isoformat(), lang, r["name"] + ".png")
            im = Image.open(src).convert("RGB"); im = im.resize((900, round(im.height * 900 / im.width)), Image.LANCZOS)
            im.quantize(colors=128, method=Image.Quantize.MEDIANCUT).save(src, optimize=True)
            Image.open(src).convert("RGB").resize((450, round(im.height * 450 / 900)), Image.LANCZOS).save(os.path.join(img, f"latest-{short}-{lang}.png"), optimize=True)
    write_index()
    open(os.path.join(ROOT, "last_edition.txt"), "w").write(edition.isoformat())
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    if warnings: print("WARNINGS:\n" + "\n".join(warnings))


def write_index():
    ed = os.path.join(ROOT, "editions"); lines = ["# Editions", "", "| Edition | English | Português |", "|---|---|---|"]
    for e in sorted([x for x in os.listdir(ed) if os.path.isdir(os.path.join(ed, x))], reverse=True):
        cells = []
        for lang in ("en", "pt"):
            p = os.path.join(ed, e, lang)
            pdfs = sorted(f for f in os.listdir(p) if f.endswith(".pdf")) if os.path.isdir(p) else []
            cells.append(" · ".join(f"[{f.rsplit('_', 1)[0].replace('_', ' ')}]({e}/{lang}/{f})" for f in pdfs) or "–")
        lines.append(f"| {e} | {cells[0]} | {cells[1]} |")
    open(os.path.join(ed, "README.md"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
