"""Monthly Supplier Quality Report for a fictitious EV assembler in Brazil with a Chinese parent company (synthetic data).
Public data gives the context (China's share of electrified car imports, the January 2027 duty on assembly kits);
every quality number comes from pipeline/sqe_synthetic.py. Headline, highlights and actions are generated from the data."""
import os, sys, calendar
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from .style import C, svg, rows_grid, footer, render_fit
from .common import ROOT, PUB, MON, MONTHS, T, num, pct, pp, usd, edition_label, coverage_note, with_note

sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import sqe_synthetic as sq  # noqa: E402

ORG = {"BR": ("Local (Brazil)", "Locais (Brasil)"), "CN": ("China imports", "Importados da China"), "OT": ("Other imports", "Outras importações")}
ORG_S = {"BR": ("Local", "Locais"), "CN": ("China", "China"), "OT": ("Other", "Outros")}
O = lambda d, k, lang: d[k][0 if lang == "en" else 1]
DEF = lambda code, lang: code if lang == "en" else sq.DEFECT_PT.get(code, code)
COMM_PT = {"Battery cells and modules": "Células e módulos de bateria", "Electric drive unit": "Motor elétrico (e-drive)", "Control units and BMS": "Centrais eletrônicas e BMS",
           "Body-in-white kits (SKD/CKD)": "Kits de carroceria (SKD/CKD)", "Interior trim kits": "Kits de acabamento interno", "Suspension and chassis": "Suspensão e chassi",
           "Wiring harness": "Chicote elétrico", "Thermal management": "Gerenciamento térmico", "Lighting": "Iluminação", "Fasteners": "Fixadores",
           "On-board charger": "Carregador embarcado", "Displays and infotainment": "Telas e multimídia", "Bumpers and exterior plastics": "Para-choques e plásticos externos",
           "Tires": "Pneus", "Seats": "Bancos", "Glass": "Vidros", "Stamped body parts": "Estampados de carroceria", "Battery pack assembly": "Pack de bateria",
           "Forged and machined chassis parts": "Forjados de chassi", "Carpets and acoustics": "Carpetes e acústica", "Sensors and ADAS": "Sensores e ADAS",
           "Brake systems": "Sistemas de freio"}
COMM = lambda c, lang: c if lang == "en" else COMM_PT.get(c, c)


def public_context():
    """China's share of electrified car imports (units, year to date) from Comex Stat, if the file is available."""
    p = os.path.join(PUB, "comex_auto_8703_8708_8507.csv")
    if not os.path.exists(p): return None
    d = pd.read_csv(p, dtype={"ncm": str}); d["ano"] = d.mes.str[:4].astype(int); d["mm"] = d.mes.str[5:].astype(int)
    e = d[d.ncm.str[:6].isin(["870380", "870360", "870370", "870340", "870350"])]
    Y = e.ano.max(); Lm = e[e.ano == Y].mm.max(); e = e[(e.ano == Y)]
    return dict(year=Y, month=Lm, china=e[e.pais_origem == "China"].qtd_estatistica.sum() / e.qtd_estatistica.sum() * 100)


def build(edition, cutoff, lang, outdir, png=True):
    sup, R, I, P, A = sq.view(cutoff); tg = sq.TARGETS
    c_end = pd.Timestamp(cutoff) + pd.Timedelta(hours=23, minutes=59)
    CUR = cutoff.strftime("%Y-%m"); dim = calendar.monthrange(cutoff.year, cutoff.month)[1]; mtd = cutoff.day < dim
    per = pd.Period(CUR, "M"); MESES = [str(per - 2), str(per - 1), CUR]; PREV = MESES[1]
    mlab = {m: MON[lang][int(m[5:]) - 1] for m in [str(per - i) for i in range(12)]}
    cur_lab = mlab[CUR] + (T(lang, " MTD", " parcial") if mtd else "")
    R = R.copy(); I = I.copy()
    R["m"] = R.data_recebimento.dt.to_period("M").astype(str); I["m"] = I.data_abertura.dt.to_period("M").astype(str)
    I["c24"] = (I.contencao_horas <= 24) | (I.contencao_horas.isna() & ((c_end - I.data_abertura) <= pd.Timedelta(hours=24)) & False)
    I["dias"] = (I.data_encerramento_8d - I.data_abertura).dt.days
    I["mc"] = I.data_encerramento_8d.dt.to_period("M").astype(str)
    A = A.copy(); A["m"] = A.data_auditoria.dt.to_period("M").astype(str)
    Pd = P.copy(); Pd["md"] = Pd.data_decisao.dt.to_period("M").astype(str)
    names = sup.set_index("id_fornecedor")

    def ppm(df): return df.qtd_rejeitada.sum() / max(df.qtd_recebida.sum(), 1) * 1e6

    def kp(m):
        r = R[R.m == m]; i = I[I.m == m]; cl = I[I.mc == m]; d = Pd[Pd.md == m]; a = A[A.m == m]
        return dict(ppm=ppm(r), ppm_br=ppm(r[r.origem == "BR"]), ppm_cn=ppm(r[r.origem == "CN"]), n=len(i),
                    esc=(i.deteccao != "Incoming inspection").mean() * 100 if len(i) else 0, c24=i.c24.mean() * 100 if len(i) else np.nan,
                    cl30=(cl.dias <= 30).mean() * 100 if len(cl) else np.nan, cld=cl.dias.mean() if len(cl) else np.nan,
                    ppap=len(d), fp=(d.decisao_1 == "Approved").mean() * 100 if len(d) else np.nan, aud=len(a), auds=a.nota_pct.mean() if len(a) else np.nan,
                    copq=i.copq_usd.sum() / 1e3, rec=i.recuperado_usd.sum() / max(i.copq_usd.sum(), 1) * 100)
    K = {m: kp(m) for m in MESES}; k, k0 = K[CUR], K[PREV]
    I3 = I[I.m.isin(MESES)]; R3 = R[R.m.isin(MESES)]
    c24_org = I3.groupby("origem").c24.mean() * 100
    open_ = I[I.status == "Open"]; overdue = open_[(c_end - open_.data_abertura).dt.days > 30]

    def status(v, t, hb):
        if v is None or (isinstance(v, float) and np.isnan(v)): return ""
        ok = v >= t if hb else v <= t
        return "good" if ok else ("warn" if abs(v - t) / t <= .05 else "bad")

    # ---------- localization wave ----------
    waves = sq.WAVES
    active = [w for w, (a, b, n) in waves.items() if pd.Timestamp(a) <= c_end <= pd.Timestamp(b) + pd.Timedelta(days=45)]
    w = active[-1] if active else max(waves)
    wa, wb, wn = waves[w]; PW = P[P.onda == w]
    st = pd.Series({
        "approved": (PW.aprovacao_final.notna()).sum(),
        "interim": ((PW.decisao_1 == "Interim approval") & PW.aprovacao_final.isna()).sum(),
        "rejected": ((PW.decisao_1 == "Rejected") & PW.aprovacao_final.isna()).sum(),
        "pending": (PW.data_submissao.notna() & PW.decisao_1.isna()).sum(),
        "overdue": (PW.data_submissao.isna() & (PW.data_prevista <= c_end)).sum(),
        "notdue": (PW.data_submissao.isna() & (PW.data_prevista > c_end)).sum()})
    st["notdue"] += wn - st.sum()    # parts planned beyond the four-month horizon of the view
    appr_pct = st.approved / wn * 100
    plan_pct = min(100, max(0, (c_end - pd.Timestamp(wa)).days / max((pd.Timestamp(wb) - pd.Timestamp(wa)).days, 1) * 100))
    weeks_left = max(0, (pd.Timestamp(wb) - c_end).days // 7)
    fpw = (PW.decisao_1.dropna() == "Approved").mean() * 100 if PW.decisao_1.notna().any() else np.nan
    late_sup = PW[PW.data_submissao.isna() & (PW.data_prevista <= c_end)].id_fornecedor.value_counts()
    deadline = T(lang, f"{wb.day} {MON['en'][wb.month-1]} {wb.year}", f"{wb.day:02d}/{wb.month:02d}/{wb.year}")
    ctx = public_context()

    # ---------- supplier watch list (rolling three months) ----------
    WL = []
    for sid, g in R3.groupby("id_fornecedor"):
        s = names.loc[sid]; ppm3 = ppm(g); op = (open_.id_fornecedor == sid).sum()
        la = A[A.id_fornecedor == sid].sort_values("data_auditoria").nota_pct
        aud = la.iloc[-1] if len(la) else np.nan
        risk = ppm3 / tg["ppm"] + .6 * op + (1.2 if (not np.isnan(aud) and aud < 80) else 0) + (.6 if s.iatf_16949 != "Sim" else 0)
        lvl = "CS2" if (ppm3 > 3 * tg["ppm"] and op >= 2) else "CS1" if (ppm3 > 2 * tg["ppm"] or (not np.isnan(aud) and aud < 70)) else T(lang, "Watch", "Atenção")
        WL.append(dict(id=sid, nome=s.fornecedor, origem=s.origem, comm=s.commodity, iatf=s.iatf_16949, ppm=ppm3, op=op, aud=aud, risk=risk, lvl=lvl))
    WL = pd.DataFrame(WL).sort_values("risk", ascending=False).head(5)

    # ---------- charts ----------
    m12 = [str(per - i) for i in range(11, -1, -1)]
    series = {o: [ppm(R[(R.m == m) & (R.origem == o)]) for m in m12] for o in ("BR", "CN")}
    tot = [ppm(R[R.m == m]) for m in m12]
    f, ax = plt.subplots(figsize=(3.3, 1.35)); f.subplots_adjust(left=.11, right=.99, top=.86, bottom=.15)
    x = np.arange(12)
    ax.plot(x, series["CN"], color=C["cat"][2], lw=1.1, label=O(ORG_S, "CN", lang))
    ax.plot(x, series["BR"], color=C["sage500"], lw=1.1, label=O(ORG_S, "BR", lang))
    ax.plot(x, tot, color=C["forest700"], lw=2, label=T(lang, "All suppliers", "Todos"))
    ax.axhline(tg["ppm"], color=C["bad"], lw=.9, ls=(0, (3, 2)), label=T(lang, "Target", "Meta"))
    rows_grid(ax); ax.set_xticks(x[::2], [mlab[m] for m in m12][::2], fontsize=6.4)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: num(v, 0, lang))); ax.tick_params(labelsize=6.4)
    ax.set_ylim(0, max(max(series["BR"]), max(series["CN"]), max(tot)) * 1.12)
    ax.legend(frameon=False, fontsize=6.2, ncol=4, loc="upper left", bbox_to_anchor=(-.02, 1.24), handlelength=1.4, columnspacing=1); c_ppm = svg(f)

    # Pareto by defect and origin (HTML bars)
    par = I3.groupby(["defeito", "origem"]).size().unstack(fill_value=0)
    par["t"] = par.sum(axis=1); par = par.sort_values("t", ascending=False).head(5); mx = par.t.max(); n3 = len(I3)
    oc = {"BR": C["sage500"], "CN": C["cat"][2], "OT": C["context"]}
    pareto = ""
    for dname, r in par.iterrows():
        segs = "".join(f'<span style="width:{r.get(o, 0) / mx * 100:.1f}%;background:{oc[o]}"></span>' for o in ("CN", "BR", "OT") if r.get(o, 0))
        pareto += f'<div class="pr"><span class="pn">{DEF(dname, lang)}</span><div class="hb2">{segs}</div><b>{int(r.t)} · {pct(r.t / n3 * 100, 0, lang)}</b></div>'
    leg = "".join(f'<span class="lk"><i style="background:{oc[o]}"></i>{O(ORG_S, o, lang)}</span>' for o in ("CN", "BR", "OT") if o in par.columns and par[o].sum())

    # PPAP wave bar
    SC = [("approved", C["good"], T(lang, "Approved", "Aprovado")), ("interim", C["signal"], T(lang, "Interim", "Provisório")),
          ("rejected", C["bad"], T(lang, "Rejected, resubmitting", "Reprovado, em revisão")), ("pending", C["sage500"], T(lang, "Under review", "Em análise")),
          ("overdue", "#5E2A20", T(lang, "Overdue, not submitted", "Atrasado, não submetido")), ("notdue", C["context"], T(lang, "Not yet due", "Ainda no prazo"))]
    ppap_bar = "".join(f'<span style="width:{st[kk] / wn * 100:.2f}%;background:{cc}"></span>' for kk, cc, _ in SC if st[kk])
    ppap_leg = "".join(f'<div class="lg"><i style="background:{cc}"></i>{lb}<b>{int(st[kk])}</b></div>' for kk, cc, lb in SC)

    # ---------- scorecard ----------
    def fmt(v, kind):
        if v is None or (isinstance(v, float) and np.isnan(v)): return "–"
        return {"k": num(v, 1, lang), "p": pct(v, 0, lang), "d": num(v, 1, lang), "i": num(v, 0, lang)}[kind]
    rows = [(T(lang, "Incoming quality", "Qualidade de recebimento"), None),
            (T(lang, "Incoming PPM, all suppliers", "PPM de recebimento, todos"), "ppm", "i", tg["ppm"], False),
            (T(lang, "PPM, local suppliers", "PPM, fornecedores locais"), "ppm_br", "i", None, None),
            (T(lang, "PPM, China imports", "PPM, importados da China"), "ppm_cn", "i", None, None),
            (T(lang, "Quality issues opened", "Problemas de qualidade abertos"), "n", "i", None, None),
            (T(lang, "Found on line or in field", "Detectados na linha ou em campo"), "esc", "p", None, None),
            (T(lang, "Problem solving", "Solução de problemas"), None),
            (T(lang, "Containment within 24 h", "Contenção em até 24 h"), "c24", "p", tg["containment_24h"], True),
            (T(lang, "8D closed within 30 days", "8D encerrado em até 30 dias"), "cl30", "p", tg["closure_30d"], True),
            (T(lang, "Supplier development", "Desenvolvimento de fornecedores"), None),
            (T(lang, "PPAP approved first time", "PPAP aprovado de primeira"), "fp", "p", tg["ppap_first_pass"], True),
            (T(lang, "Process audit score (avg)", "Nota de auditoria de processo"), "auds", "p", tg["audit_score"], True),
            (T(lang, "Cost of poor quality, USD k", "Custo da não qualidade, US$ mil"), "copq", "k", None, None),
            ]
    tb = ""
    for r in rows:
        if r[1] is None: tb += f'<tr class="grp"><td colspan="6">{r[0]}</td></tr>'; continue
        name, key, kind, t, hb = r
        sv = status(k[key], t, hb) if t is not None else ""
        dot = f'<span class="dot {sv}"></span>' if sv else ""
        tb += f'<tr><td>{name}</td>' + "".join(f"<td>{fmt(K[m][key], kind)}</td>" for m in MESES) + f'<td class="tg">{fmt(t, kind) if t is not None else "–"}</td><td>{dot}</td></tr>'

    wl = ""
    for _, s in WL.iterrows():
        cls = "bad" if s.lvl == "CS2" else "warn" if s.lvl == "CS1" else ""
        aud = pct(s.aud, 0, lang) if not np.isnan(s.aud) else "–"
        wl += (f'<tr><td>{s.nome}<div class="sub">{COMM(s.comm, lang)} · {O(ORG_S, s.origem, lang)}{"" if s.iatf == "Sim" else " · " + T(lang, "no IATF", "sem IATF")}</div></td>'
               f'<td class="{"bad" if s.ppm > 2 * tg["ppm"] else ""}">{num(s.ppm, 0, lang)}</td><td>{int(s.op)}</td>'
               f'<td class="{"bad" if (not np.isnan(s.aud) and s.aud < 80) else ""}">{aud}</td><td class="{cls}"><b>{s.lvl}</b></td></tr>')

    # ---------- data-driven text ----------
    drv = max(("BR", "CN"), key=lambda o: k[f"ppm_{o.lower()}"] - k0[f"ppm_{o.lower()}"])
    above = k["ppm"] > tg["ppm"]; back = above and k0["ppm"] <= tg["ppm"]
    behind = appr_pct + 10 < plan_pct
    launch_br = R3[(R3.origem == "BR")].id_fornecedor.map(names.onda_nacionalizacao).eq(w).any()
    drv_txt = {("BR", "en"): "Local launch suppliers" if launch_br else "Local suppliers", ("BR", "pt"): "Fornecedores locais em lançamento" if launch_br else "Fornecedores locais",
               ("CN", "en"): "Parts imported from China", ("CN", "pt"): "Peças importadas da China"}[(drv, lang)]
    if above:
        p1 = T(lang, f"{drv_txt} pushed incoming PPM {'back ' if back else ''}above target", f"{drv_txt} levaram o PPM {'de volta ' if back else ''}para cima da meta")
    else:
        p1 = T(lang, "Incoming PPM is on target", "PPM de recebimento na meta")
    past = c_end > pd.Timestamp(wb)
    if behind and past:
        p2 = T(lang, f"wave {w} localization missed its {deadline} deadline with {pct(appr_pct, 0, lang)} of parts approved",
               f"a onda {w} passou do prazo de {deadline} com {pct(appr_pct, 0, lang)} das peças aprovadas")
        headline = p1 + T(lang, ", and ", ", e ") + p2
    elif behind:
        p2 = T(lang, f"wave {w} localization has only {pct(appr_pct, 0, lang)} of parts approved with {weeks_left} weeks to go",
               f"a onda {w} tem só {pct(appr_pct, 0, lang)} das peças aprovadas a {weeks_left} semanas do prazo")
        headline = p1 + T(lang, ", and ", ", e ") + p2
    else:
        headline = p1 + T(lang, f", with wave {w} localization on plan ({pct(appr_pct, 0, lang)} approved)", f", com a onda {w} de nacionalização no plano ({pct(appr_pct, 0, lang)} aprovada)")

    H = []
    H.append(("bad" if above else "good", T(lang,
        f"<b>Incoming PPM {'above' if above else 'on'} target:</b> {num(k['ppm'], 0, lang)} against {num(tg['ppm'], 0, lang)} ({mlab[PREV]} {num(k0['ppm'], 0, lang)}). Local suppliers at {num(k['ppm_br'], 0, lang)}, China imports at {num(k['ppm_cn'], 0, lang)}.",
        f"<b>PPM {'acima' if above else 'dentro'} da meta:</b> {num(k['ppm'], 0, lang)} para meta de {num(tg['ppm'], 0, lang)} ({mlab[PREV]}: {num(k0['ppm'], 0, lang)}). Locais em {num(k['ppm_br'], 0, lang)}, importados da China em {num(k['ppm_cn'], 0, lang)}.")))
    gap = c24_org.get("BR", np.nan) - c24_org.get("CN", np.nan)
    if not np.isnan(gap) and gap > 10:
        H.append(("bad", T(lang,
            f"<b>Containment gap:</b> over {mlab[MESES[0]]}–{mlab[CUR]}, {pct(c24_org['CN'], 0, lang)} of issues with China-based suppliers were contained within 24 h, against {pct(c24_org['BR'], 0, lang)} for local suppliers. Time zone and language cost the first day.",
            f"<b>Contenção mais lenta na China:</b> em {mlab[MESES[0]]}–{mlab[CUR]}, {pct(c24_org['CN'], 0, lang)} dos problemas com fornecedores chineses foram contidos em até 24 h, contra {pct(c24_org['BR'], 0, lang)} dos locais. Fuso e idioma atrasam o primeiro dia.")))
    H.append((status(k["cl30"], tg["closure_30d"], True) or "good", T(lang,
        f"<b>8D closure:</b> {pct(k['cl30'], 0, lang)} closed within 30 days (target {pct(tg['closure_30d'], 0, lang)}); {len(open_)} issues open, {len(overdue)} of them past 30 days.",
        f"<b>Encerramento de 8D:</b> {pct(k['cl30'], 0, lang)} encerrados em até 30 dias (meta {pct(tg['closure_30d'], 0, lang)}); {len(open_)} problemas abertos, {len(overdue)} com mais de 30 dias.")))
    if False: H.append(("bad" if behind else "good", T(lang,
        f"<b>Wave {w} PPAP:</b> {int(st.approved)} of {wn} parts approved ({pct(appr_pct, 0, lang)} against {pct(plan_pct, 0, lang)} of the timeline elapsed), first-time approval {pct(fpw, 0, lang)}, {int(st.overdue)} parts overdue and not submitted.",
        f"<b>PPAP da onda {w}:</b> {int(st.approved)} de {wn} peças aprovadas ({pct(appr_pct, 0, lang)} para {pct(plan_pct, 0, lang)} do cronograma decorrido), aprovação de primeira em {pct(fpw, 0, lang)}, {int(st.overdue)} peças atrasadas sem submissão.")))

    A_ = []
    if st.overdue:
        top_late = T(lang, " and ", " e ").join(names.loc[i, "fornecedor"] for i in late_sup.index[:2])
        A_.append(T(lang, f"Weekly PPAP review for the {int(st.overdue)} overdue wave {w} parts, starting with {top_late}; escalate any part that cannot be approved before {deadline}.",
                    f"Revisão semanal das {int(st.overdue)} peças atrasadas da onda {w}, começando por {top_late}; escalar o que não for aprovado até {deadline}."))
    cs = WL[WL.lvl.isin(["CS2", "CS1"])]
    if len(cs):
        s0 = cs.iloc[0]
        A_.append(T(lang, f"Controlled shipping level {s0.lvl[-1]} at {s0.nome} ({num(s0.ppm, 0, lang)} PPM over three months) until two clean months, with a third-party sort at receiving.",
                    f"Controlled shipping nível {s0.lvl[-1]} em {s0.nome} ({num(s0.ppm, 0, lang)} PPM em três meses) até dois meses sem defeito, com seleção por terceiro no recebimento."))
    if not np.isnan(gap) and gap > 10:
        A_.append(T(lang, "24-hour containment protocol with China-based suppliers: bilingual 8D template, a named contact in each time zone and a local sorting partner in Brazil.",
                    "Protocolo de contenção em 24 h com fornecedores chineses: modelo de 8D bilíngue, um contato nomeado em cada fuso e um parceiro local de seleção no Brasil."))
    unrec = I3.copq_usd.sum() - I3.recuperado_usd.sum()
    if len(A_) < 4 and unrec > 0:
        A_.append(T(lang, f"Issue debit notes for the {usd(lang)} {num(unrec / 1e3, 0, lang)}k of cost of poor quality not yet recovered over {mlab[MESES[0]]}–{mlab[CUR]}.",
                    f"Emitir notas de débito para os {usd(lang)} {num(unrec / 1e3, 0, lang)} mil de custo da não qualidade ainda não recuperados em {mlab[MESES[0]]}–{mlab[CUR]}."))
    A_ = A_[:4]
    hl = "".join(f'<li><i class="{c}"></i><span>{t}</span></li>' for c, t in H)
    ac = "".join(f'<li><i class="n">{i + 1}</i><span>{t}</span></li>' for i, t in enumerate(A_))
    next_m = MONTHS[lang][cutoff.month % 12]
    ctx_txt = ""
    if ctx:
        ctx_txt = T(lang, f"Public context: {pct(ctx['china'], 0, lang)} of Brazil's electrified car imports in Jan–{MON['en'][ctx['month']-1]} {ctx['year']} came from China (Comex Stat), and the import duty on assembly kits reaches 35% in January 2027.",
                    f"Contexto público: {pct(ctx['china'], 0, lang)} dos carros eletrificados importados pelo Brasil em jan–{MON['pt'][ctx['month']-1]} de {ctx['year']} vieram da China (Comex Stat), e o imposto sobre kits de montagem chega a 35% em janeiro de 2027.")

    EXTRA = """
table.t.sc2 td, table.t.sc2 th { padding: .5mm 1.2mm; }
table.t tr.grp td { font-family:'IBM Plex Mono',monospace; font-size:6pt; letter-spacing:.08em; text-transform:uppercase; color:#06402B; background:#E7E2D9; padding:.6mm 1.2mm; }
table.t td.tg { color:#4F615A; }
table.t td .sub { font-size:6.2pt; color:#4F615A; margin-top:.2mm; }
.dot { width:2.2mm; height:2.2mm; border-radius:50%; display:inline-block; } .dot.good{background:#235F46} .dot.warn{background:#795300} .dot.bad{background:#9B3434}
.hb2 { background:#E7E2D9; height:2mm; border-radius:.4mm; overflow:hidden; display:flex; } .hb2 span { display:block; height:100%; }
.stk { display:flex; height:4mm; border-radius:.5mm; overflow:hidden; margin:1.2mm 0 1.8mm; } .stk span { display:block; height:100%; }
.lgs { display:grid; grid-template-columns:1fr 1fr; gap:.8mm 3mm; font-size:6.8pt; color:#4F615A; }
.lg { display:flex; align-items:center; gap:1.4mm; } .lg i { width:2mm; height:2mm; display:inline-block; flex:none; } .lg b { margin-left:auto; font-weight:500; color:#2B2F2E; }
.lk { display:inline-flex; align-items:center; gap:1.2mm; margin-right:3mm; font-size:6.6pt; color:#4F615A; } .lk i { width:2mm; height:2mm; display:inline-block; }
.pb { margin-bottom:.9mm; } .pr { display:grid; grid-template-columns: 44% 1fr 13mm; align-items:center; gap:2mm; font-size:7pt; margin-bottom:1.1mm; } .pr b { font-weight:500; text-align:right; } .pr .hb2 { height:2.4mm; } .pl { display:flex; justify-content:space-between; font-size:7.1pt; margin-bottom:.5mm; } .pl b { font-weight:500; }
ul.pc { list-style:none; margin:0; padding:0; font-size:7.5pt; line-height:1.4; } ul.pc li { display:flex; gap:2mm; margin-bottom:1.2mm; }
ul.pc i { flex:none; width:1.6mm; height:1.6mm; margin-top:1.3mm; } ul.pc i.good{background:#235F46} ul.pc i.bad{background:#9B3434} ul.pc i.warn{background:#795300}
ul.pc i.n { width:4mm; height:4mm; margin-top:.2mm; background:#06402B; color:#FBF9F4; font-style:normal; font-family:'IBM Plex Mono',monospace; font-size:6.5pt; display:flex; align-items:center; justify-content:center; border-radius:.5mm; }
.ctx { font-size:6.8pt; color:#4F615A; line-height:1.4; border-left:2px solid #C97A3A; padding-left:2mm; margin-top:1.8mm; }
.mini { width:100%; border-collapse:collapse; font-size:7.2pt; margin-top:1mm; } .mini td { padding:.6mm 0; border-bottom:1px solid #E7E2D9; } .mini td:last-child { text-align:right; font-weight:500; }
.syn { display:inline-block; font-family:'IBM Plex Mono',monospace; font-weight:500; font-size:6pt; letter-spacing:.08em; text-transform:uppercase; color:#795300; background:transparent; border:1px solid #795300; padding:.4mm 1.4mm; border-radius:1mm; margin-top:2.5mm; }
.page { gap: 2.2mm; padding-top: 7.5mm; padding-bottom: 6mm; } .kpi { padding: 2.3mm 3mm; } .kpi .v { font-size: 15pt; } .card { padding: 2.2mm 3mm; } .sec { margin-bottom: 1.2mm; } .hdr { padding: 4mm 6mm 4.5mm; } .hdr h1 { font-size: 14.5pt; }
"""
    month_title = T(lang, f"{MONTHS['en'][cutoff.month-1]} {cutoff.year}", f"{MONTHS['pt'][cutoff.month-1].capitalize()} de {cutoff.year}")
    span = T(lang, f"1–{cutoff.day} {MON['en'][cutoff.month-1]}" if mtd else "Full month", f"1 a {cutoff.day}/{cutoff.month:02d}" if mtd else "Mês fechado")
    mini = "".join(f'<tr><td>{O(ORG, o, lang)}</td><td class="{"bad" if c24_org.get(o, 100) < tg["containment_24h"] - 5 else ""}">{pct(c24_org[o], 0, lang)}</td></tr>' for o in ("BR", "CN") if o in c24_org)
    body = f"""<style>{EXTRA}</style>
<div class="hdr"><div class="grid"></div><div class="in"><div>
<div class="eyebrow"><span class="node"></span>{T(lang, 'Monthly supplier quality report · EV assembly plant · Brazil', 'Qualidade de fornecedores · Montadora de veículos elétricos · Brasil')}</div>
<h1>{headline}</h1>
<span class="syn">{T(lang, 'SYNTHETIC DATA · FICTITIOUS PLANT WITH A CHINESE PARENT', 'DADOS SINTÉTICOS · MONTADORA FICTÍCIA DE CONTROLE CHINÊS')}</span></div>
<div class="side"><div class="sm">{T(lang, 'Reporting month', 'Mês de referência')}</div><div class="big">{month_title}</div><div class="sm" style="margin-top:2mm">{T(lang, 'Period', 'Período')}</div><div class="big" style="font-size:9pt">{span} · {T(lang, 'edition', 'edição')} {edition_label(edition, lang)}</div></div></div></div>
<div class="kpis" style="grid-template-columns:repeat(5,1fr)">
<div class="kpi inv"><div class="lb">{T(lang, 'Incoming PPM', 'PPM de recebimento')}</div><div class="v">{num(k['ppm'], 0, lang)}</div><div class="d">{T(lang, 'Target', 'Meta')} {num(tg['ppm'], 0, lang)} · {mlab[PREV]} {num(k0['ppm'], 0, lang)}</div></div>
<div class="kpi"><div class="lb">{T(lang, 'Containment ≤ 24 h', 'Contenção ≤ 24 h')}</div><div class="v {status(k['c24'], tg['containment_24h'], True)}">{pct(k['c24'], 0, lang)}</div><div class="d">{T(lang, 'Target', 'Meta')} {pct(tg['containment_24h'], 0, lang)} · {k['n']} {T(lang, 'issues opened', 'problemas abertos')}</div></div>
<div class="kpi"><div class="lb">{T(lang, '8D closed ≤ 30 days', '8D em até 30 dias')}</div><div class="v {status(k['cl30'], tg['closure_30d'], True)}">{pct(k['cl30'], 0, lang)}</div><div class="d">{T(lang, 'Target', 'Meta')} {pct(tg['closure_30d'], 0, lang)} · {len(open_)} {T(lang, 'open', 'abertos')}, {len(overdue)} &gt; 30 {T(lang, 'days', 'dias')}</div></div>
<div class="kpi"><div class="lb">{T(lang, f'Wave {w} PPAP approved', f'PPAP onda {w} aprovado')}</div><div class="v {'bad' if behind else 'good'}">{pct(appr_pct, 0, lang)}</div><div class="d">{int(st.approved)} {T(lang, 'of', 'de')} {wn} {T(lang, 'parts', 'peças')} · {T(lang, 'deadline', 'prazo')} {deadline}</div></div>
<div class="kpi"><div class="lb">{T(lang, 'Cost of poor quality', 'Custo da não qualidade')}</div><div class="v">{num(k['copq'], 0, lang)}{T(lang, 'k', ' mil')}</div><div class="d">{usd(lang)} · {pct(k['rec'], 0, lang)} {T(lang, 'recovered', 'recuperado')}</div></div>
</div>
<div style="display:grid;grid-template-columns:1.12fr 1fr;gap:4mm">
<div><div class="sec"><span class="no">01</span><h2>Scorecard</h2><span class="r">{T(lang, 'Status vs target', 'Status vs meta')}</span></div>
<table class="t sc2"><tr><th>{T(lang, 'Indicator', 'Indicador')}</th><th>{mlab[MESES[0]]}</th><th>{mlab[MESES[1]]}</th><th>{cur_lab}</th><th>{T(lang, 'Target', 'Meta')}</th><th></th></tr>{tb}</table></div>
<div><div class="sec"><span class="no">02</span><h2>{T(lang, 'Incoming quality by origin', 'Qualidade de recebimento por origem')}</h2><span class="r">12 {T(lang, 'months', 'meses')}</span></div>
<div class="card"><p class="ct">{T(lang, 'Incoming PPM by month', 'PPM de recebimento por mês')}</p>{c_ppm}</div>
<div class="card" style="margin-top:2mm"><p class="ct">{T(lang, 'Highlights', 'Destaques')}</p><ul class="pc">{hl}</ul></div></div>
</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:4mm">
<div><div class="sec"><span class="no">03</span><h2>{T(lang, 'Defect Pareto', 'Pareto de defeitos')}</h2><span class="r">{mlab[MESES[0]]}–{mlab[CUR]} · {n3} {T(lang, 'issues', 'problemas')}</span></div>
<div class="card">{pareto}<div style="margin-top:1mm">{leg}</div></div></div>
<div><div class="sec"><span class="no">04</span><h2>{T(lang, f'Localization wave {w}: PPAP status', f'Nacionalização, onda {w}: status do PPAP')}</h2><span class="r">{wn} {T(lang, 'parts', 'peças')}</span></div>
<div class="card"><p class="ct">{T(lang, f'Deadline {deadline} · ' + ('passed' if past else f'{weeks_left} weeks left'), f'Prazo {deadline} · ' + ('vencido' if past else f'faltam {weeks_left} semanas'))}</p><div class="stk">{ppap_bar}</div><div class="lgs">{ppap_leg}</div>
<div class="ctx">{ctx_txt}</div></div></div>
</div>
<div style="display:grid;grid-template-columns:1.12fr 1fr;gap:4mm">
<div><div class="sec"><span class="no">05</span><h2>{T(lang, 'Supplier watch list', 'Fornecedores em atenção')}</h2><span class="r">{mlab[MESES[0]]}–{mlab[CUR]}</span></div>
<table class="t"><tr><th>{T(lang, 'Supplier', 'Fornecedor')}</th><th>PPM</th><th>{T(lang, 'Open 8D', '8D')}</th><th>{T(lang, 'Audit', 'Auditoria')}</th><th>{T(lang, 'Level', 'Nível')}</th></tr>{wl}</table></div>
<div><div class="sec"><span class="no">06</span><h2>{T(lang, 'Actions for ', 'Ações para ')}{next_m}</h2></div>
<div class="card"><ul class="pc">{ac}</ul></div></div>
</div>
{footer(with_note(T(lang, "Synthetic data for a fictitious EV assembler in Brazil with a Chinese parent company; plant, suppliers and records are invented and describe no real company. Public context: MDIC Comex Stat and the Gecex import duty schedule. PPAP per AIAG; audit score on a VDA 6.3 style scale (A ≥ 90%, B 80 to 89%, C below 80%). Controlled shipping: CS1 = supplier sorts, CS2 = third-party sort. Status: green on target, amber within 5%, red beyond 5%.",
          "Dados sintéticos de uma montadora fictícia de veículos elétricos no Brasil com controle chinês; planta, fornecedores e registros são inventados. Contexto público: MDIC Comex Stat e cronograma de imposto de importação do Gecex. PPAP conforme AIAG; auditoria em escala estilo VDA 6.3 (A ≥ 90%, B 80 a 89%, C < 80%). Controlled shipping: CS1 = seleção pelo fornecedor, CS2 = seleção por terceiro. Status: verde na meta, âmbar até 5% fora, vermelho acima de 5%."), coverage_note("sqe", edition, lang)))}
"""
    name = T(lang, "Monthly_Supplier_Quality_Report", "Relatorio_Mensal_Qualidade_Fornecedores") + f"_{CUR}"
    html = os.path.join(outdir, name + ".html")
    h, lvl = render_fit(body, T(lang, "Monthly Supplier Quality Report", "Relatório Mensal de Qualidade de Fornecedores") + f" · {month_title}", lang,
                        html, os.path.join(outdir, name + ".pdf"), os.path.join(outdir, name + ".png") if png else None)
    return dict(name=name, height=h, fit_level=lvl, headline=headline, ppm=round(k["ppm"]), wave=w, ppap_approved_pct=round(appr_pct, 1))
