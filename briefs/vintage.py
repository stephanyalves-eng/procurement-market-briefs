"""Data vintage of each public series behind an edition: which period it covers, which period it should cover on the
edition date, and whether the data is fresh, carried forward from an earlier download, or from a skipped/failed fetch.

run_edition.py writes this into the manifest ("sources"), turns gaps into warnings, and the briefs print a short
partial-coverage note in their source line when a series they use is behind.

Status of a series
- current          downloaded in this run and covering the expected period
- carried_forward  downloaded in this run, but the source has not released the expected period yet
- fetch_failed     the download failed; the file from an earlier run was kept
- skipped          the run used --skip-fetch; the file in the repository was used as it is

`behind` is True when the series stops before the expected period (partial coverage). `ahead` is True when it goes
past the expected period and the file was downloaded after the edition date, which happens when an old edition is
rebuilt with --skip-fetch from newer files: those values may not have been public on the edition date. The release
days below are typical, not exact, so a gap of a few days around them is expected.
"""
import os, json
from datetime import date, timedelta
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, "data", "public")

# release_day: first day of the month on which the previous month is normally available. Before that day, the
# expected period is two months back. The monthly workflow runs on the 16th so all three are normally in.
SERIES = {
    "bcb_ptax_daily": dict(source="bcb", file="bcb_ptax_diaria.csv", freq="daily", date_col="data", col="usd_brl_ptax_venda",
                           en="BCB PTAX", pt="PTAX do BCB", used_by=["aerospace"]),
    "bcb_ipca_monthly": dict(source="bcb", file="bcb_cambio_ipca_mensal.csv", freq="monthly", col="ipca_var_mensal_pct", release_day=12,
                             en="BCB monthly FX and IPCA", pt="câmbio mensal e IPCA do BCB", used_by=["aerospace", "procurement"]),
    "bls_ppi": dict(source="bls", file="bls_ppi_aeroespacial_metais_mensal.csv", freq="monthly", col=None, release_day=16,
                    en="BLS PPI", pt="PPI do BLS", used_by=["aerospace", "procurement"]),
    "comex_aero": dict(source="comex", file="comex_aero_8807_8411.csv", freq="monthly", col="valor_fob_usd", release_day=10,
                       en="Comex Stat (aerospace)", pt="Comex Stat (aeroespacial)", used_by=["aerospace"]),
    "comex_auto": dict(source="comex", file="comex_auto_8703_8708_8507.csv", freq="monthly", col="qtd_estatistica", release_day=10,
                       en="Comex Stat (automotive)", pt="Comex Stat (automotivo)", used_by=["ev", "sqe"]),
}
MON = {"en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
       "pt": ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]}


def _month(d, back):
    m = pd.Period(d, freq="M") - back; return str(m)


def expected_period(name, edition):
    """Period the series should cover on the edition date."""
    s = SERIES[name]
    if s["freq"] == "daily":                      # last weekday before the edition (PTAX is published in the afternoon)
        d = edition - timedelta(days=1)
        while d.weekday() >= 5: d -= timedelta(days=1)
        return d.isoformat()
    return _month(edition, 1 if edition.day >= s["release_day"] else 2)


def source_period(name, edition, pub=None):
    """Last period the file covers, ignoring anything after the edition date. For a table with several series
    (BLS PPI), the oldest of their last values, so a single late series counts."""
    s = SERIES[name]; df = pd.read_csv(os.path.join(pub or PUB, s["file"]))
    if s["freq"] == "daily":
        df = df[df[s["date_col"]] <= edition.isoformat()].dropna(subset=[s["col"]])
        return str(df[s["date_col"]].max())
    df = df[df.mes <= str(pd.Period(edition, freq="M"))]
    if s["col"] is None:
        df = df.set_index("mes").sort_index(); return min(str(df[c].dropna().index.max()) for c in df.columns)
    return str(df.dropna(subset=[s["col"]]).mes.max())


def _behind(name, period, expected):
    if SERIES[name]["freq"] == "monthly": return period < expected
    # daily: allow one missing business day (a Brazilian holiday) before calling the series late
    d = date.fromisoformat(expected) - timedelta(days=1)
    while d.weekday() >= 5: d -= timedelta(days=1)
    return period < d.isoformat()


def collect(edition, fetched=True, failed=(), pub=None):
    """Vintage of every series on the edition date. `fetched` is False with --skip-fetch; `failed` lists the
    sources whose download failed in this run."""
    pub = pub or PUB; p = os.path.join(pub, "sources_status.json")
    st = json.load(open(p)) if os.path.exists(p) else {}
    out = {}
    for name, s in SERIES.items():
        period, exp = source_period(name, edition, pub), expected_period(name, edition)
        behind = _behind(name, period, exp)
        status = ("skipped" if not fetched else "fetch_failed" if s["source"] in failed
                  else "carried_forward" if behind else "current")
        got = st.get(s["source"], {}).get("fetched_at")
        # values past the expected period are only suspect if the file was downloaded after the edition date
        ahead = s["freq"] == "monthly" and period > exp and (got is None or got[:10] > edition.isoformat())
        out[name] = dict(source=s["source"], file=f"data/public/{s['file']}", source_period=period, expected_period=exp,
                         behind=behind, ahead=ahead, status=status, fetched_at=st.get(s["source"], {}).get("fetched_at"),
                         published_at=st.get(s["source"], {}).get("published_at"), used_by=s["used_by"])
    return out


def warnings(sources):
    """Manifest warnings: every series that is not current, and every series behind its expected period."""
    w = []
    for name, v in sources.items():
        got = f"{name} covers {v['source_period']}, expected {v['expected_period']}"
        if v["behind"]:
            w.append(f"partial coverage: {got}; status {v['status']}, last download {v['fetched_at'] or 'unknown'} "
                     f"(briefs affected: {', '.join(v['used_by'])})")
        elif v["status"] in ("fetch_failed", "skipped"):
            w.append(f"{v['status'].replace('_', ' ')}: {name} from the file downloaded {v['fetched_at'] or 'at an unknown date'}, covers {v['source_period']}")
        if v.get("ahead"):
            w.append(f"possible hindsight: {got}; values after {v['expected_period']} may not have been public on the edition date")
    return w


def _label(period, lang):
    if len(period) == 7:
        y, m = int(period[:4]), int(period[5:]); return f"{MON[lang][m-1]} {y}" if lang == "en" else f"{MON[lang][m-1]}/{y}"
    d = date.fromisoformat(period); return f"{d.day} {MON['en'][d.month-1]} {d.year}" if lang == "en" else f"{d:%d/%m/%Y}"


def coverage_note(brief, edition, lang, pub=None):
    """One sentence for the brief's source line when a series it uses is behind; empty when all are in."""
    parts = []
    for name, s in SERIES.items():
        if brief not in s["used_by"]: continue
        period, exp = source_period(name, edition, pub), expected_period(name, edition)
        if _behind(name, period, exp):
            parts.append(f"{s['en']} through {_label(period, 'en')} ({_label(exp, 'en')} not yet available)" if lang == "en"
                         else f"{s['pt']} até {_label(period, 'pt')} ({_label(exp, 'pt')} ainda indisponível)")
    if not parts: return ""
    return ("Partial coverage: " if lang == "en" else "Cobertura parcial: ") + "; ".join(parts) + "."
