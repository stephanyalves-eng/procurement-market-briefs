"""Downloads the public data behind the briefs and updates data/public/.

    python pipeline/fetch_public.py bcb bls comex      # all sources (default)
    python pipeline/fetch_public.py bcb                 # one source

Every source fails soft: if an API is down or rate-limited, the previous file is kept, a warning is
printed and the run continues, so a monthly edition is never blocked by one source. The footer of each
brief states the last date each source covers.

Sources
- Banco Central do Brasil, SGS: series 1 (USD PTAX, selling), 21619 (EUR PTAX, selling), 433 (IPCA).
- U.S. Bureau of Labor Statistics, PPI API v2. Set the BLS_API_KEY environment variable (free key)
  to avoid the low daily limit of anonymous requests.
- MDIC Comex Stat: imports of 8807 and 8411 (aerospace) and 8703, 8708, 8507 by NCM (automotive).
"""
import os, sys, time, json
from datetime import date
import requests, pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, "data", "public")
COMEX = "https://api-comexstat.mdic.gov.br"


def log(*a): print(*a, flush=True)


# ---------------------------------------------------------------- BCB
def sgs(code, start_year, end):
    parts = []
    for y in range(start_year, end.year + 1):
        fim = end.strftime("%d/%m/%Y") if y == end.year else f"31/12/{y}"
        for i in range(6):
            try:
                r = requests.get(f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados",
                                 params={"formato": "json", "dataInicial": f"01/01/{y}", "dataFinal": fim}, timeout=90)
                parts.append(pd.DataFrame(r.json())); break
            except Exception:
                time.sleep(5 + 5 * i)
        else:
            raise RuntimeError(f"SGS {code} {y}")
        time.sleep(1)
    df = pd.concat(parts); df["data"] = pd.to_datetime(df.data, dayfirst=True); df["valor"] = df.valor.astype(float)
    return df.drop_duplicates("data")


def fetch_bcb(end):
    usd, eur, ipca = sgs(1, 2019, end), sgs(21619, 2019, end), sgs(433, 2019, end)
    for d in (usd, eur, ipca): d["mes"] = d.data.dt.strftime("%Y-%m")
    fx = pd.DataFrame({"usd_brl_ptax_media": usd.groupby("mes").valor.mean().round(4),
                       "eur_brl_ptax_media": eur.groupby("mes").valor.mean().round(4)})
    fx = fx.join(ipca.set_index("mes").valor.rename("ipca_var_mensal_pct")); fx.index.name = "mes"
    fx.to_csv(os.path.join(PUB, "bcb_cambio_ipca_mensal.csv"))
    daily = usd[["data", "valor"]].rename(columns={"valor": "usd_brl_ptax_venda"}).merge(
        eur[["data", "valor"]].rename(columns={"valor": "eur_brl_ptax_venda"}), on="data", how="outer").sort_values("data")
    daily["data"] = daily.data.dt.strftime("%Y-%m-%d")
    daily.to_csv(os.path.join(PUB, "bcb_ptax_diaria.csv"), index=False)
    log(f"BCB ok: PTAX to {daily.data.max()}")


# ---------------------------------------------------------------- BLS
BLS_SERIES = {"PCU336413336413": "ppi_pecas_aeronauticas_PCU336413", "PCU336412336412": "ppi_motores_aeronauticos_PCU336412",
              "PCU334511334511": "ppi_avionica_navegacao_PCU334511", "WPU102505": "ppi_WPU102505_conferir_titulo",
              "WPU1017": "ppi_aco_laminados_WPU1017"}


def fetch_bls(end):
    body = {"seriesid": list(BLS_SERIES), "startyear": str(end.year - 2), "endyear": str(end.year)}
    if os.environ.get("BLS_API_KEY"): body["registrationkey"] = os.environ["BLS_API_KEY"]
    j = requests.post("https://api.bls.gov/publicAPI/v2/timeseries/data/", json=body, timeout=90).json()
    if j.get("status") != "REQUEST_SUCCEEDED":
        raise RuntimeError("; ".join(j.get("message", [])) or j.get("status"))
    path = os.path.join(PUB, "bls_ppi_aeroespacial_metais_mensal.csv")
    old = pd.read_csv(path).set_index("mes")
    for s in j["Results"]["series"]:
        col = BLS_SERIES[s["seriesID"]]
        for d in s["data"]:
            if d["period"].startswith("M") and d["period"] != "M13" and d["value"] not in ("-", ""):
                old.loc[f"{d['year']}-{d['period'][1:]}", col] = float(d["value"])   # also takes revisions
    old.sort_index().to_csv(path)
    # BLS terms of use: the brief must state the retrieval date, so record the real download day (not the edition date)
    json.dump({"bls_retrieved": date.today().isoformat()}, open(os.path.join(PUB, "bls_status.json"), "w"))
    log(f"BLS ok: PPI to {old.dropna(subset=['ppi_avionica_navegacao_PCU334511']).index.max()}")


# ---------------------------------------------------------------- Comex Stat
def comex_q(body, tries=25):
    for i in range(tries):
        time.sleep(22)                                   # the API allows few requests per minute
        try:
            r = requests.post(COMEX + "/general?language=pt", json=body, timeout=180); j = r.json()
            if r.status_code == 200 and isinstance(j.get("data"), dict) and "list" in j["data"]:
                return j["data"]["list"]
            log("comex retry", r.status_code, str(j)[:120])
        except Exception as e:
            log("comex retry", e)
        time.sleep(25 + 10 * i)
    raise RuntimeError("Comex Stat did not answer")


def comex_last_month():
    j = requests.get(COMEX + "/general/dates/updated", timeout=60).json()["data"]
    return int(j["year"]), int(j["monthNumber"]), j["updated"]


def half_years(last_month):
    return ((1, 6), (7, last_month)) if last_month > 6 else ((1, last_month),)


def rows(lst, metric_stat):
    out = []
    for x in lst:
        code = x.get("coNcm") or x.get("headingCode") or x.get("coHeading")
        out.append(dict(mes=f"{x['year']}-{int(x['monthNumber']):02d}", codigo=str(code), pais_origem=x["country"],
                        valor_fob_usd=int(x["metricFOB"]), peso_liquido_kg=int(x["metricKG"]),
                        **({"qtd_estatistica": float(x.get("metricStatistic") or 0)} if metric_stat else {})))
    return out


def fetch_comex(end):
    y, m, upd = comex_last_month(); log(f"Comex Stat has data to {y}-{m:02d} (updated {upd})")
    # aerospace: four years, full months available, all origin countries
    aero = []
    for a in range(y - 3, y + 1):
        fim = m if a == y else 12
        for ini, end_m in half_years(fim):            # half-year blocks: full-year requests hit the rate limit far more often
            aero += rows(comex_q({"flow": "import", "monthDetail": True, "period": {"from": f"{a}-{ini:02d}", "to": f"{a}-{end_m:02d}"},
                                  "filters": [{"filter": "heading", "values": ["8807", "8411"]}], "details": ["country", "heading"],
                                  "metrics": ["metricFOB", "metricKG"]}), False)
            log("aero", a, ini, "ok")
    pd.DataFrame(aero).rename(columns={"codigo": "ncm_posicao"}).sort_values(["mes", "ncm_posicao", "pais_origem"]) \
        .to_csv(os.path.join(PUB, "comex_aero_8807_8411.csv"), index=False)
    # automotive: refresh the current year (and the previous one early in the year, when revisions still land)
    path = os.path.join(PUB, "comex_auto_8703_8708_8507.csv")
    old = pd.read_csv(path, dtype={"ncm": str})
    years = [y - 1, y] if m <= 3 else [y]
    new = []
    for a in years:
        fim = m if a == y else 12
        for ini, end_m in half_years(fim):
            new += rows(comex_q({"flow": "import", "monthDetail": True, "period": {"from": f"{a}-{ini:02d}", "to": f"{a}-{end_m:02d}"},
                                 "filters": [{"filter": "heading", "values": ["8703", "8708", "8507"]}], "details": ["country", "ncm"],
                                 "metrics": ["metricFOB", "metricKG", "metricStatistic"]}), True)
            log("auto", a, ini, "ok")
    new = pd.DataFrame(new).rename(columns={"codigo": "ncm"})
    keep = old[~old.mes.str[:4].astype(int).isin(years)]
    pd.concat([keep, new], ignore_index=True).sort_values(["mes", "ncm", "pais_origem"]).to_csv(path, index=False)
    json.dump({"comex_last_month": f"{y}-{m:02d}", "comex_updated": upd}, open(os.path.join(PUB, "comex_status.json"), "w"))


SOURCES = {"bcb": fetch_bcb, "bls": fetch_bls, "comex": fetch_comex}

if __name__ == "__main__":
    end = date.fromisoformat(os.environ["EDITION_DATE"]) if os.environ.get("EDITION_DATE") else date.today()
    failed = []
    for name in [a for a in sys.argv[1:] if a in SOURCES] or list(SOURCES):
        try:
            SOURCES[name](end)
        except Exception as e:
            failed.append(name); log(f"WARNING {name} failed, keeping the previous file: {e}")
    if failed:
        with open(os.path.join(ROOT, "fetch_warnings.txt"), "w") as f: f.write(",".join(failed))
