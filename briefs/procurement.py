"""Monthly Procurement Performance Report for a fictitious aerospace buyer (synthetic data).
Every number and every sentence of the highlights, headline and actions comes from the data."""
import os, sys, calendar
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from .style import C, svg, rows_grid, footer, render_fit
from .common import ROOT, SYN, MON, MONTHS, T, num, pct, pp, usd, edition_label, bls_notice

sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import synthetic  # noqa: E402

CAT = {"Propulsão": ("Propulsion", "Propulsão"), "Aviônica": ("Avionics", "Aviônica"), "Estruturas e usinados": ("Structures", "Estruturas"),
       "Trem de pouso e hidráulica": ("Landing gear", "Trem de pouso"), "Elétrica e chicotes": ("Electrical", "Elétrica"), "Matéria-prima metálica": ("Raw metals", "Matéria-prima")}
SEG = {"Estratégico": ("Strategic", "Estratégico"), "Preferencial": ("Preferred", "Preferencial"), "Aprovado": ("Approved", "Aprovado"), "Em desenvolvimento": ("Developing", "Em desenv.")}
NC = {"Certificação do fabricante ausente": ("Missing manufacturer cert.", "Certificado do fabricante ausente"),
      "Reprovação na inspeção de recebimento": ("Failed receiving inspection", "Reprovação na inspeção"),
      "Revisão de peça superada": ("Superseded part revision", "Revisão de peça superada"), "Dano no transporte": ("Transport damage", "Dano no transporte"),
      "Divergência de documentação (CoC/FAI)": ("Documentation mismatch (CoC/FAI)", "Documentação divergente (CoC/FAI)")}
L = lambda d, k, lang: d.get(k, (k, k))[0 if lang == "en" else 1]


def load(cutoff):
    P, Q, R = synthetic.view(cutoff)
    F = pd.read_csv(os.path.join(SYN, "fornecedores.csv")); M = pd.read_csv(os.path.join(SYN, "materiais.csv"))
    T_ = pd.read_csv(os.path.join(SYN, "metas_mensais.csv")).set_index("mes")
    if cutoff.strftime("%Y-%m") not in T_.index: T_.loc[cutoff.strftime("%Y-%m")] = T_.iloc[-1]
    for c in ("quantidade",): P[c] = P[c].astype(int)
    for c in ("valor_total_usd",): P[c] = P[c].astype(float)
    for c in ("data_pedido", "data_prometida", "data_recebimento"): P[c] = pd.to_datetime(P[c].replace("", None))
    for c in ("qtd_rejeitada", "qtd_recebida"): Q[c] = Q[c].astype(int)
    Q["data_abertura"] = pd.to_datetime(Q.data_abertura)
    R["impacto_usd"] = R.impacto_usd.astype(float); R["novos_fabricantes_incluidos"] = R.novos_fabricantes_incluidos.astype(int)
    for c in ("data_abertura", "data_fechamento"): R[c] = pd.to_datetime(R[c])
    P["m"] = P.data_pedido.dt.to_period("M").astype(str); P["mr"] = P.data_recebimento.dt.to_period("M").astype(str)
    R["m"] = R.data_fechamento.dt.to_period("M").astype(str); Q["m"] = Q.data_abertura.dt.to_period("M").astype(str)
    P = P.merge(M[["part_number", "fonte_unica"]], on="part_number").merge(F[["id_fornecedor", "fornecedor", "segmentacao"]], on="id_fornecedor")
    return P, Q, R, T_


def build(edition, cutoff, lang, outdir, png=True):
    P, Q, R, TG = load(cutoff)
    CUR = cutoff.strftime("%Y-%m"); dim = calendar.monthrange(cutoff.year, cutoff.month)[1]; mtd = cutoff.day < dim; frac = cutoff.day / dim
    per = pd.Period(CUR, "M"); MESES = [str(per - 2), str(per - 1), CUR]; PREV = MESES[1]; m4 = str(per - 3)

    def kp(m):
        p = P[P.m == m]; r = P[P.mr == m]; rr = R[R.m == m]; q = Q[Q.m == m]
        return dict(spend=p.valor_total_usd.sum() / 1e6, lines=len(p), ss=p[p.fonte_unica == "Sim"].valor_total_usd.sum() / max(p.valor_total_usd.sum(), 1) * 100,
                    sav=rr[rr.tipo_resultado == "Savings"].impacto_usd.sum() / 1e3, ca=rr[rr.tipo_resultado == "Cost avoidance"].impacto_usd.sum() / 1e3,
                    inc=rr[rr.tipo_resultado == "Aumento"].impacto_usd.sum() / 1e3, rfqs=len(rr), cyc=(rr.data_fechamento - rr.data_abertura).dt.days.mean(),
                    otd=(r.data_recebimento <= r.data_prometida).mean() * 100, ppm=q.qtd_rejeitada.sum() / max(r.quantidade.sum(), 1) * 1e6, ncs=len(q))
    K = {m: kp(m) for m in MESES + [m4]}; k, kp_ = K[CUR], K[PREV]; tg = TG.loc[CUR]
    tgt = lambda m: TG.loc[m, "meta_savings_usd"] * (frac if (m == CUR and mtd) else 1)
    ms = [str(x) for x in pd.period_range(f"{cutoff.year}-01", CUR, freq="M")]
    ytd = R[(R.m >= ms[0]) & (R.m <= CUR)]
    sav_ytd = ytd[ytd.tipo_resultado == "Savings"].impacto_usd.sum() / 1e3
    val_ytd = ytd[(ytd.tipo_resultado == "Savings") & (ytd.validado_finance == "Sim")].impacto_usd.sum() / 1e3
    inc_ytd = ytd[ytd.tipo_resultado == "Aumento"].impacto_usd.sum() / 1e3
    tgt_ytd = sum(tgt(m) for m in ms) / 1e3
    mlab = {m: MON[lang][int(m[5:]) - 1] for m in MESES + [m4]}
    cur_lab = mlab[CUR] + (T(lang, " MTD", " parcial") if mtd else "")

    # suppliers, quality, backlog (rolling three months)
    q3 = P[P.m.isin(MESES)]; rq3 = P[P.mr.isin(MESES)]
    top = q3.groupby(["id_fornecedor", "fornecedor"]).valor_total_usd.sum().sort_values(ascending=False).head(6)
    SUP = []
    for (fid, nm), v in top.items():
        rr_ = rq3[rq3.id_fornecedor == fid]; otd = (rr_.data_recebimento <= rr_.data_prometida).mean() * 100 if len(rr_) else np.nan
        rej = Q[(Q.id_fornecedor == fid) & Q.m.isin(MESES)].qtd_rejeitada.sum(); ppm = rej / rr_.quantidade.sum() * 1e6 if len(rr_) else 0
        po = 50 if otd >= 95 else 40 if otd >= 90 else 30 if otd >= 85 else 20 if otd >= 80 else 10
        pq = 50 if ppm == 0 else 40 if ppm <= 2500 else 30 if ppm <= 7500 else 20 if ppm <= 15000 else 10
        SUP.append(dict(nome=nm, spend=v / 1e6, otd=otd, ppm=ppm, score=po + pq))
    SUP = pd.DataFrame(SUP)
    NCs = Q[Q.m.isin(MESES)].motivo.value_counts(); n_open = int((Q.status == "Aberta").sum())
    late = P[P.data_recebimento.isna() & (P.data_prometida < pd.Timestamp(cutoff))]
    bl_top = late.groupby("fornecedor").valor_total_usd.sum().sort_values(ascending=False).head(2) / 1e6

    def status(v, t, hb):
        ok = v >= t if hb else v <= t
        return "good" if ok else ("warn" if abs(v - t) / t <= .05 else "bad")

    # ---------- charts ----------
    real = np.cumsum([R[(R.m == m) & (R.tipo_resultado == "Savings")].impacto_usd.sum() / 1e3 for m in ms])
    meta = np.cumsum([tgt(m) / 1e3 for m in ms])
    f, ax = plt.subplots(figsize=(3.3, 1.12)); f.subplots_adjust(left=.1, right=.99, top=.95, bottom=.15)
    lab = [MON[lang][int(m[5:]) - 1] for m in ms]
    ax.bar(lab, real, color=[C["context"]] * (len(ms) - 1) + [C["forest700"]], width=.62, label=T(lang, "Actual", "Realizado"))
    ax.plot(lab, meta, color=C["ink"], lw=1.1, ls=(0, (3, 2)), label=T(lang, "Target", "Meta")); rows_grid(ax)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: num(v, 0, lang)))
    ax.legend(frameon=False, fontsize=6.5, loc="upper left", handlelength=1.6); ax.tick_params(labelsize=6.5); c_sav = svg(f)

    def stack(series, names):
        s = series.sort_values(ascending=False); s = s / s.sum() * 100
        if len(s) > 4: s = pd.concat([s.iloc[:3], pd.Series({"_other": s.iloc[3:].sum()})])
        cols = [C["forest700"], C["sage500"], C["cat"][2], C["context"]][:len(s)]
        nm = lambda n: T(lang, "Other", "Outros") if n == "_other" else (L(names, n, lang) if names else n)
        bar = "".join(f'<span style="width:{v:.2f}%;background:{c}"></span>' for v, c in zip(s.values, cols))
        leg = "".join(f'<div class="lg"><i style="background:{c}"></i>{nm(n)}<b>{pct(v, 0, lang)}</b></div>' for (n, v), c in zip(s.items(), cols))
        return f'<div class="stk">{bar}</div><div class="lgs">{leg}</div>'
    pc = P[P.m == CUR]
    s1 = stack(pc.groupby("categoria").valor_total_usd.sum(), CAT); s2 = stack(pc.groupby("moeda").valor_total_usd.sum(), None)
    s3 = stack(pc.groupby("segmentacao").valor_total_usd.sum(), SEG)

    # ---------- scorecard ----------
    def fmt(v, kind):
        return {"m": num(v, 2, lang), "k": num(v, 1, lang), "p": pct(v, 1, lang), "d": num(v, 1, lang), "i": num(v, 0, lang)}[kind]
    rows = [(T(lang, "Spend &amp; sourcing", "Gasto e sourcing"), None),
            (T(lang, "Spend (USD million)", "Gasto (US$ milhões)"), "spend", "m", None, None), (T(lang, "PO lines issued", "Linhas de pedido emitidas"), "lines", "i", None, None),
            (T(lang, "Spend in single-source items", "Gasto em itens de fonte única"), "ss", "p", None, None), (T(lang, "RFQs closed", "RFQs concluídas"), "rfqs", "i", None, None),
            (T(lang, "Avg RFQ cycle (days)", "Ciclo médio de RFQ (dias)"), "cyc", "d", tg.meta_lead_time_rfq_dias, False),
            (T(lang, "Negotiation (USD thousand)", "Negociação (US$ mil)"), None),
            ("Savings", "sav", "k", tgt(CUR) / 1e3, True), ("Cost avoidance", "ca", "k", None, None),
            (T(lang, "Price increases accepted", "Aumentos aceitos"), "inc", "k", None, None),
            (T(lang, "Delivery &amp; quality", "Entrega e qualidade"), None),
            (T(lang, "On-time delivery", "Entrega no prazo (OTD)"), "otd", "p", tg.meta_otd_pct, True), (T(lang, "Incoming PPM", "PPM de recebimento"), "ppm", "i", tg.meta_ppm, False),
            (T(lang, "Non-conformances opened", "Não conformidades abertas"), "ncs", "i", None, None)]
    tb = ""
    for r in rows:
        if r[1] is None: tb += f'<tr class="grp"><td colspan="6">{r[0]}</td></tr>'; continue
        name, key, kind, t, hb = r
        st = f'<span class="dot {status(k[key], t, hb)}"></span>' if t is not None else ""
        tb += f'<tr><td>{name}</td>' + "".join(f"<td>{fmt(K[m][key], kind)}</td>" for m in MESES) + f'<td class="tg">{fmt(t, kind) if t is not None else "–"}</td><td>{st}</td></tr>'
    sup = ""; mx = SUP.spend.max()
    for _, s in SUP.iterrows():
        dots = int(round(s.score / 20)); cls = "good" if s.score >= 80 else ("warn" if s.score >= 60 else "bad")
        sup += (f'<tr><td>{s.nome}</td><td><div class="hb"><span style="width:{s.spend/mx*100:.0f}%"></span></div></td><td>{num(s.spend, 2, lang)}</td>'
                f'<td class="{"bad" if s.otd < 85 else ""}">{pct(s.otd, 0, lang)}</td><td class="{"bad" if s.ppm > 15000 else ""}">{num(s.ppm, 0, lang)}</td>'
                f'<td class="sc {cls}">{"●" * dots}{"○" * (5 - dots)}</td></tr>')
    nct = NCs.sum()
    ncb = "".join(f'<div class="pb"><div class="pl"><span>{L(NC, n, lang)}</span><b>{v} · {pct(v / nct * 100, 0, lang)}</b></div><div class="hb"><span style="width:{v / NCs.max() * 100:.0f}%"></span></div></div>' for n, v in NCs.items())

    # ---------- data-driven text ----------
    otd_seq = [K[m]["otd"] for m in [m4] + MESES]
    declining = all(b < a for a, b in zip(otd_seq, otd_seq[1:]))
    low = SUP[SUP.otd < 85]; worst = SUP.sort_values("ppm", ascending=False).iloc[0]
    cyc = [K[m]["cyc"] for m in MESES]; sav_ok = sav_ytd >= tgt_ytd
    sav_mtd_p = k["sav"] / (tgt(CUR) / 1e3) * 100; ppm_t = tg.meta_ppm; otd_t = tg.meta_otd_pct; cyc_t = tg.meta_lead_time_rfq_dias
    issues = []
    H = []
    month_ok = sav_mtd_p >= 100; ytd_p = pct(sav_ytd / tgt_ytd * 100, 0, lang); mon_p = pct(sav_mtd_p, 0, lang)
    mname_en, mname_pt = MONTHS["en"][cutoff.month-1], MONTHS["pt"][cutoff.month-1]
    if sav_ok == month_ok:
        H.append(("good" if sav_ok else "bad",
                  T(lang, f"<b>Savings {'ahead of' if sav_ok else 'behind'} plan:</b> USD {num(k['sav'], 1, lang)}k in {mname_en} ({mon_p} of {'pro-rated ' if mtd else ''}target), {ytd_p} of target YTD.",
                    f"<b>Savings {'acima' if sav_ok else 'abaixo'} do plano:</b> US$ {num(k['sav'], 1, lang)} mil em {mname_pt} ({mon_p} da meta{' proporcional' if mtd else ''}), {ytd_p} da meta no ano.")))
    else:
        H.append(("warn",
                  T(lang, f"<b>Savings {'ahead of' if sav_ok else 'behind'} plan YTD</b> at {ytd_p} of target, although {mname_en} reached {mon_p} of its {'pro-rated ' if mtd else ''}monthly target (USD {num(k['sav'], 1, lang)}k).",
                    f"<b>Savings {'acima' if sav_ok else 'abaixo'} do plano no ano,</b> com {ytd_p} da meta, embora {mname_pt} tenha ficado em {mon_p} da meta{' proporcional' if mtd else ''} do mês (US$ {num(k['sav'], 1, lang)} mil).")))
    seq_txt = ", ".join(pct(x, 1, lang) for x in otd_seq)
    if declining:
        issues.append(T(lang, "delivery keeps slipping", "a entrega segue piorando"))
        H.append(("bad", T(lang, f"<b>Delivery keeps slipping:</b> OTD has declined every month since {MONTHS['en'][int(m4[5:])-1]} ({seq_txt}); {len(low)} of the top six suppliers are below 85% over {mlab[MESES[0]]}–{mlab[CUR]}.",
                           f"<b>Entrega piorando:</b> o OTD caiu todos os meses desde {MONTHS['pt'][int(m4[5:])-1]} ({seq_txt}); {len(low)} dos seis maiores fornecedores estão abaixo de 85% em {mlab[MESES[0]]}–{mlab[CUR]}.")))
    elif k["otd"] < otd_t:
        issues.append(T(lang, "delivery is below target", "a entrega está abaixo da meta"))
        H.append(("warn" if status(k["otd"], otd_t, True) == "warn" else "bad", T(lang, f"<b>Delivery below target:</b> OTD at {pct(k['otd'], 1, lang)} against {pct(otd_t, 0, lang)}; {len(low)} of the top six suppliers are below 85% over {mlab[MESES[0]]}–{mlab[CUR]}.",
                                                                                   f"<b>Entrega abaixo da meta:</b> OTD em {pct(k['otd'], 1, lang)} para meta de {pct(otd_t, 0, lang)}; {len(low)} dos seis maiores fornecedores estão abaixo de 85% em {mlab[MESES[0]]}–{mlab[CUR]}.")))
    else:
        H.append(("good", T(lang, f"<b>Delivery on target:</b> OTD at {pct(k['otd'], 1, lang)} against {pct(otd_t, 0, lang)}.", f"<b>Entrega na meta:</b> OTD em {pct(k['otd'], 1, lang)} para meta de {pct(otd_t, 0, lang)}.")))
    if k["ppm"] > ppm_t:
        back = kp_["ppm"] <= ppm_t
        issues.append(T(lang, "quality is back above target" if back else "quality is above target", "a qualidade voltou a passar da meta" if back else "a qualidade está acima da meta"))
        H.append(("bad", T(lang, f"<b>Quality {'reversed' if back else 'above target'}:</b> incoming PPM {'rose' if k['ppm'] > kp_['ppm'] else 'moved'} to {num(k['ppm'], 0, lang)} from {num(kp_['ppm'], 0, lang)} in {MONTHS['en'][int(PREV[5:])-1]}, above target; {worst.nome} runs at {num(worst.ppm, 0, lang)} PPM despite {pct(worst.otd, 0, lang)} OTD.",
                           f"<b>Qualidade {'piorou' if back else 'acima da meta'}:</b> o PPM de recebimento {'subiu' if k['ppm'] > kp_['ppm'] else 'foi'} para {num(k['ppm'], 0, lang)}, contra {num(kp_['ppm'], 0, lang)} em {MONTHS['pt'][int(PREV[5:])-1]}, acima da meta; {worst.nome} roda a {num(worst.ppm, 0, lang)} PPM mesmo com {pct(worst.otd, 0, lang)} de OTD.")))
    else:
        H.append(("good", T(lang, f"<b>Quality on target:</b> incoming PPM at {num(k['ppm'], 0, lang)} against {num(ppm_t, 0, lang)}.", f"<b>Qualidade na meta:</b> PPM de recebimento em {num(k['ppm'], 0, lang)} para meta de {num(ppm_t, 0, lang)}.")))
    if k["cyc"] > cyc_t:
        most = k["rfqs"] >= max(K[m]["rfqs"] for m in MESES)
        issues.append(T(lang, "RFQs are taking longer", "as RFQs estão mais lentas"))
        H.append(("warn", T(lang, f"<b>Sourcing slower:</b> RFQ cycle {'rose from ' + num(cyc[0], 1, lang) + ' to' if cyc[2] > cyc[0] else 'at'} {num(cyc[2], 1, lang)} days (target {num(cyc_t, 0, lang)}) with {k['rfqs']} RFQs closed{', the most in three months' if most else ''}.",
                            f"<b>Sourcing mais lento:</b> ciclo de RFQ {'subiu de ' + num(cyc[0], 1, lang) + ' para' if cyc[2] > cyc[0] else 'em'} {num(cyc[2], 1, lang)} dias (meta {num(cyc_t, 0, lang)}), com {k['rfqs']} RFQs concluídas{', o maior volume em três meses' if most else ''}.")))
    if sav_ok:
        headline = T(lang, "Savings are ahead of plan" + (", but " + " and ".join(issues[:2]) if issues else ", with delivery, quality and sourcing on target"),
                     "Savings acima do plano" + (", mas " + " e ".join(issues[:2]) if issues else ", com entrega, qualidade e sourcing na meta"))
    else:
        headline = T(lang, "Savings are behind plan" + (" and " + " and ".join(issues[:1]) if issues else ", while delivery and quality hold on target"),
                     "Savings abaixo do plano" + (" e " + " e ".join(issues[:1]) if issues else ", com entrega e qualidade na meta"))
    A = []
    if len(late):
        names = [f"{n} ({usd(lang)} {num(v, 2, lang)} {T(lang, 'M', 'mi')})" for n, v in bl_top.items()]
        A.append(T(lang, f"Expedite the {len(late)} overdue PO lines ({usd(lang)} {num(late.valor_total_usd.sum() / 1e6, 2, lang)} M), starting with {' and '.join(names)}.",
                   f"Cobrar as {len(late)} linhas de pedido atrasadas ({usd(lang)} {num(late.valor_total_usd.sum() / 1e6, 2, lang)} mi), começando por {' e '.join(names)}."))
    if worst.ppm > ppm_t:
        A.append(T(lang, f"Open an 8D with {worst.nome} and contain open receipts until PPM recovers.", f"Abrir um 8D com {worst.nome} e conter os recebimentos em aberto até o PPM voltar à meta."))
    if k["cyc"] > cyc_t:
        A.append(T(lang, f"Standard package and a 5-business-day response window for repeat RFQs, to bring the cycle under {num(cyc_t, 0, lang)} days.",
                   f"Pacote padrão e prazo de resposta de 5 dias úteis para RFQs recorrentes, para trazer o ciclo abaixo de {num(cyc_t, 0, lang)} dias."))
    if inc_ytd < 0:
        A.append(T(lang, f"Test the USD {num(abs(inc_ytd), 0, lang)}k of increases accepted YTD against each category PPI before renewals.",
                   f"Confrontar os US$ {num(abs(inc_ytd), 0, lang)} mil de aumentos aceitos no ano com o PPI de cada categoria antes das renovações."))
    if not sav_ok:
        A.append(T(lang, "Bring forward RFQs for items with purchase history and single-source exposure, where savings are measurable.",
                   "Antecipar RFQs de itens com histórico de compra e exposição a fonte única, onde o savings é mensurável."))
    A = A[:4]
    hl = "".join(f'<li><i class="{c}"></i><span>{t}</span></li>' for c, t in H)
    ac = "".join(f'<li><i class="n">{i + 1}</i><span>{t}</span></li>' for i, t in enumerate(A))
    next_m = MONTHS[lang][cutoff.month % 12]

    EXTRA = """
table.t.sc2 td, table.t.sc2 th { padding: .55mm 1.2mm; }
table.t tr.grp td { font-family:'IBM Plex Mono',monospace; font-size:6pt; letter-spacing:.08em; text-transform:uppercase; color:#1E5246; background:#E4ECE7; padding:.7mm 1.2mm; }
table.t td.tg { color:#5E6561; }
.dot { width:2.2mm; height:2.2mm; border-radius:50%; display:inline-block; } .dot.good{background:#1F7A4F} .dot.warn{background:#9A6412} .dot.bad{background:#A63A2A}
.hb { background:#E8E9E5; height:2mm; border-radius:.4mm; overflow:hidden; } .hb span { display:block; height:100%; background:#1E5246; }
td .hb { width:22mm; } td.sc { letter-spacing:.06em; font-size:7pt; }
.stk { display:flex; height:3.4mm; border-radius:.5mm; overflow:hidden; margin:1mm 0 1.6mm; } .stk span { display:block; height:100%; }
.lgs { display:grid; grid-template-columns:1fr 1fr; gap:.8mm 3mm; font-size:6.8pt; color:#454C48; }
.lg { display:flex; align-items:center; gap:1.4mm; } .lg i { width:2mm; height:2mm; display:inline-block; flex:none; } .lg b { margin-left:auto; font-weight:500; color:#101714; }
.pb { margin-bottom:.9mm; } .pl { display:flex; justify-content:space-between; font-size:7.2pt; margin-bottom:.5mm; } .pl b { font-weight:500; }
ul.pc { list-style:none; margin:0; padding:0; font-size:7.6pt; line-height:1.42; } ul.pc li { display:flex; gap:2mm; margin-bottom:1.3mm; }
ul.pc i { flex:none; width:1.6mm; height:1.6mm; margin-top:1.3mm; } ul.pc i.good{background:#1F7A4F} ul.pc i.bad{background:#A63A2A} ul.pc i.warn{background:#9A6412}
ul.pc i.n { width:4mm; height:4mm; margin-top:.2mm; background:#0B302B; color:#F5F4EC; font-style:normal; font-family:'IBM Plex Mono',monospace; font-size:6.5pt; display:flex; align-items:center; justify-content:center; border-radius:.5mm; }
table.rt { width:100%; border-collapse:collapse; font-size:7.4pt; } table.rt td { padding:.8mm 0; border-bottom:1px solid #E8E9E5; } table.rt td:last-child { text-align:right; font-weight:500; }
.syn { display:inline-block; font-family:'IBM Plex Mono',monospace; font-size:6pt; letter-spacing:.08em; color:#0B302B; background:#35D58A; padding:.5mm 1.5mm; border-radius:.5mm; margin-top:2.5mm; }
.page { gap: 2.3mm; padding-top: 7.5mm; padding-bottom: 6mm; } .kpi { padding: 2.4mm 3mm; } .kpi .v { font-size: 15pt; } .card { padding: 2.3mm 3mm; } .sec { margin-bottom: 1.3mm; } .hdr { padding: 4mm 6mm 4.5mm; }
"""
    month_title = T(lang, f"{MONTHS['en'][cutoff.month-1]} {cutoff.year}", f"{MONTHS['pt'][cutoff.month-1].capitalize()} de {cutoff.year}")
    span = T(lang, f"1–{cutoff.day} {MON['en'][cutoff.month-1]}" if mtd else "Full month", f"1 a {cutoff.day}/{cutoff.month:02d}" if mtd else "Mês fechado")
    body = f"""<style>{EXTRA}</style>
<div class="hdr"><div class="grid"></div><div class="in"><div>
<div class="eyebrow"><span class="node"></span>{T(lang, 'Monthly procurement performance report · Direct materials · Aerospace', 'Relatório mensal de compras · Materiais diretos · Aeroespacial')}</div>
<h1>{headline}</h1>
<span class="syn">{T(lang, 'SYNTHETIC DATA · PORTFOLIO CASE', 'DADOS SINTÉTICOS · CASO DE PORTFÓLIO')}</span></div>
<div class="side"><div class="sm">{T(lang, 'Reporting month', 'Mês de referência')}</div><div class="big">{month_title}</div><div class="sm" style="margin-top:2mm">{T(lang, 'Month to date' if mtd else 'Period', 'Parcial do mês' if mtd else 'Período')}</div><div class="big" style="font-size:9pt">{span} · {T(lang, 'edition', 'edição')} {edition_label(edition, lang)}</div></div></div></div>
<div class="kpis" style="grid-template-columns:repeat(5,1fr)">
<div class="kpi inv"><div class="lb">{T(lang, 'Savings YTD', 'Savings no ano')}</div><div class="v">{num(sav_ytd, 0, lang)}{T(lang, 'k', ' mil')}</div><div class="d">{usd(lang)} · {pct(sav_ytd / tgt_ytd * 100, 0, lang)} {T(lang, 'of target', 'da meta')}</div></div>
<div class="kpi"><div class="lb">{T(lang, 'Spend MTD' if mtd else 'Spend', 'Gasto parcial' if mtd else 'Gasto')}</div><div class="v">{num(k['spend'], 1, lang)}{T(lang, 'M', ' mi')}</div><div class="d">{usd(lang)} · {mlab[PREV]} {num(kp_['spend'], 1, lang)}{T(lang, 'M', ' mi')}</div></div>
<div class="kpi"><div class="lb">{T(lang, 'On-time delivery', 'Entrega no prazo')}</div><div class="v {status(k['otd'], otd_t, True)}">{pct(k['otd'], 1, lang)}</div><div class="d">{pp(k['otd'] - otd_t, 1, lang)} {T(lang, 'vs', 'vs meta de')} {pct(otd_t, 0, lang)}{T(lang, ' target', '')}</div></div>
<div class="kpi"><div class="lb">{T(lang, 'Incoming PPM', 'PPM de recebimento')}</div><div class="v {status(k['ppm'], ppm_t, False)}">{num(k['ppm'], 0, lang)}</div><div class="d">{T(lang, 'Target', 'Meta')} {num(ppm_t, 0, lang)} · {mlab[PREV]} {num(kp_['ppm'], 0, lang)}</div></div>
<div class="kpi"><div class="lb">{T(lang, 'RFQ cycle', 'Ciclo de RFQ')}</div><div class="v {status(k['cyc'], cyc_t, False)}">{num(k['cyc'], 1, lang)}{T(lang, 'd', ' d')}</div><div class="d">{T(lang, 'Target', 'Meta')} {num(cyc_t, 0, lang)} {T(lang, 'days', 'dias')} · {k['rfqs']} {T(lang, 'RFQs closed', 'RFQs concluídas')}</div></div>
</div>
<div style="display:grid;grid-template-columns:1.15fr 1fr;gap:4mm">
<div><div class="sec"><span class="no">01</span><h2>Scorecard</h2><span class="r">{T(lang, 'Status vs target', 'Status vs meta')}</span></div>
<table class="t sc2"><tr><th>{T(lang, 'Indicator', 'Indicador')}</th><th>{mlab[MESES[0]]}</th><th>{mlab[MESES[1]]}</th><th>{cur_lab}</th><th>{T(lang, 'Target', 'Meta')}</th><th></th></tr>{tb}</table></div>
<div><div class="sec"><span class="no">02</span><h2>{T(lang, 'Savings and negotiation', 'Savings e negociação')}</h2><span class="r">{cutoff.year} {T(lang, 'YTD', 'no ano')}</span></div>
<div class="card"><p class="ct">{T(lang, 'Cumulative savings vs target, USD thousand', 'Savings acumulado vs meta, US$ mil')}</p><p class="cs">{T(lang, f'{MONTHS["en"][cutoff.month-1]} target pro-rated to {cutoff.day} of {dim} days', f'Meta de {MONTHS["pt"][cutoff.month-1]} proporcional a {cutoff.day} de {dim} dias') if mtd else T(lang, 'Monthly targets, cumulative', 'Metas mensais acumuladas')}</p>{c_sav}</div>
<div class="card" style="margin-top:2mm"><table class="rt">
<tr><td>{T(lang, 'Savings validated by Finance', 'Savings validado por Finanças')}</td><td>{pct(val_ytd / sav_ytd * 100 if sav_ytd else 0, 0, lang)}</td></tr>
<tr><td>{T(lang, 'Increases accepted YTD (USD k)', 'Aumentos aceitos no ano (US$ mil)')}</td><td class="bad">{num(inc_ytd, 0, lang)}</td></tr>
<tr><td>{T(lang, 'Net negotiation result YTD (USD k)', 'Resultado líquido no ano (US$ mil)')}</td><td>{num(sav_ytd + inc_ytd, 0, lang)}</td></tr></table></div></div>
</div>
<div><div class="sec"><span class="no">03</span><h2>{T(lang, 'Spend composition', 'Composição do gasto')}</h2><span class="r">{cur_lab}</span></div>
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:3mm">
<div class="card"><p class="ct">{T(lang, 'By category', 'Por categoria')}</p>{s1}</div><div class="card"><p class="ct">{T(lang, 'By currency', 'Por moeda')}</p>{s2}</div><div class="card"><p class="ct">{T(lang, 'By supplier segment', 'Por segmento de fornecedor')}</p>{s3}</div></div></div>
<div style="display:grid;grid-template-columns:1.15fr 1fr;gap:4mm">
<div><div class="sec"><span class="no">04</span><h2>{T(lang, 'Supplier performance', 'Performance de fornecedores')}</h2><span class="r">Top 6 · {mlab[MESES[0]]}–{mlab[CUR]}</span></div>
<table class="t"><tr><th>{T(lang, 'Supplier', 'Fornecedor')}</th><th>{T(lang, 'Spend', 'Gasto')}</th><th>{T(lang, 'USD M', 'US$ mi')}</th><th>OTD</th><th>PPM</th><th>Score</th></tr>{sup}</table>
<div class="card" style="margin-top:2mm"><p class="ct">{T(lang, 'Highlights and watch points', 'Destaques e pontos de atenção')}</p><ul class="pc">{hl}</ul></div></div>
<div><div class="sec"><span class="no">05</span><h2>{T(lang, 'Quality and actions', 'Qualidade e ações')}</h2><span class="r">{n_open} {T(lang, 'NCs open', 'NCs abertas')}</span></div>
<div class="card"><p class="ct">{T(lang, 'Non-conformances by reason', 'Não conformidades por motivo')}, {mlab[MESES[0]]}–{mlab[CUR]}</p>{ncb}</div>
<div class="card" style="margin-top:2mm"><p class="ct">{T(lang, 'Actions for ', 'Ações para ')}{next_m}</p><ul class="pc">{ac}</ul></div></div>
</div>
{footer(T(lang, f"Synthetic data, portfolio purposes only; no real company data. Prices indexed to the latest published BLS PPI of each category and FX at the monthly PTAX average. {'The month covers 1 to ' + str(cutoff.day) + ' ' + MON['en'][cutoff.month-1] + ' ' + str(cutoff.year) + '. ' if mtd else ''}Supplier score: up to 50 points for OTD and 50 for PPM (5 dots = 100). Status: green on target, amber within 5%, red beyond 5%.",
          f"Dados sintéticos, para portfólio; nenhum dado de empresa real. Preços indexados ao último PPI do BLS de cada categoria e câmbio pela PTAX média do mês. {'O mês cobre de 1 a ' + str(cutoff.day) + '/' + f'{cutoff.month:02d}' + '/' + str(cutoff.year) + '. ' if mtd else ''}Score: até 50 pontos por OTD e 50 por PPM (5 pontos = 100). Status: verde na meta, âmbar até 5% fora, vermelho acima de 5%.") + " " + bls_notice())}
"""
    name = T(lang, "Monthly_Procurement_Performance_Report", "Relatorio_Mensal_Performance_Compras") + f"_{CUR}"
    html = os.path.join(outdir, name + ".html")
    h, lvl = render_fit(body, T(lang, "Monthly Procurement Performance Report", "Relatório Mensal de Performance de Compras") + f" · {month_title}", lang,
                        html, os.path.join(outdir, name + ".pdf"), os.path.join(outdir, name + ".png") if png else None)
    return dict(name=name, height=h, fit_level=lvl, headline=headline, savings_ytd_pct=round(sav_ytd / tgt_ytd * 100, 1), otd=round(k["otd"], 2), ppm=round(k["ppm"]))
