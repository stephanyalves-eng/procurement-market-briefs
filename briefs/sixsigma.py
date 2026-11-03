"""Six Sigma Supplier Quality Report for the fictitious EV plant in Brazil (synthetic data).

Same dataset as the monthly supplier quality report, read through Six Sigma tools:
- Control: Laney p' chart of the monthly defective rate (corrects the false alarms of a classic p chart when lots are huge)
- Measure: DPMO and sigma level (1.5 sigma shift convention), by supplier origin
- Capability: Cp, Cpk (within, R-bar/d2) and Ppk (overall) of a critical characteristic at a local launch supplier
- Analyze: Pareto with cumulative share, and a two-proportion z test on containment speed
- Improve and control: DMAIC project portfolio against plan, and control-plan actions
Every number and sentence comes from the data."""
import os, sys, calendar
from statistics import NormalDist
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from .style import C, svg, rows_grid, footer, render_fit
from .common import ROOT, MON, MONTHS, T, num, pct, usd, edition_label

sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import sqe_synthetic as sq  # noqa: E402
import sixsigma_synthetic as ss  # noqa: E402

N = NormalDist()
ORG = {"BR": ("Local (Brazil)", "Locais (Brasil)"), "CN": ("China imports", "Importados da China"), "OT": ("Other imports", "Outras importações")}
PH = {"en": ["Define", "Measure", "Analyze", "Improve", "Control", "Closed"], "pt": ["Definir", "Medir", "Analisar", "Melhorar", "Controlar", "Encerrado"]}


def sigma_level(dpmo): return N.inv_cdf(1 - max(dpmo, 1e-3) / 1e6) + 1.5


def build(edition, cutoff, lang, outdir, png=True):
    sup, R, I, P, A = sq.view(cutoff); tg = sq.TARGETS
    c_end = pd.Timestamp(cutoff) + pd.Timedelta(hours=23, minutes=59)
    CUR = cutoff.strftime("%Y-%m"); dim = calendar.monthrange(cutoff.year, cutoff.month)[1]; mtd = cutoff.day < dim
    per = pd.Period(CUR, "M"); M3 = [str(per - 2), str(per - 1), CUR]
    mname = lambda m: MON[lang][int(m[5:]) - 1]
    R = R.copy(); I = I.copy()
    R["m"] = R.data_recebimento.dt.to_period("M").astype(str); I["m"] = I.data_abertura.dt.to_period("M").astype(str)
    names = sup.set_index("id_fornecedor")

    # ---------- control: Laney p' chart, last 18 months ----------
    m18 = [str(per - i) for i in range(17, -1, -1)]
    g = R[R.m.isin(m18)].groupby("m").agg(n=("qtd_recebida", "sum"), x=("qtd_rejeitada", "sum")).reindex(m18).fillna(0)
    p = g.x / g.n; pb = g.x.sum() / g.n.sum(); s = np.sqrt(pb * (1 - pb) / g.n); z = (p - pb) / s
    sz = np.abs(np.diff(z.values)).mean() / 1.128
    ucl = (pb + 3 * s * sz) * 1e6; lcl = np.maximum(0, pb - 3 * s * sz) * 1e6; ppm = p * 1e6
    out_hi = list(g.index[ppm > ucl]); out_lo = list(g.index[ppm < lcl])
    last_out = CUR in out_hi
    # run rule: 8 points in a row on one side of the centre line
    side = np.sign(ppm.values - pb * 1e6); run = 1
    for a_, b_ in zip(side[::-1], side[-2::-1]):
        if a_ == b_ and a_ != 0: run += 1
        else: break
    run_signal = run >= 8

    # ---------- measure: DPMO and sigma by origin, rolling three months ----------
    R3 = R[R.m.isin(M3)]
    def dpmo(df): return df.qtd_rejeitada.sum() / max(df.qtd_recebida.sum(), 1) * 1e6
    sig_rows = [("ALL", dpmo(R3))] + [(o, dpmo(R3[R3.origem == o])) for o in ("BR", "CN") if (R3.origem == o).any()]
    cur_dpmo = dpmo(R[R.m == CUR]); cur_sig = sigma_level(cur_dpmo); tgt_sig = sigma_level(tg["ppm"])

    # ---------- capability ----------
    Ms = ss.measurements(cutoff); Ms["m"] = Ms.data.dt.to_period("M").astype(str)
    def cap(df):
        rbar = df.groupby("subgrupo").valor_mm.agg(lambda x: x.max() - x.min()).mean(); sw = rbar / 2.326
        mu = df.valor_mm.mean(); so = df.valor_mm.std(ddof=1); lsl, usl = ss.CHAR["lsl"], ss.CHAR["usl"]
        return dict(n=len(df), mu=mu, sw=sw, so=so, cp=(usl - lsl) / (6 * sw), cpk=min(usl - mu, mu - lsl) / (3 * sw), ppk=min(usl - mu, mu - lsl) / (3 * so),
                    out=((df.valor_mm < lsl) | (df.valor_mm > usl)).mean() * 1e6)
    capm = {m: cap(gr) for m, gr in Ms.groupby("m")}
    cm = sorted(capm)[-12:]; ck = capm[CUR] if CUR in capm else capm[cm[-1]]
    ck_prev = capm[cm[-4]] if len(cm) >= 4 else ck

    # ---------- analyze ----------
    I3 = I[I.m.isin(M3)]
    par = I3.defeito.value_counts().head(6); n3 = len(I3); cum = par.cumsum() / n3 * 100
    a, b = I3[I3.origem == "CN"], I3[I3.origem == "BR"]
    x1, n1, x2, n2 = int((a.contencao_horas <= 24).sum()), len(a), int((b.contencao_horas <= 24).sum()), len(b)
    if n1 and n2:
        pp_ = (x1 + x2) / (n1 + n2); zt = (x2 / n2 - x1 / n1) / np.sqrt(pp_ * (1 - pp_) * (1 / n1 + 1 / n2)); pv = 2 * (1 - N.cdf(abs(zt)))
    else:
        zt, pv = 0.0, 1.0
    signif = pv < .05

    # ---------- DMAIC portfolio ----------
    PS = ss.project_status(cutoff)
    def metric(key, months):
        r = R[R.m.isin(months)]; i = I[I.m.isin(months)]
        if key == "ppm_corrosion_cn":
            rc = r[r.origem == "CN"]; ic = i[(i.origem == "CN") & (i.defeito == "Corrosion after sea transport")]
            return ic.qtd_rejeitada.sum() / max(rc.qtd_recebida.sum(), 1) * 1e6
        if key == "ppm_dim_br":
            rb = r[r.origem == "BR"]; ib = i[(i.origem == "BR") & (i.defeito == "Dimensional out of tolerance")]
            return ib.qtd_rejeitada.sum() / max(rb.qtd_recebida.sum(), 1) * 1e6
        if key == "c24_cn":
            ic = i[i.origem == "CN"]; return (ic.contencao_horas <= 24).mean() * 100 if len(ic) else np.nan
        if key == "cpk":
            d = Ms[Ms.m.isin(months)]; return cap(d)["cpk"] if len(d) else np.nan
        return np.nan
    rows, late = [], 0
    for pr in PS.itertuples():
        st_m = pd.Period(pr.start, "M"); base_m = [str(st_m - k) for k in (3, 2, 1)]
        if pr.metric == "ppap_fp_w3":
            prev = P[P.onda.isin([1, 2])].decisao_1.dropna(); cur3 = P[P.onda == 3].decisao_1.dropna()
            base, curv, target, fmtk, hb = (prev == "Approved").mean() * 100, (cur3 == "Approved").mean() * 100, tg["ppap_first_pass"], "p", True
        elif pr.metric == "cpk":
            base, curv, target, fmtk, hb = metric("cpk", base_m), ck["cpk"], 1.33, "c", True
        elif pr.metric == "c24_cn":
            base, curv, target, fmtk, hb = metric("c24_cn", base_m), metric("c24_cn", M3), tg["containment_24h"], "p", True
        else:
            base, curv = metric(pr.metric, base_m), metric(pr.metric, M3); target, fmtk, hb = base * .5, "i", False
        is_late = pr.phase < 5 and (pr.phase < pr.phase_plan or pr.late_weeks >= 2)
        late += is_late
        hit = (curv >= target) if hb else (curv <= target)
        rows.append(dict(id=pr.id, name=pr.en if lang == "en" else pr.pt, belt=pr.belt, phase=pr.phase, late=is_late, lw=pr.late_weeks,
                         base=base, cur=curv, target=target, fmt=fmtk, hit=hit, end=pr.end_act))
    PRJ = pd.DataFrame(rows); n_prj = len(PRJ); on_plan = n_prj - late

    def f(v, k):
        if v is None or (isinstance(v, float) and np.isnan(v)): return "–"
        return {"p": pct(v, 0, lang), "c": num(v, 2, lang), "i": num(v, 0, lang)}[k]

    # ---------- charts ----------
    x = np.arange(len(m18))
    fig, ax = plt.subplots(figsize=(4.4, 1.55)); fig.subplots_adjust(left=.085, right=.99, top=.97, bottom=.15)
    ax.fill_between(x, lcl, ucl, step="mid", color=C["accent"], lw=0)
    ax.step(x, ucl, where="mid", color=C["sage500"], lw=.8); ax.step(x, lcl, where="mid", color=C["sage500"], lw=.8)
    ax.axhline(pb * 1e6, color=C["ink3"], lw=.8, ls=(0, (3, 2)))
    ax.plot(x, ppm, color=C["forest700"], lw=1.4, marker="o", ms=2.6)
    for i_, m_ in enumerate(m18):
        if m_ in out_hi or m_ in out_lo: ax.plot(i_, ppm.iloc[i_], "o", color=C["bad"], ms=4.2)
    ax.plot(x[-1], ppm.iloc[-1], "o", color=C["bad"] if last_out else C["forest900"], ms=4.2)
    ax.axhline(tg["ppm"], color=C["bad"], lw=.8, ls=(0, (1, 1.5)))
    ax.text(x[-1] + .4, tg["ppm"], T(lang, "target", "meta"), fontsize=5.8, color=C["bad"], va="top", ha="left")
    ax.text(x[-1] + .4, ucl.iloc[-1], T(lang, "UCL", "LSC"), fontsize=5.8, color=C["ink3"], va="center", ha="left")
    ax.text(x[-1] + .4, pb * 1e6, T(lang, "mean", "média"), fontsize=5.8, color=C["ink3"], va="bottom", ha="left")
    rows_grid(ax); ax.set_xticks(x[::3], [mname(m) for m in m18][::3], fontsize=6.3); ax.tick_params(labelsize=6.3)
    ax.set_xlim(-.6, len(m18) + 1.3); ax.set_ylim(0, max(ucl.max(), ppm.max()) * 1.1)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: num(v, 0, lang))); c_ctrl = svg(fig)

    # histogram with spec limits
    d = Ms[Ms.m == (CUR if CUR in capm else cm[-1])].valor_mm
    fig, ax = plt.subplots(figsize=(2.35, 1.3)); fig.subplots_adjust(left=.04, right=.98, top=.9, bottom=.18)
    ax.hist(d, bins=np.linspace(-.6, .6, 25), color=C["sage500"], edgecolor="white", linewidth=.4)
    xs = np.linspace(-.6, .6, 200); pdf = np.exp(-.5 * ((xs - ck["mu"]) / ck["so"]) ** 2) / (ck["so"] * np.sqrt(2 * np.pi)) * len(d) * .05
    ax.plot(xs, pdf, color=C["forest700"], lw=1.1)
    for v_, lb in ((ss.CHAR["lsl"], "LSL"), (ss.CHAR["usl"], "USL")):
        ax.axvline(v_, color=C["bad"], lw=.9); ax.text(v_, ax.get_ylim()[1] * .98, lb, fontsize=5.8, color=C["bad"], ha="center", va="bottom")
    ax.axvline(0, color=C["ink3"], lw=.6, ls=(0, (2, 2)))
    ax.set_yticks([]); ax.tick_params(labelsize=6); ax.set_xticks([-.5, -.25, 0, .25, .5], [num(v_, 2, lang) for v_ in (-.5, -.25, 0, .25, .5)])
    c_hist = svg(fig)
    # Cpk trend
    fig, ax = plt.subplots(figsize=(2.0, 1.3)); fig.subplots_adjust(left=.16, right=.97, top=.9, bottom=.18)
    ax.plot(range(len(cm)), [capm[m]["cpk"] for m in cm], color=C["forest700"], lw=1.4, marker="o", ms=2.2)
    ax.axhline(1.33, color=C["bad"], lw=.8, ls=(0, (2, 2))); ax.text(0, 1.36, "1,33" if lang == "pt" else "1.33", fontsize=5.8, color=C["bad"])
    rows_grid(ax); ax.set_xticks(range(0, len(cm), 3), [mname(m) for m in cm][::3], fontsize=6); ax.tick_params(labelsize=6)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: num(v, 1, lang))); ax.set_ylim(0, max(1.7, max(capm[m]["cpk"] for m in cm) * 1.1)); c_cpk = svg(fig)

    # Pareto with cumulative line (HTML)
    mx = par.max()
    pareto = "".join(
        f'<div class="pr"><span class="pn">{k if lang == "en" else sq.DEFECT_PT.get(k, k)}</span><div class="hb"><span style="width:{v / mx * 100:.0f}%"></span></div>'
        f'<b>{v}</b><em class="{"in" if cum.iloc[i] - v / n3 * 100 < 80 else ""}">{pct(cum.iloc[i], 0, lang)}</em></div>' for i, (k, v) in enumerate(par.items()))
    vital = int((cum.shift(fill_value=0) < 80).sum())

    # ---------- tables ----------
    sigt = "".join(f'<tr><td>{T(lang, "All suppliers", "Todos os fornecedores") if o == "ALL" else ORG[o][0 if lang == "en" else 1]}</td>'
                   f'<td>{num(v, 0, lang)}</td><td class="{"bad" if sigma_level(v) < tgt_sig else "good"}">{num(sigma_level(v), 2, lang)}</td></tr>' for o, v in sig_rows)
    def phase_dots(ph, is_late):
        out_ = ""
        for i_ in range(5):
            cls = "done" if i_ < ph else ("cur late" if (i_ == ph and is_late) else "cur" if i_ == ph else "")
            out_ += f'<span class="ph {cls}">{"DMAIC"[i_]}</span>'
        return out_
    prt = ""
    for r in PRJ.itertuples():
        stat = (T(lang, "Closed, target met", "Encerrado, meta atingida") if r.hit else T(lang, "Closed, target missed", "Encerrado, meta não atingida")) if r.phase == 5 else (T(lang, f"{r.lw} wk late", f"{r.lw} sem. atraso") if r.late else T(lang, "On plan", "No plano"))
        prt += (f'<tr><td><b>{r.id}</b> {r.name}<div class="sub">{r.belt}</div></td><td class="phs">{phase_dots(min(r.phase, 5), r.late)}</td>'
                f'<td>{f(r.base, r.fmt)}</td><td class="{"good" if r.hit else ""}">{f(r.cur, r.fmt)}</td><td class="tg">{f(r.target, r.fmt)}</td>'
                f'<td class="{"bad" if (r.late or (r.phase == 5 and not r.hit)) else "good"}">{stat}</td></tr>')

    # ---------- data-driven text ----------
    mon_en, mon_pt = MONTHS["en"][cutoff.month - 1], MONTHS["pt"][cutoff.month - 1]
    up = ppm.iloc[-1] > ppm.iloc[-2]
    if last_out:
        p1 = T(lang, f"{mon_en.capitalize()}'s PPM broke the upper control limit, a special cause to investigate now",
               f"O PPM de {mon_pt} rompeu o limite superior de controle, uma causa especial a investigar já")
    elif run_signal:
        p1 = T(lang, f"PPM has stayed {'above' if side[-1] > 0 else 'below'} the mean for {run} months, a shift in the process",
               f"O PPM está {'acima' if side[-1] > 0 else 'abaixo'} da média há {run} meses, um deslocamento do processo")
    else:
        p1 = T(lang, f"{mon_en.capitalize()}'s PPM {'rise' if up else 'drop'} is common-cause variation",
               f"A {'alta' if up else 'queda'} do PPM em {mon_pt} é variação de causa comum")
    act = int((PRJ.phase < 5).sum()) if n_prj else 0
    if last_out:
        p2 = ""
    elif act:
        p2 = T(lang, f", so the gain has to come from the {act} active DMAIC projects, " + (f"{late} of them behind plan" if late else "all on plan"),
               f", então o ganho tem de vir dos {act} projetos DMAIC ativos, " + (f"{late} deles atrasados" if late else "todos no plano"))
    else:
        p2 = T(lang, ", and with every DMAIC project closed, the next one needs a charter", ", e com todos os projetos DMAIC encerrados, o próximo precisa ser aberto")
    headline = p1 + p2

    H = []
    H.append(("bad" if last_out else "good", T(lang,
        f"<b>Control:</b> {num(ppm.iloc[-1], 0, lang)} PPM in {mname(CUR)}, {'above' if last_out else 'inside'} limits of {num(lcl.iloc[-1], 0, lang)} to {num(ucl.iloc[-1], 0, lang)}. "
        + ("A special cause: contain and investigate first." if last_out else "Reacting to one month would be tampering; the mean of " + num(pb * 1e6, 0, lang) + " PPM is what must change."),
        f"<b>Controle:</b> {num(ppm.iloc[-1], 0, lang)} PPM em {mname(CUR)}, {'acima dos' if last_out else 'dentro dos'} limites de {num(lcl.iloc[-1], 0, lang)} a {num(ucl.iloc[-1], 0, lang)}. "
        + ("Causa especial: conter e investigar primeiro." if last_out else "Reagir a um mês seria ajuste excessivo; é a média de " + num(pb * 1e6, 0, lang) + " PPM que precisa mudar."))))
    H.append(("good" if ck["cpk"] >= 1.33 else "bad", T(lang,
        f"<b>Capability:</b> Cpk {num(ck['cpk'], 2, lang)} (from {num(ck_prev['cpk'], 2, lang)} three months earlier), {'but Ppk ' + num(ck['ppk'], 2, lang) + ' is still below 1.33: not yet stable' if ck['ppk'] < 1.33 else 'with Ppk ' + num(ck['ppk'], 2, lang) + ' above 1.33'}.",
        f"<b>Capacidade:</b> Cpk {num(ck['cpk'], 2, lang)} (era {num(ck_prev['cpk'], 2, lang)}), {'mas o Ppk de ' + num(ck['ppk'], 2, lang) + ' segue abaixo de 1,33: ainda instável' if ck['ppk'] < 1.33 else 'com Ppk de ' + num(ck['ppk'], 2, lang) + ' acima de 1,33'}.")))
    if n1 and n2:
        H.append(("bad" if signif else "warn", T(lang,
            f"<b>Hypothesis test:</b> containment within 24 h, {pct(x1 / n1 * 100, 0, lang)} China-based vs {pct(x2 / n2 * 100, 0, lang)} local (z = {num(zt, 2, lang)}, p = {num(pv, 3, lang)}): {'a real difference' if signif else 'not significant at 5%'}.",
            f"<b>Teste de hipótese:</b> contenção em 24 h de {pct(x1 / n1 * 100, 0, lang)} nos chineses vs {pct(x2 / n2 * 100, 0, lang)} nos locais (p = {num(pv, 3, lang)}): {'diferença real' if signif else 'não significativa a 5%'}.")))

    A_ = []
    late_prj = PRJ[PRJ.late & (PRJ.phase < 5)]
    if len(late_prj):
        r0 = late_prj.iloc[0]
        A_.append(T(lang, f"Gate review for {r0.id} ({PH['en'][min(r0.phase, 4)]} phase, {r0.lw} weeks late): confirm resources or re-baseline before the next phase.",
                    f"Revisão de gate do {r0.id} (fase {PH['pt'][min(r0.phase, 4)]}, {r0.lw} semanas de atraso): confirmar recursos ou replanejar antes da próxima fase."))
    if ck["ppk"] < 1.33:
        A_.append(T(lang, f"Keep 100% gauge check on the mounting point until Ppk ≥ 1.33 for two months, then move it to the control plan at 5 parts per shift.",
                    f"Inspeção 100% no ponto de fixação até Ppk ≥ 1,33 por dois meses; depois, 5 peças por turno no plano de controle."))
    if signif:
        A_.append(T(lang, "Start an Improve-phase pilot with two China-based suppliers: a named 24-hour contact and a local sorting partner, measured with the same test.",
                    "Piloto da fase Melhorar com dois fornecedores chineses: contato nomeado em 24 h e parceiro local de seleção, medidos com o mesmo teste."))
    if vital <= 3:
        A_.append(T(lang, f"Charter the next project on the vital few: the top {vital} defect types explain {pct(cum.iloc[max(vital - 1, 0)], 0, lang)} of issues over {mname(M3[0])}–{mname(CUR)}.",
                    f"Abrir o próximo projeto nos poucos vitais: os {vital} principais defeitos explicam {pct(cum.iloc[max(vital - 1, 0)], 0, lang)} dos problemas em {mname(M3[0])}–{mname(CUR)}."))
    else:
        A_.append(T(lang, f"The Pareto is flat ({vital} defect types to reach 80%): stratify by supplier and part number before chartering the next project.",
                    f"O Pareto está achatado ({vital} tipos de defeito para chegar a 80%): estratificar por fornecedor e part number antes de abrir o próximo projeto."))
    missed = PRJ[(PRJ.phase == 5) & ~PRJ.hit]
    if len(missed):
        A_.insert(0, T(lang, f"Reopen {missed.iloc[0].id} at Analyze: it closed without reaching its target, so the root cause was not confirmed.",
                          f"Reabrir o {missed.iloc[0].id} na fase Analisar: encerrou sem atingir a meta, então a causa raiz não foi confirmada."))
    A_ = A_[:4]
    hl = "".join(f'<li><i class="{c}"></i><span>{t}</span></li>' for c, t in H)
    ac = "".join(f'<li><i class="n">{i + 1}</i><span>{t}</span></li>' for i, t in enumerate(A_))
    next_m = MONTHS[lang][cutoff.month % 12]

    EXTRA = """
table.t td .sub { font-size:6.1pt; color:#5E6561; margin-top:.2mm; }
table.t td.tg { color:#5E6561; }
.hb { background:#E8E9E5; height:2.4mm; border-radius:.4mm; overflow:hidden; } .hb span { display:block; height:100%; background:#1E5246; }
.pr { display:grid; grid-template-columns: 46% 1fr 7mm 9mm; align-items:center; gap:1.6mm; font-size:7pt; margin-bottom:1mm; }
.pr b { font-weight:500; text-align:right; } .pr em { font-style:normal; text-align:right; color:#5E6561; font-family:'IBM Plex Mono',monospace; font-size:6.4pt; } .pr em.in { color:#1E5246; font-weight:500; }
.ph { display:inline-block; width:3.6mm; height:3.6mm; line-height:3.6mm; text-align:center; font-family:'IBM Plex Mono',monospace; font-size:5.8pt; border:1px solid #D6D8D2; color:#5E6561; margin-right:.5mm; border-radius:.4mm; }
.ph.done { background:#1E5246; border-color:#1E5246; color:#F5F4EC; } .ph.cur { background:#E4ECE7; border-color:#1E5246; color:#0B302B; font-weight:500; } .ph.cur.late { background:#F4DFD9; border-color:#A63A2A; color:#A63A2A; }
td.phs { white-space:nowrap; text-align:left !important; }
ul.pc { list-style:none; margin:0; padding:0; font-size:7.5pt; line-height:1.4; } ul.pc li { display:flex; gap:2mm; margin-bottom:1.2mm; }
ul.pc i { flex:none; width:1.6mm; height:1.6mm; margin-top:1.3mm; } ul.pc i.good{background:#1F7A4F} ul.pc i.bad{background:#A63A2A} ul.pc i.warn{background:#9A6412}
ul.pc i.n { width:4mm; height:4mm; margin-top:.2mm; background:#0B302B; color:#F5F4EC; font-style:normal; font-family:'IBM Plex Mono',monospace; font-size:6.5pt; display:flex; align-items:center; justify-content:center; border-radius:.5mm; }
.stats { display:grid; grid-template-columns:repeat(4,1fr); gap:1.5mm; margin-top:1.2mm; } .stats div { font-family:'IBM Plex Mono',monospace; font-size:5.9pt; letter-spacing:.06em; text-transform:uppercase; color:#5E6561; }
.stats b { display:block; font-family:'IBM Plex Sans'; font-size:9.5pt; letter-spacing:0; text-transform:none; color:#101714; font-weight:500; margin-top:.3mm; }
.syn { display:inline-block; font-family:'IBM Plex Mono',monospace; font-size:6pt; letter-spacing:.08em; color:#0B302B; background:#35D58A; padding:.5mm 1.5mm; border-radius:.5mm; margin-top:2.5mm; }
.page { gap: 2.2mm; padding-top: 7.5mm; padding-bottom: 6mm; } .kpi { padding: 2.3mm 3mm; } .kpi .v { font-size: 15pt; } .card { padding: 2.2mm 3mm; } .sec { margin-bottom: 1.2mm; } .hdr { padding: 4mm 6mm 4.5mm; } .hdr h1 { font-size: 14.5pt; }
"""
    month_title = T(lang, f"{MONTHS['en'][cutoff.month-1]} {cutoff.year}", f"{MONTHS['pt'][cutoff.month-1].capitalize()} de {cutoff.year}")
    span = T(lang, f"1–{cutoff.day} {MON['en'][cutoff.month-1]}" if mtd else "Full month", f"1 a {cutoff.day}/{cutoff.month:02d}" if mtd else "Mês fechado")
    ctrl_state = T(lang, "Out of control" if last_out else ("Shift" if run_signal else "In control"), "Fora de controle" if last_out else ("Deslocado" if run_signal else "Sob controle"))
    body = f"""<style>{EXTRA}</style>
<div class="hdr"><div class="grid"></div><div class="in"><div>
<div class="eyebrow"><span class="node"></span>{T(lang, 'Six Sigma supplier quality report · EV assembly plant · Brazil', 'Six Sigma em qualidade de fornecedores · Montadora de VE · Brasil')}</div>
<h1>{headline}</h1>
<span class="syn">{T(lang, 'SYNTHETIC DATA · FICTITIOUS PLANT WITH A CHINESE PARENT', 'DADOS SINTÉTICOS · MONTADORA FICTÍCIA DE CONTROLE CHINÊS')}</span></div>
<div class="side"><div class="sm">{T(lang, 'Reporting month', 'Mês de referência')}</div><div class="big">{month_title}</div><div class="sm" style="margin-top:2mm">{T(lang, 'Period', 'Período')}</div><div class="big" style="font-size:9pt">{span} · {T(lang, 'edition', 'edição')} {edition_label(edition, lang)}</div></div></div></div>
<div class="kpis" style="grid-template-columns:repeat(5,1fr)">
<div class="kpi inv"><div class="lb">{T(lang, 'Sigma level', 'Nível sigma')}</div><div class="v">{num(cur_sig, 2, lang)}σ</div><div class="d">{T(lang, 'Target', 'Meta')} {num(tgt_sig, 2, lang)}σ ({num(tg['ppm'], 0, lang)} DPMO)</div></div>
<div class="kpi"><div class="lb">DPMO</div><div class="v {'bad' if cur_dpmo > tg['ppm'] else 'good'}">{num(cur_dpmo, 0, lang)}</div><div class="d">{T(lang, 'Defective parts per million received', 'Defeituosos por milhão')}</div></div>
<div class="kpi"><div class="lb">{T(lang, 'Process status', 'Estado do processo')}</div><div class="v {'bad' if last_out else 'warn' if run_signal else 'good'}" style="font-size:12.5pt">{ctrl_state}</div><div class="d">{T(lang, 'UCL', 'LSC')} {num(ucl.iloc[-1], 0, lang)} · Laney p′</div></div>
<div class="kpi"><div class="lb">Cpk · {T(lang, 'mounting point', 'fixação')}</div><div class="v {'good' if ck['cpk'] >= 1.33 else 'bad'}">{num(ck['cpk'], 2, lang)}</div><div class="d">Ppk {num(ck['ppk'], 2, lang)} · {T(lang, 'target', 'meta')} ≥ {num(1.33, 2, lang)}</div></div>
<div class="kpi"><div class="lb">{T(lang, 'DMAIC on plan', 'DMAIC no plano')}</div><div class="v {'good' if late == 0 else 'warn' if late == 1 else 'bad'}">{act - late}/{act}</div><div class="d">{T(lang, 'active', 'ativos')} · {n_prj - act} {T(lang, 'closed', 'encerrado' if n_prj - act == 1 else 'encerrados')}</div></div>
</div>
<div style="display:grid;grid-template-columns:1.45fr 1fr;gap:4mm">
<div><div class="sec"><span class="no">01</span><h2>{T(lang, 'Control: is the process stable?', 'Controle: o processo está estável?')}</h2><span class="r">18 {T(lang, 'months', 'meses')}</span></div>
<div class="card"><p class="ct">{T(lang, "Laney p′ chart, incoming PPM", "Gráfico p′ de Laney, PPM de recebimento")}</p><p class="cs">{T(lang, 'Limits widen for overdispersion; a classic p chart flags every month when lots run to the hundreds of thousands', 'Limites ajustados à sobredispersão; um gráfico p clássico acusaria todo mês com lotes de centenas de milhares')}</p>{c_ctrl}</div></div>
<div><div class="sec"><span class="no">02</span><h2>{T(lang, 'Measure: sigma level', 'Medir: nível sigma')}</h2><span class="r">{mname(M3[0])}–{mname(CUR)}</span></div>
<table class="t"><tr><th>{T(lang, 'Origin', 'Origem')}</th><th>DPMO</th><th>{T(lang, 'Sigma', 'Sigma')}</th></tr>{sigt}</table>
<div class="card" style="margin-top:2mm"><p class="ct">{T(lang, 'Highlights', 'Destaques')}</p><ul class="pc">{hl}</ul></div></div>
</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:4mm">
<div><div class="sec"><span class="no">03</span><h2>{T(lang, 'Capability', 'Capacidade')}</h2><span class="r">{ss.CHAR['name_en'] if lang == 'en' else ss.CHAR['name_pt']}</span></div>
<div class="card"><div style="display:grid;grid-template-columns:1.2fr 1fr;gap:2mm"><div><p class="cs" style="margin:0">{T(lang, f'{mname(CUR)} · ±0.50 mm · {ck["n"]} parts', f'{mname(CUR)} · ±0,50 mm · {ck["n"]} peças')}</p>{c_hist}</div><div><p class="cs" style="margin:0">{T(lang, 'Cpk by month', 'Cpk por mês')}</p>{c_cpk}</div></div>
<div class="stats"><div>Cp<b>{num(ck['cp'], 2, lang)}</b></div><div>Cpk<b class="{'good' if ck['cpk'] >= 1.33 else 'bad'}">{num(ck['cpk'], 2, lang)}</b></div><div>Ppk<b class="{'good' if ck['ppk'] >= 1.33 else 'bad'}">{num(ck['ppk'], 2, lang)}</b></div><div>{T(lang, 'Mean', 'Média')}<b>{num(ck['mu'], 3, lang)}</b></div></div></div></div>
<div><div class="sec"><span class="no">04</span><h2>{T(lang, 'Analyze: Pareto', 'Analisar: Pareto')}</h2><span class="r">{n3} {T(lang, 'issues', 'problemas')} · {T(lang, 'cum. %', '% acum.')}</span></div>
<div class="card">{pareto}<p class="cs" style="margin:1.2mm 0 0">{T(lang, f'{vital} defect types reach 80% of issues' + (': a flat Pareto, no vital few.' if vital > 3 else '.'), f'{vital} tipos chegam a 80%' + (': Pareto achatado, sem poucos vitais.' if vital > 3 else '.'))}</p></div></div>
</div>
<div><div class="sec"><span class="no">05</span><h2>{T(lang, 'Improve: DMAIC project portfolio', 'Melhorar: portfólio de projetos DMAIC')}</h2><span class="r">{T(lang, 'Baseline = three months before start', 'Base = três meses antes do início')}</span></div>
<table class="t"><tr><th>{T(lang, 'Project', 'Projeto')}</th><th style="text-align:left">D M A I C</th><th>{T(lang, 'Baseline', 'Base')}</th><th>{T(lang, 'Now', 'Atual')}</th><th>{T(lang, 'Target', 'Meta')}</th><th>Status</th></tr>{prt}</table></div>
<div><div class="sec"><span class="no">06</span><h2>{T(lang, 'Control plan and actions for ', 'Plano de controle e ações para ')}{next_m}</h2></div>
<div class="card"><ul class="pc" style="columns:2;column-gap:5mm;display:block">{''.join(f'<li style="break-inside:avoid"><i class="n">{i + 1}</i><span>{t}</span></li>' for i, t in enumerate(A_))}</ul></div></div>
{footer(T(lang, "Synthetic data for a fictitious EV assembler in Brazil with a Chinese parent company; plant, suppliers, projects and measurements are invented. Laney p′ chart with 3-sigma limits; sigma level from DPMO with the 1.5σ shift convention; Cpk uses within-subgroup sigma (R̄/d₂, n = 5), Ppk the overall standard deviation; two-proportion z test at 5%. Projects: Belt level and DMAIC gates are illustrative.",
          "Dados sintéticos de uma montadora fictícia de veículos elétricos no Brasil com controle chinês; planta, fornecedores, projetos e medições são inventados. Gráfico p′ de Laney com limites de 3 sigma; nível sigma a partir do DPMO com a convenção de deslocamento de 1,5σ; Cpk usa o sigma dentro do subgrupo (R̄/d₂, n = 5) e Ppk o desvio padrão total; teste z de duas proporções a 5%. Belts e gates ilustrativos."))}
"""
    name = T(lang, "Six_Sigma_Supplier_Quality_Report", "Relatorio_Six_Sigma_Qualidade_Fornecedores") + f"_{CUR}"
    html = os.path.join(outdir, name + ".html")
    h, lvl = render_fit(body, T(lang, "Six Sigma Supplier Quality Report", "Relatório Six Sigma de Qualidade de Fornecedores") + f" · {month_title}", lang,
                        html, os.path.join(outdir, name + ".pdf"), os.path.join(outdir, name + ".png") if png else None)
    return dict(name=name, height=h, fit_level=lvl, headline=headline, sigma=round(cur_sig, 2), cpk=round(ck["cpk"], 2), p_value=round(pv, 4))
