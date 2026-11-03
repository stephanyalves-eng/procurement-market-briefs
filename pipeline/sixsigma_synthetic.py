"""Synthetic Six Sigma layer for the fictitious EV plant in pipeline/sqe_synthetic.py.

Two things the supplier quality dataset does not have on its own:
1. Measurements of one critical characteristic at a local launch supplier, for process capability (Cp, Cpk).
   Subgroups of 5 parts, 5 subgroups per week, from the supplier's first serial lot. The process starts off-centre
   and wide after launch and improves as the DMAIC project on it progresses.
2. A portfolio of DMAIC projects with planned and actual phase gates.

Everything is invented and deterministic (fixed seeds), so any cutoff date reproduces the same history.
"""
from datetime import date, timedelta
import numpy as np, pandas as pd

# critical characteristic: bumper mounting point position at Serra Azul Plásticos (B01), nominal 0, tolerance ±0.50 mm
CHAR = dict(supplier="B01", name_en="Bumper mounting point position", name_pt="Posição do ponto de fixação do para-choque",
            unit="mm", lsl=-0.50, usl=0.50, start=date(2025, 8, 4))

# DMAIC portfolio. Phase lengths in weeks (D, M, A, I, C); slip = weeks lost per phase by the actual project.
PROJECTS = [
    dict(id="SS-01", en="Corrosion on sea-freight parts from China", pt="Corrosão em peças importadas por via marítima",
         metric="ppm_corrosion_cn", start=date(2026, 3, 2), weeks=(3, 5, 6, 8, 4), slip=(0, 1, 2, 0, 0), belt="Green Belt"),
    dict(id="SS-02", en="Mounting point variation at Serra Azul Plásticos", pt="Variação do ponto de fixação na Serra Azul Plásticos",
         metric="cpk", start=date(2026, 5, 4), weeks=(2, 5, 5, 8, 4), slip=(0, 0, 3, 2, 0), belt="Black Belt"),
    dict(id="SS-03", en="24-hour containment with China-based suppliers", pt="Contenção em 24 h com fornecedores chineses",
         metric="c24_cn", start=date(2026, 7, 6), weeks=(2, 4, 4, 6, 4), slip=(1, 2, 0, 0, 0), belt="Green Belt"),
    dict(id="SS-04", en="Dimensional defects at local suppliers", pt="Defeitos dimensionais em fornecedores locais",
         metric="ppm_dim_br", start=date(2026, 9, 7), weeks=(2, 4, 5, 6, 4), slip=(0, 0, 0, 0, 0), belt="Green Belt"),
    dict(id="SS-05", en="Wave 3 PPAP first-time approval", pt="Aprovação de primeira do PPAP da onda 3",
         metric="ppap_fp_w3", start=date(2026, 8, 3), weeks=(2, 3, 4, 6, 4), slip=(0, 1, 1, 0, 0), belt="Green Belt"),
]
PHASES = ["Define", "Measure", "Analyze", "Improve", "Control"]


def measurements(end):
    """Subgroups (5 parts) of the critical characteristic from launch to `end`."""
    rng = np.random.default_rng(20261104)
    rows, d, k = [], CHAR["start"], 0
    imp = PROJECTS[1]["start"] + timedelta(weeks=sum(a + b for a, b in zip(PROJECTS[1]["weeks"][:3], PROJECTS[1]["slip"][:3])))   # improve gate
    while d <= end:
        weeks = (d - CHAR["start"]).days / 7
        mean = .22 * np.exp(-weeks / 40) + .06            # off-centre after launch, drifting back slowly
        sd = .17 * np.exp(-weeks / 70) + .07
        if d >= imp:                                       # fixture change from the DMAIC project
            t = (d - imp).days / 7; mean *= np.exp(-t / 6); sd *= .8 + .2 * np.exp(-t / 6)
        for s in range(5):
            sub_d = d + timedelta(days=s)
            shift = rng.normal(0, sd * .35)                # between-subgroup variation
            for x in rng.normal(mean + shift, sd * .9, 5):
                rows.append(dict(data=sub_d, subgrupo=k, valor_mm=round(float(x), 3)))
            k += 1
        d += timedelta(days=7)
    df = pd.DataFrame(rows); df["data"] = pd.to_datetime(df.data)
    return df


def project_status(cutoff):
    """Phase each project is in on `cutoff`, against its plan."""
    c = pd.Timestamp(cutoff); out = []
    for p in PROJECTS:
        plan, act = [pd.Timestamp(p["start"])], [pd.Timestamp(p["start"])]
        for w, s in zip(p["weeks"], p["slip"]):
            plan.append(plan[-1] + pd.Timedelta(weeks=w)); act.append(act[-1] + pd.Timedelta(weeks=w + s))
        if c < act[0]: continue
        ph_act = next((i for i in range(5) if c < act[i + 1]), 5)          # 5 = closed
        ph_plan = next((i for i in range(5) if c < plan[i + 1]), 5)
        out.append(dict(id=p["id"], en=p["en"], pt=p["pt"], metric=p["metric"], belt=p["belt"], start=p["start"],
                        phase=ph_act, phase_plan=ph_plan, late_weeks=max(0, round((act[min(ph_act, 4) + 0].value - plan[min(ph_act, 4)].value) / 6.048e14)),
                        gate_improve=act[3], end_plan=plan[5], end_act=act[5]))
    return pd.DataFrame(out)
