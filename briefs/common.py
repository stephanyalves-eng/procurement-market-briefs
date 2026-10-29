"""Helpers shared by the three briefs: paths, number formatting in EN and PT-BR, month and country names,
edition context and FX event detection."""
import os, json
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, "data", "public")
SYN = os.path.join(ROOT, "data", "synthetic")

MONTHS = {"en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
          "pt": ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]}
MON = {"en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
       "pt": ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]}

# Comex Stat country names (Portuguese) -> display names
COUNTRY = {
    "Estados Unidos": ("United States", "Estados Unidos"), "Portugal": ("Portugal", "Portugal"), "Brasil": ("Brazil (re-imports)", "Brasil (reimportação)"),
    "França": ("France", "França"), "México": ("Mexico", "México"), "Alemanha": ("Germany", "Alemanha"), "Canadá": ("Canada", "Canadá"),
    "Reino Unido": ("United Kingdom", "Reino Unido"), "Itália": ("Italy", "Itália"), "China": ("China", "China"), "Japão": ("Japan", "Japão"),
    "Coreia do Sul": ("South Korea", "Coreia do Sul"), "Argentina": ("Argentina", "Argentina"), "Espanha": ("Spain", "Espanha"),
    "Turquia": ("Türkiye", "Turquia"), "Índia": ("India", "Índia"), "Hong Kong": ("Hong Kong", "Hong Kong"), "Suécia": ("Sweden", "Suécia"),
    "Tailândia": ("Thailand", "Tailândia"), "Eslováquia": ("Slovakia", "Eslováquia"), "Israel": ("Israel", "Israel"), "Suíça": ("Switzerland", "Suíça"),
    "Países Baixos (Holanda)": ("Netherlands", "Países Baixos"), "Bélgica": ("Belgium", "Bélgica"), "Áustria": ("Austria", "Áustria"),
}
ARTICLE_EN = {"United States", "United Kingdom", "Netherlands"}
ARTICLE_PT = {"Estados Unidos": "os", "Reino Unido": "o", "Canadá": "o", "México": "o", "Japão": "o", "Brasil (reimportação)": "o",
              "Países Baixos": "os", "França": "a", "Alemanha": "a", "Itália": "a", "China": "a", "Espanha": "a", "Coreia do Sul": "a",
              "Argentina": "a", "Turquia": "a", "Índia": "a", "Suécia": "a", "Suíça": "a", "Bélgica": "a", "Áustria": "a", "Eslováquia": "a"}


def bls_notice():
    """Attribution required by the BLS API terms of use, in English word for word in both languages.
    The retrieval date comes from data/public/bls_status.json, written by pipeline/fetch_public.py."""
    p = os.path.join(PUB, "bls_status.json")
    ret = pd.Timestamp(json.load(open(p))["bls_retrieved"]).date() if os.path.exists(p) else None
    when = f" Data retrieved on {MONTHS['en'][ret.month-1]} {ret.day}, {ret.year}." if ret else ""
    return (f"Data source: U.S. Bureau of Labor Statistics (BLS).{when}"
            " BLS.gov cannot vouch for the data or analyses derived from these data after the data have been retrieved from BLS.gov.")


def country(name, lang): return COUNTRY.get(name, (name, name))[0 if lang == "en" else 1]


def country_subject(name, lang):
    """Country as the subject of a sentence: 'the United States', 'os Estados Unidos'."""
    c = country(name, lang)
    if lang == "en": return ("the " + c) if c in ARTICLE_EN else c
    art = ARTICLE_PT.get(c); return f"{art} {c}" if art else c


def num(v, d=1, lang="en", sign=False):
    s = f"{v:+,.{d}f}" if sign else f"{v:,.{d}f}"
    if lang == "pt": s = s.replace(",", "§").replace(".", ",").replace("§", ".")
    return s


def pct(v, d=1, lang="en", sign=False): return num(v, d, lang, sign) + "%"


def pp(v, d=1, lang="en"): return num(v, d, lang, sign=True) + " pp"


def usd(lang): return "USD" if lang == "en" else "US$"


def T(lang, en, pt): return en if lang == "en" else pt


def day_month(d, lang, short=True):
    """'28 Oct' / '28/10'."""
    return f"{d.day} {MON['en'][d.month-1]}" if lang == "en" else f"{d.day:02d}/{d.month:02d}"


def long_date(d, lang):
    return f"{d.day} {MONTHS['en'][d.month-1]} {d.year}" if lang == "en" else f"{d.day} de {MONTHS['pt'][d.month-1]} de {d.year}"


def edition_label(d, lang):
    return f"{d.day} {MON['en'][d.month-1]} {d.year}" if lang == "en" else f"{d.day:02d}/{d.month:02d}/{d.year}"


def period_label(m_from, m_to, lang):
    """Jan–Sep / jan. a set."""
    if lang == "en": return f"{MON['en'][m_from-1]}–{MON['en'][m_to-1]}" if m_from != m_to else MON['en'][m_to-1]
    return f"{MON['pt'][m_from-1]}–{MON['pt'][m_to-1]}" if m_from != m_to else MON['pt'][m_to-1]


def context(edition, lang, key):
    """Optional human-written context for one edition (config/context.json), e.g. an event behind an FX move."""
    p = os.path.join(ROOT, "config", "context.json")
    if not os.path.exists(p): return ""
    return json.load(open(p)).get(edition.isoformat(), {}).get(f"{key}_{lang}", "")


def ptax(edition):
    dd = pd.read_csv(os.path.join(PUB, "bcb_ptax_diaria.csv"), parse_dates=["data"]).set_index("data").sort_index()
    return dd[dd.index <= pd.Timestamp(edition)].dropna(subset=["usd_brl_ptax_venda"])


def fx_event(dd, days=30, threshold=2.0):
    """Largest one-session USD/BRL move in the last `days` days, if it is at least `threshold` percent."""
    last = dd.index.max(); win = dd.loc[last - pd.Timedelta(days=days):].usd_brl_ptax_venda
    chg = dd.usd_brl_ptax_venda.pct_change().loc[win.index] * 100
    if chg.abs().max() < threshold: return None
    t = chg.abs().idxmax(); prev = dd.loc[:t].index[-2]
    return dict(date=t.date(), prev_date=prev.date(), chg=chg.loc[t], before=dd.loc[prev, "usd_brl_ptax_venda"], after=dd.loc[t, "usd_brl_ptax_venda"])


def part_of_month(day, lang):
    if lang == "en": return "early" if day <= 10 else "mid" if day <= 20 else "late"
    return "início de" if day <= 10 else "meados de" if day <= 20 else "fim de"
