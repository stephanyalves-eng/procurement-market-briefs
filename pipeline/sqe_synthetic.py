"""Synthetic supplier quality dataset for a fictitious EV assembler in Brazil with a Chinese parent company.

Nothing here describes a real company. The plant, the suppliers and every record are invented. The scenario follows
public facts only at the level of context: Chinese-owned EV plants in Brazil started from imported kits and are
localizing parts ahead of the import duty on assembly kits reaching 35% in January 2027.

The whole history (2025 to 2028) is generated in memory from fixed seeds, so it never needs to be stored or extended.
`view(cutoff)` returns only what a supplier quality engineer would see on the cutoff date: receipts and issues up to
that day, containment and closure dates only once they happened, PPAP decisions only once they were made.

    python pipeline/sqe_synthetic.py 2026-10-31     # exports the view as of that date to data/synthetic/sqe/
"""
import os, sys
from datetime import date, timedelta
import numpy as np, pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "synthetic", "sqe")
START, END = date(2025, 1, 1), date(2028, 12, 31)

# origin: CN = imported from China, BR = local supplier in Brazil, OT = other imports
# columns: id, name, origin, commodity, iatf (Sim/Não/Em certificação), localization wave (0 = not localized)
SUPPLIERS = [
    ("S01", "Jiangtai Battery Systems Co.", "CN", "Battery cells and modules", "Sim", 0),
    ("S02", "Shenglan E-Drive Co.", "CN", "Electric drive unit", "Sim", 0),
    ("S03", "Qianhe Vehicle Electronics Co.", "CN", "Control units and BMS", "Sim", 0),
    ("S04", "Tianrui Body Kit Co.", "CN", "Body-in-white kits (SKD/CKD)", "Sim", 0),
    ("S05", "Yuhang Interior Systems Co.", "CN", "Interior trim kits", "Sim", 0),
    ("S06", "Lianfeng Chassis Co.", "CN", "Suspension and chassis", "Sim", 0),
    ("S07", "Haode Wiring Co.", "CN", "Wiring harness", "Sim", 0),
    ("S08", "Mingrui Thermal Co.", "CN", "Thermal management", "Sim", 0),
    ("S09", "Kaiyuan Lighting Co.", "CN", "Lighting", "Sim", 0),
    ("S10", "Ruixing Fasteners Co.", "CN", "Fasteners", "Não", 0),
    ("S11", "Bocheng Charging Co.", "CN", "On-board charger", "Sim", 0),
    ("S12", "Xinda Display Co.", "CN", "Displays and infotainment", "Sim", 0),
    ("B01", "Serra Azul Plásticos", "BR", "Bumpers and exterior plastics", "Sim", 1),
    ("B02", "Rodovale Pneus", "BR", "Tires", "Sim", 1),
    ("B03", "Ipê Assentos Automotivos", "BR", "Seats", "Sim", 1),
    ("B04", "Vidraria Atlântica", "BR", "Glass", "Sim", 2),
    ("B05", "Chicotes Paraguaçu", "BR", "Wiring harness", "Em certificação", 2),
    ("B06", "Estamparia Recôncavo", "BR", "Stamped body parts", "Sim", 2),
    ("B07", "Baterias Camassari Montagem", "BR", "Battery pack assembly", "Em certificação", 3),
    ("B08", "Forjados Planalto", "BR", "Forged and machined chassis parts", "Sim", 3),
    ("B09", "Tapetes e Acústica Sertão", "BR", "Carpets and acoustics", "Não", 3),
    ("B10", "Fixadores Baiano", "BR", "Fasteners", "Sim", 3),
    ("B11", "Luzes do Litoral", "BR", "Lighting", "Em certificação", 3),
    ("B12", "Térmica Nordeste", "BR", "Thermal management", "Sim", 3),
    ("O01", "Bavaria Sensorik GmbH", "OT", "Sensors and ADAS", "Sim", 0),
    ("O02", "Toluca Frenos S.A.", "OT", "Brake systems", "Sim", 0),
]
ORIGIN = {"CN": ("China imports", "Importados da China"), "BR": ("Local (Brazil)", "Locais (Brasil)"), "OT": ("Other imports", "Outras importações")}
# defect codes per origin with weights
DEFECTS = {
    "CN": [("Corrosion after sea transport", .22), ("Packaging and transport damage", .20), ("Wrong revision (ECN not communicated)", .16),
           ("Labeling and documentation", .16), ("Functional or electrical test failure", .14), ("Dimensional out of tolerance", .12)],
    "BR": [("Dimensional out of tolerance", .30), ("Appearance and paint", .22), ("Missing or incomplete PPAP documentation", .14),
           ("Functional or electrical test failure", .12), ("Weld and joining", .12), ("Packaging and transport damage", .10)],
    "OT": [("Functional or electrical test failure", .40), ("Labeling and documentation", .30), ("Packaging and transport damage", .30)],
}
DEFECT_PT = {"Corrosion after sea transport": "Corrosão no transporte marítimo", "Packaging and transport damage": "Embalagem e dano no transporte",
             "Wrong revision (ECN not communicated)": "Revisão errada (ECN não comunicada)", "Labeling and documentation": "Etiquetagem e documentação",
             "Functional or electrical test failure": "Falha em teste funcional ou elétrico", "Dimensional out of tolerance": "Dimensional fora de tolerância",
             "Appearance and paint": "Aparência e pintura", "Missing or incomplete PPAP documentation": "Documentação de PPAP ausente ou incompleta",
             "Weld and joining": "Solda e união"}
# localization waves: PPAP due window (local parts replacing imported content)
WAVES = {1: (date(2025, 4, 1), date(2025, 9, 30), 24), 2: (date(2025, 10, 1), date(2026, 3, 31), 36), 3: (date(2026, 6, 1), date(2026, 12, 15), 54)}
# plant output (vehicles per month): kit assembly ramping to the 150k/year nameplate
def vehicles(m):  # m: months since Jan 2025
    return int(3000 + 9500 / (1 + np.exp(-(m - 20) / 5)))

TARGETS = dict(ppm=300, containment_24h=95.0, closure_30d=85.0, ppap_first_pass=80.0, audit_score=80.0)


def _sop(wave):
    """Start of serial supply for a localized supplier: end of its PPAP window."""
    return WAVES[wave][1] if wave else START


def generate():
    rng = np.random.default_rng(20261103)
    sup = pd.DataFrame(SUPPLIERS, columns=["id_fornecedor", "fornecedor", "origem", "commodity", "iatf_16949", "onda_nacionalizacao"])
    # ---------- receipts (one row per lot) ----------
    rec, iss = [], []
    base_rate = {"CN": .068, "BR": .042, "OT": .025}     # probability that a lot has a defect event, steady state
    for s in sup.itertuples():
        start = START if s.origem != "BR" else _sop(s.onda_nacionalizacao) - timedelta(days=60)
        quality = rng.lognormal(0, .35)                  # supplier-specific multiplier
        if s.iatf_16949 != "Sim": quality *= 1.5
        lots_week = 5 if s.origem == "BR" else 2         # sea freight arrives in fewer, larger lots
        d = start
        while d <= END:
            m = (d.year - 2025) * 12 + d.month - 1
            share = 1.0
            if s.origem == "CN" and s.commodity in {"Battery cells and modules", "Body-in-white kits (SKD/CKD)", "Interior trim kits", "Wiring harness",
                                                     "Thermal management", "Lighting", "Fasteners"}:
                # imported content shrinks as local suppliers of the same commodity take over
                twins = sup[(sup.origem == "BR") & (sup.commodity.str.split().str[0] == s.commodity.split()[0])]
                if len(twins) and d >= _sop(int(twins.onda_nacionalizacao.min())): share = .35
            qty = max(20, int(vehicles(m) * share * rng.uniform(2, 6) / (4.3 * lots_week)))
            if s.origem == "BR":
                months_since = (d - _sop(s.onda_nacionalizacao)).days / 30.4
                launch = 1 + 2.4 * np.exp(-max(months_since, -2) / 4.5)   # launch curve: high defect rate, learning over ~6 months
            else:
                launch = 1.0
            humid = 1.35 if (s.origem == "CN" and d.month in (1, 2, 3, 12)) else 1.0   # southern summer, longer humid voyages
            p = base_rate[s.origem] * quality * launch * humid
            for _ in range(lots_week):
                dd = d + timedelta(days=int(rng.integers(0, 7)))
                if dd > END: break
                rej = 0
                if rng.random() < p:
                    rej = max(1, int(qty * rng.uniform(.001, .008)))
                    dfx = DEFECTS[s.origem]; code = dfx[int(rng.choice(len(dfx), p=[w for _, w in dfx]))][0]
                    src = rng.choice(["Incoming inspection", "Assembly line", "Field"], p=[.68, .27, .05])
                    tz = 1.9 if s.origem == "CN" else 1.0          # time zone and language add hours to containment
                    cont_h = float(rng.lognormal(np.log(11 * tz), .55))
                    close_d = int(rng.gamma(2.6, (8.0 if s.origem != "CN" else 11.0) * (1.25 if launch > 1.6 else 1)))
                    copq = float(rej * rng.uniform(25, 140) + (rng.uniform(4000, 22000) if src == "Assembly line" else 0) + (rng.uniform(15000, 60000) if src == "Field" else 0))
                    recov = rng.random() < (.78 if s.origem == "BR" else .45 if s.origem == "CN" else .65)
                    iss.append(dict(id_problema=None, data_abertura=dd, id_fornecedor=s.id_fornecedor, origem=s.origem, defeito=code, deteccao=src,
                                    qtd_rejeitada=rej, contencao_horas=round(cont_h, 1), data_contencao=pd.Timestamp(dd) + pd.Timedelta(hours=8 + cont_h),
                                    data_encerramento_8d=dd + timedelta(days=close_d + 1), copq_usd=round(copq, 2),
                                    recuperado_usd=round(copq * rng.uniform(.6, 1.0), 2) if recov else 0.0))
                rec.append(dict(data_recebimento=dd, id_fornecedor=s.id_fornecedor, origem=s.origem, qtd_recebida=qty, qtd_rejeitada=rej))
            d += timedelta(days=7)
    R = pd.DataFrame(rec).sort_values("data_recebimento").reset_index(drop=True)
    I = pd.DataFrame(iss).sort_values("data_abertura").reset_index(drop=True)
    I["id_problema"] = [f"QI-{25000 + i}" for i in range(len(I))]
    R["data_recebimento"] = pd.to_datetime(R.data_recebimento)
    for c in ("data_abertura", "data_encerramento_8d"): I[c] = pd.to_datetime(I[c])
    I["data_abertura"] = I.data_abertura + pd.Timedelta(hours=8)
    # ---------- PPAP for localized parts ----------
    pp, n = [], 0
    for w, (a, b, nparts) in WAVES.items():
        sup_w = sup[sup.onda_nacionalizacao == w]
        for i in range(nparts):
            s = sup_w.iloc[i % len(sup_w)]; n += 1
            due = a + timedelta(days=int(rng.integers(0, (b - a).days + 1)))
            slip = {1: 4, 2: 9, 3: 26}[w]                # wave 3: compressed timeline ahead of the January 2027 kit duty
            if s.iatf_16949 != "Sim": slip += 12
            sub = due + timedelta(days=int(rng.normal(slip, 14)))
            first_pass = rng.random() < ({1: .82, 2: .78, 3: .64}[w] - (.12 if s.iatf_16949 != "Sim" else 0))
            dec = sub + timedelta(days=int(rng.integers(5, 16)))
            res = "Approved" if first_pass else rng.choice(["Rejected", "Interim approval"], p=[.6, .4])
            final = dec if first_pass else dec + timedelta(days=int(rng.integers(20, 50)))
            pp.append(dict(id_ppap=f"PPAP-{n:03d}", onda=w, id_fornecedor=s.id_fornecedor, commodity=s.commodity, part_number=f"BR-{w}{i:03d}",
                           data_prevista=due, data_submissao=sub, data_decisao=dec, decisao_1=res, aprovacao_final=final))
    P = pd.DataFrame(pp)
    for c in ("data_prevista", "data_submissao", "data_decisao", "aprovacao_final"): P[c] = pd.to_datetime(P[c])
    # ---------- process audits (VDA 6.3 style score, %) ----------
    au = []
    for s in sup.itertuples():
        first = (_sop(s.onda_nacionalizacao) - timedelta(days=int(rng.integers(60, 130)))) if s.origem == "BR" else START + timedelta(days=int(rng.integers(30, 300)))
        d, k = first, 0
        while d <= END:
            mu = 79 if (s.origem == "BR" and k == 0) else 84 if s.origem == "BR" else 86
            if s.iatf_16949 != "Sim": mu -= 5
            au.append(dict(data_auditoria=d, id_fornecedor=s.id_fornecedor, origem=s.origem, nota_pct=round(float(np.clip(rng.normal(mu, 5), 55, 98)), 1)))
            d += timedelta(days=int(rng.integers(300, 400)) if k else int(rng.integers(150, 220))); k += 1
    A = pd.DataFrame(au).sort_values("data_auditoria").reset_index(drop=True); A["data_auditoria"] = pd.to_datetime(A.data_auditoria)
    return sup, R, I, P, A


_CACHE = {}


def view(cutoff):
    """What a supplier quality engineer sees on `cutoff` (inclusive)."""
    if "g" not in _CACHE: _CACHE["g"] = generate()
    sup, R, I, P, A = _CACHE["g"]
    c = pd.Timestamp(cutoff) + pd.Timedelta(hours=23, minutes=59)
    R = R[R.data_recebimento <= c].copy()
    I = I[I.data_abertura <= c].copy()
    I.loc[I.data_contencao > c, ["data_contencao", "contencao_horas"]] = [pd.NaT, np.nan]
    I.loc[I.data_encerramento_8d > c, "data_encerramento_8d"] = pd.NaT
    I["status"] = np.where(I.data_encerramento_8d.isna(), "Open", "Closed")
    P = P[P.data_prevista <= c + pd.Timedelta(days=120)].copy()      # parts in the plan for the next four months
    P.loc[P.data_submissao > c, ["data_submissao", "data_decisao", "decisao_1", "aprovacao_final"]] = [pd.NaT, pd.NaT, None, pd.NaT]
    P.loc[P.data_decisao > c, ["data_decisao", "decisao_1", "aprovacao_final"]] = [pd.NaT, None, pd.NaT]
    P.loc[P.aprovacao_final > c, "aprovacao_final"] = pd.NaT
    A = A[A.data_auditoria <= c].copy()
    return sup, R, I, P, A


def export(cutoff):
    sup, R, I, P, A = view(cutoff); os.makedirs(OUT, exist_ok=True)
    for df, f in ((sup, "fornecedores"), (R, "recebimentos"), (I, "problemas_qualidade"), (P, "ppap_nacionalizacao"), (A, "auditorias")):
        df.to_csv(os.path.join(OUT, f + ".csv"), index=False, date_format="%Y-%m-%d %H:%M" if f == "problemas_qualidade" else "%Y-%m-%d")
    pd.DataFrame([dict(mes=f"{y}-{m:02d}", **TARGETS) for y in range(2025, 2029) for m in range(1, 13)]).to_csv(os.path.join(OUT, "metas_mensais.csv"), index=False)


if __name__ == "__main__":
    export(date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today())


# ---------- root cause (6M) for non-conformance analysis ----------
# Assigned per issue with its own random stream (seeded by the issue number), so the history above does not change.
ROOT_CAUSES = {
    "Corrosion after sea transport": [("Environment", "Humidity in containers on long voyages", .55), ("Material", "Packaging without corrosion inhibitor", .45)],
    "Packaging and transport damage": [("Method", "Packaging specification not adapted to the route", .6), ("Man", "Incorrect stacking or handling", .4)],
    "Wrong revision (ECN not communicated)": [("Method", "Engineering change not communicated to the supplier", .75), ("Man", "Old drawing used at the supplier", .25)],
    "Labeling and documentation": [("Method", "Label and document template not standardized", .6), ("Man", "Manual labeling error", .4)],
    "Functional or electrical test failure": [("Material", "Defective sub-component from a sub-supplier", .55), ("Machine", "Test station out of calibration", .45)],
    "Dimensional out of tolerance": [("Machine", "Worn tooling or fixture", .5), ("Measurement", "Gauge or measurement method not validated", .3), ("Method", "Process parameters not frozen after launch", .2)],
    "Appearance and paint": [("Machine", "Paint line parameters unstable", .55), ("Man", "Operator not trained on the appearance standard", .45)],
    "Missing or incomplete PPAP documentation": [("Method", "PPAP checklist not followed", .7), ("Man", "New supplier unfamiliar with PPAP requirements", .3)],
    "Weld and joining": [("Machine", "Welding parameters drifting", .6), ("Man", "Welder qualification not verified", .4)],
}
CAUSE_PT = {"Environment": "Meio ambiente", "Material": "Material", "Method": "Método", "Man": "Mão de obra", "Machine": "Máquina", "Measurement": "Medição",
            "Humidity in containers on long voyages": "Umidade no contêiner em viagens longas", "Packaging without corrosion inhibitor": "Embalagem sem inibidor de corrosão",
            "Packaging specification not adapted to the route": "Especificação de embalagem inadequada à rota", "Incorrect stacking or handling": "Empilhamento ou manuseio incorreto",
            "Engineering change not communicated to the supplier": "Mudança de engenharia não comunicada ao fornecedor", "Old drawing used at the supplier": "Desenho antigo em uso no fornecedor",
            "Label and document template not standardized": "Modelo de etiqueta e documento não padronizado", "Manual labeling error": "Erro manual de etiquetagem",
            "Defective sub-component from a sub-supplier": "Subcomponente defeituoso de subfornecedor", "Test station out of calibration": "Bancada de teste fora de calibração",
            "Worn tooling or fixture": "Ferramental ou dispositivo desgastado", "Gauge or measurement method not validated": "Calibrador ou método de medição não validado",
            "Process parameters not frozen after launch": "Parâmetros de processo não congelados após o lançamento", "Paint line parameters unstable": "Parâmetros da linha de pintura instáveis",
            "Operator not trained on the appearance standard": "Operador sem treinamento no padrão de aparência", "PPAP checklist not followed": "Checklist de PPAP não seguido",
            "New supplier unfamiliar with PPAP requirements": "Fornecedor novo sem domínio dos requisitos de PPAP", "Welding parameters drifting": "Parâmetros de solda variando",
            "Welder qualification not verified": "Qualificação do soldador não verificada"}


def root_cause(I):
    """Adds 6M category and root cause to closed issues (the root cause is known once the 8D reaches D4 and closes).
    Open issues stay 'Under investigation'."""
    I = I.copy(); cat, cause = [], []
    for r in I.itertuples():
        rng = np.random.default_rng(int(r.id_problema[3:]))
        opts = ROOT_CAUSES[r.defeito]; k = int(rng.choice(len(opts), p=[o[2] for o in opts]))
        cat.append(opts[k][0]); cause.append(opts[k][1])
    I["categoria_6m"] = cat; I["causa_raiz"] = cause
    if "status" in I:
        I.loc[I.status == "Open", ["categoria_6m", "causa_raiz"]] = ["Under investigation", "Under investigation"]
    return I
