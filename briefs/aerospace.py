"""Aerospace Supply Market Brief: aircraft parts demand (Comex Stat), US producer prices (BLS PPI) and FX (BCB PTAX)."""
import os, json, math
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from .style import C, svg, rows_grid, footer, page, render, render_fit
from .common import (PUB, MON, MONTHS, T, num, pct, pp, usd, country, country_subject, day_month, long_date, edition_label,
                     period_label, context, ptax, fx_event, part_of_month, bls_notice)

WORDS = {"en": {2: "twice", 3: "three times", 4: "four times", 5: "five times", 6: "six times", 7: "seven times", 8: "eight times",
                9: "nine times", 10: "ten times", 11: "eleven times", 12: "twelve times"},
         "pt": {2: "o dobro do", 3: "três vezes o", 4: "quatro vezes o", 5: "cinco vezes o", 6: "seis vezes o", 7: "sete vezes o",
                8: "oito vezes o", 9: "nove vezes o", 10: "dez vezes o", 11: "onze vezes o", 12: "doze vezes o"}}


def data(edition):
    c = pd.read_csv(os.path.join(PUB, "comex_aero_8807_8411.csv")); c["ano"] = c.mes.str[:4].astype(int); c["mm"] = c.mes.str[5:].astype(int)
    Y = c.ano.max(); L = c[c.ano == Y].mm.max(); c = c[c.mm <= L]
    x = c[c.ncm_posicao == 8807]; ytd = x.groupby("ano").valor_fob_usd.sum() / 1e6; ytd = ytd.loc[Y - 3:Y]
    t411 = c[c.ncm_posicao == 8411].groupby("ano").valor_fob_usd.sum()
    sh = x.pivot_table(index="pais_origem", columns="ano", values="valor_fob_usd", aggfunc="sum").fillna(0); sh = sh / sh.sum() * 100
    pp_ = pd.read_csv(os.path.join(PUB, "bls_ppi_aeroespacial_metais_mensal.csv")).set_index("mes").sort_index()
    pm = pp_.dropna(subset=["ppi_avionica_navegacao_PCU334511"]).index.max()
    pm0 = f"{int(pm[:4]) - 1}{pm[4:]}"; yoy = (pp_.loc[pm] / pp_.loc[pm0] - 1) * 100
    fx = pd.read_csv(os.path.join(PUB, "bcb_cambio_ipca_mensal.csv")).set_index("mes")
    dd = ptax(edition); last = dd.index.max(); u = dd.usd_brl_ptax_venda.iloc[-1]; e = dd.eur_brl_ptax_venda.iloc[-1]
    ref_m = f"{last.year - 1}-{last.month:02d}"; u_ref = fx.loc[ref_m, "usd_brl_ptax_media"]; e_ref = fx.loc[ref_m, "eur_brl_ptax_media"]
    ev = fx_event(dd)
    if ev:
        before = dd.loc[:pd.Timestamp(ev["prev_date"])]
        pre = before.loc[pd.Timestamp(ev["date"]).replace(day=1):] if pd.Timestamp(ev["date"]).month == last.month else before.tail(20)
        ev["pre_vs_ref"] = (pre.usd_brl_ptax_venda.mean() / u_ref - 1) * 100
        ev["vs_before"] = (u / ev["before"] - 1) * 100
    st = json.load(open(os.path.join(PUB, "comex_status.json"))) if os.path.exists(os.path.join(PUB, "comex_status.json")) else {}
    return dict(Y=Y, L=L, ytd=ytd, g=(ytd[Y] / ytd[Y - 1] - 1) * 100, t411=(t411[Y] / t411[Y - 1] - 1) * 100, sh=sh,
                pm=pm, av=yoy["ppi_avionica_navegacao_PCU334511"], pa=yoy["ppi_pecas_aeronauticas_PCU336413"], en=yoy["ppi_motores_aeronauticos_PCU336412"],
                dd=dd, last=last.date(), u=u, e=e, ref_m=ref_m, u_ref=u_ref, vs=(u / u_ref - 1) * 100, e_vs=(e / e_ref - 1) * 100, ev=ev,
                comex_updated=st.get("comex_updated"))


def charts(k, lang):
    Y, ytd = k["Y"], k["ytd"]
    f, ax = plt.subplots(figsize=(2.45, 1.9)); f.subplots_adjust(left=.02, right=.98, top=.97, bottom=.12)
    b = ax.bar([str(i) for i in ytd.index], ytd.values, color=[C["context"]] * (len(ytd) - 1) + [C["forest700"]], width=.62)
    for r, v in zip(b, ytd.values): ax.text(r.get_x() + r.get_width() / 2, v + ytd.max() * .02, num(v, 0, lang), ha="center", fontsize=7.5, color=C["ink"])
    ax.set_yticks([]); ax.tick_params(length=0); ax.set_ylim(0, ytd.max() * 1.15); c1 = svg(f)

    lab = [("en", T(lang, "Engines", "Motores")), ("pa", T(lang, "Aircraft parts", "Peças")), ("av", T(lang, "Avionics", "Aviônica"))]
    vals = [k[a] for a, _ in lab]
    f, ax = plt.subplots(figsize=(2.45, 1.9)); f.subplots_adjust(left=.3, right=.97, top=.97, bottom=.08)
    ax.barh([l for _, l in lab], vals, color=[C["context"], C["context"], C["bad"] if k["av"] >= 5 else C["forest700"]], height=.55)
    for i, v in enumerate(vals): ax.text(max(v, 0) + max(vals) * .025, i, pct(v, 1, lang, True), va="center", fontsize=7.5)
    ax.set_xticks([]); ax.spines["bottom"].set_visible(False); ax.tick_params(length=0); ax.set_xlim(min(0, min(vals)), max(vals) * 1.35); c2 = svg(f)

    dd = k["dd"]; start = (pd.Timestamp(k["last"]) - pd.DateOffset(months=3)).replace(day=1); s = dd.loc[start:].usd_brl_ptax_venda
    f, ax = plt.subplots(figsize=(2.45, 1.9)); f.subplots_adjust(left=.15, right=.97, top=.97, bottom=.14)
    ax.plot(s.index, s.values, color=C["forest700"], lw=1.4); rows_grid(ax)
    ax.axhline(k["u_ref"], color=C["sage500"], lw=.9, ls=(0, (3, 2)))
    ref = int(k["ref_m"][5:])
    ax.text(s.index[0], k["u_ref"] + .015, T(lang, f"{MON['en'][ref-1]} {k['ref_m'][:4]} avg {k['u_ref']:.2f}", f"média {MON['pt'][ref-1]}/{k['ref_m'][2:4]} {num(k['u_ref'], 2, 'pt')}"), fontsize=6.3, color=C["ink3"])
    if k["ev"]:
        t = pd.Timestamp(k["ev"]["date"]); ax.plot([t], [k["ev"]["after"]], "o", color=C["bad"], ms=3.5)
        ax.annotate(f"{day_month(k['ev']['date'], lang)}  {num(k['ev']['after'], 2, lang)}", (t, k["ev"]["after"]), xytext=(-46, -3), textcoords="offset points", fontsize=6.6, color=C["bad"])
    ticks = pd.date_range(start, s.index.max() + pd.offsets.MonthBegin(1), freq="MS")
    ax.set_xticks(ticks, [MON[lang][d.month - 1] for d in ticks]); ax.set_ylim(s.min() - .08, s.max() + .1)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: num(v, 1, lang))); c3 = svg(f)
    return c1, c2, c3


def times_word(ratio, lang):
    r = int(ratio); return WORDS[lang].get(r, f"{r} times" if lang == "en" else f"{r} vezes o")


def build(edition, lang, outdir, png=True):
    k = data(edition); Y, L, ev, last = k["Y"], k["L"], k["ev"], k["last"]
    per = period_label(1, L, lang); pm_y, pm_m = int(k["pm"][:4]), int(k["pm"][5:])
    ppi_lab = T(lang, f"{MON['en'][pm_m-1]} {pm_y}", f"{MON['pt'][pm_m-1]}/{pm_y}")
    ppi_prev = T(lang, f"{MON['en'][pm_m-1]} {pm_y-1}", f"{MON['pt'][pm_m-1]}/{pm_y-1}")
    ref_m = int(k["ref_m"][5:]); ref_lab = T(lang, f"{MONTHS['en'][ref_m-1]} {k['ref_m'][:4]}", f"{MONTHS['pt'][ref_m-1]} de {k['ref_m'][:4]}")
    ref_short = T(lang, f"{MON['en'][ref_m-1]} {k['ref_m'][:4]}", f"{MON['pt'][ref_m-1]}/{k['ref_m'][2:4]}")
    up = k["g"] >= 0; g, av = k["g"], k["av"]
    c1, c2, c3 = charts(k, lang)

    # headline
    h1 = T(lang, f"Aircraft parts demand {'up' if up else 'down'} {num(abs(g), 1, lang)}% and avionics prices {'up' if av >= 0 else 'down'} {num(abs(av), 1, lang)}%",
           f"Demanda por peças aeronáuticas {'sobe' if up else 'cai'} {num(abs(g), 1, lang)}% e preço de aviônica {'sobe' if av >= 0 else 'cai'} {num(abs(av), 1, lang)}%")
    if ev and ev["chg"] > 0 and abs(k["vs"]) < 2 and ev["pre_vs_ref"] < -2:
        d = ev["date"]; h2 = T(lang, f", while the {part_of_month(d.day, 'en')}-{MONTHS['en'][d.month-1]} BRL selloff erased most of the currency cushion",
                                f", enquanto a alta do dólar no {part_of_month(d.day, 'pt')} {MONTHS['pt'][d.month-1]} apagou quase toda a folga do câmbio")
    elif ev and ev["chg"] > 0:
        h2 = T(lang, ", while a sharp BRL selloff raises import costs", ", enquanto uma alta forte do dólar encarece as importações")
    elif k["vs"] < -2:
        h2 = T(lang, f", with the BRL still {num(abs(k['vs']), 0, lang)}% stronger than a year ago", f", com o real ainda {num(abs(k['vs']), 0, lang)}% mais forte que há um ano")
    elif k["vs"] > 2:
        h2 = T(lang, f", and a BRL {num(k['vs'], 0, lang)}% weaker than a year ago adds to import costs", f", e um real {num(k['vs'], 0, lang)}% mais fraco que há um ano pesa no custo de importação")
    else:
        h2 = T(lang, ", with the BRL back near last year's level", ", com o real de volta ao nível de um ano atrás")
    headline = h1 + h2

    # lead
    s1 = T(lang, f"Brazilian imports of aircraft parts reached USD {num(k['ytd'][Y], 0, lang)} million in {per} {Y}, {num(abs(g), 1, lang)}% {'above' if up else 'below'} {Y-1}.",
           f"A importação brasileira de peças aeronáuticas chegou a US$ {num(k['ytd'][Y], 0, lang)} milhões em {per} de {Y}, {num(abs(g), 1, lang)}% {'acima' if up else 'abaixo'} de {Y-1}.")
    base = max(k["pa"], k["en"])
    if base > 0 and av > 2 * base:
        s2 = T(lang, f" US avionics producer prices rose {num(av, 1, lang)}% in twelve months, roughly {times_word(av / base, 'en')} the pace of aircraft parts ({pct(k['pa'], 1, lang, True)}) and engines ({pct(k['en'], 1, lang, True)}).",
               f" O preço ao produtor de aviônica nos EUA subiu {num(av, 1, lang)}% em doze meses, cerca de {times_word(av / base, 'pt')} ritmo de peças ({pct(k['pa'], 1, lang, True)}) e motores ({pct(k['en'], 1, lang, True)}).")
    else:
        s2 = T(lang, f" US producer prices changed {pct(av, 1, lang, True)} for avionics, {pct(k['pa'], 1, lang, True)} for aircraft parts and {pct(k['en'], 1, lang, True)} for engines in twelve months.",
               f" Em doze meses, o preço ao produtor nos EUA variou {pct(av, 1, lang, True)} em aviônica, {pct(k['pa'], 1, lang, True)} em peças e {pct(k['en'], 1, lang, True)} em motores.")
    if ev:
        note = context(edition, lang, "fx_event"); note = f", {note}," if note else ""
        pre = ev["pre_vs_ref"]
        s3 = T(lang, f" Until {ev['prev_date'].day} {MONTHS['en'][ev['prev_date'].month-1]} the BRL was trading {num(abs(pre), 1, lang)}% {'stronger' if pre < 0 else 'weaker'} than a year earlier; on {ev['date'].day} {MONTHS['en'][ev['date'].month-1]}{note} USD PTAX {'jumped' if ev['chg'] > 0 else 'fell'} {num(abs(ev['chg']), 1, lang)}% in one session and closed {last.day} {MONTHS['en'][last.month-1]} {'only ' if abs(k['vs']) < 2 else ''}{num(abs(k['vs']), 1, lang)}% {'below' if k['vs'] < 0 else 'above'} the {ref_lab} average.",
               f" Até {ev['prev_date'].day} de {MONTHS['pt'][ev['prev_date'].month-1]}, o real estava {num(abs(pre), 1, lang)}% {'mais forte' if pre < 0 else 'mais fraco'} que um ano antes; em {ev['date'].day} de {MONTHS['pt'][ev['date'].month-1]}{note} a PTAX do dólar {'subiu' if ev['chg'] > 0 else 'caiu'} {num(abs(ev['chg']), 1, lang)}% em um pregão e fechou {last.day} de {MONTHS['pt'][last.month-1]} {'apenas ' if abs(k['vs']) < 2 else ''}{num(abs(k['vs']), 1, lang)}% {'abaixo' if k['vs'] < 0 else 'acima'} da média de {ref_lab}.")
    else:
        s3 = T(lang, f" USD PTAX closed {last.day} {MONTHS['en'][last.month-1]} at {num(k['u'], 4, lang)}, {num(abs(k['vs']), 1, lang)}% {'below' if k['vs'] < 0 else 'above'} the {ref_lab} average.",
               f" A PTAX do dólar fechou {last.day} de {MONTHS['pt'][last.month-1]} em {num(k['u'], 4, lang)}, {num(abs(k['vs']), 1, lang)}% {'abaixo' if k['vs'] < 0 else 'acima'} da média de {ref_lab}.")
    lead = s1 + s2 + s3

    # KPIs
    fx_d = (f"<span class='{'bad' if ev['vs_before'] > 0 else 'good'}'>{pct(ev['vs_before'], 1, lang, True)}</span> {T(lang, 'vs', 'vs')} {day_month(ev['prev_date'], lang)} · {pct(k['vs'], 1, lang, True)} {T(lang, 'vs', 'vs')} {T(lang, ref_short + ' avg', 'média ' + ref_short)}"
            if ev else f"{pct(k['vs'], 1, lang, True)} {T(lang, 'vs ' + ref_short + ' avg', 'vs média ' + ref_short)}")
    kpis = f"""
<div class="kpi inv"><div class="lb">{T(lang, 'Aircraft parts imports', 'Importação de peças')}</div><div class="v">{pct(g, 1, lang, True)}</div><div class="d">NCM 8807, {per} {Y} {T(lang, 'vs', 'vs')} {Y-1} · {usd(lang)} {num(k['ytd'][Y], 0, lang)} {T(lang, 'M', 'mi')}</div></div>
<div class="kpi"><div class="lb">{T(lang, 'Avionics PPI (US)', 'PPI aviônica (EUA)')}</div><div class="v {'bad' if av >= 5 else ''}">{pct(av, 1, lang, True)}</div><div class="d">PCU334511, {ppi_lab} {T(lang, 'vs', 'vs')} {ppi_prev}</div></div>
<div class="kpi"><div class="lb">USD/BRL PTAX · {day_month(last, lang)}</div><div class="v">{num(k['u'], 4, lang)}</div><div class="d">{fx_d}</div></div>
<div class="kpi"><div class="lb">EUR/BRL PTAX · {day_month(last, lang)}</div><div class="v">{num(k['e'], 4, lang)}</div><div class="d">{pct(k['e_vs'], 1, lang, True)} {T(lang, 'vs ' + ref_short + ' avg', 'vs média ' + ref_short)}</div></div>"""

    # implications
    q = (edition.month - 1) // 3 + 1; budget_y = edition.year + 1 if edition.month >= 7 else edition.year
    imp = []
    if av >= 5:
        imp.append(T(lang, f"<b>Avionics:</b> move renewals to index-linked clauses (PPI PCU334511 with a trigger band) instead of fixed annual increases. A {num(av, 0, lang)}% step in one year makes fixed-price multi-year offers a supplier-side bet you pay for upfront.",
                     f"<b>Aviônica:</b> levar as renovações para cláusulas indexadas (PPI PCU334511 com banda de gatilho) no lugar de reajuste anual fixo. Um salto de {num(av, 0, lang)}% em um ano transforma oferta de preço fixo plurianual numa aposta do fornecedor que você paga adiantado."))
    else:
        imp.append(T(lang, f"<b>Avionics:</b> PPI growth eased to {pct(av, 1, lang, True)}. Keep index-linked clauses, and use the calmer period to lock multi-year pricing where suppliers offer it.",
                     f"<b>Aviônica:</b> o PPI desacelerou para {pct(av, 1, lang, True)}. Manter as cláusulas indexadas e aproveitar o período mais calmo para fechar preço plurianual onde o fornecedor oferecer."))
    if (ev and ev["chg"] > 0) or k["vs"] > -2:
        imp.append(T(lang, f"<b>FX:</b> the planning assumption of a stronger BRL no longer holds. Revisit Q{q} USD and EUR payables with Treasury, and avoid locking {budget_y} budget rates on {'one volatile week' if ev else 'a single month'}: use a 30-day average and a sensitivity band.",
                     f"<b>Câmbio:</b> a premissa de real forte deixou de valer. Revisar com a Tesouraria os pagamentos em USD e EUR do {q}º trimestre e não fechar o câmbio do orçamento {budget_y} com base {'numa semana volátil' if ev else 'num único mês'}: usar média de 30 dias e banda de sensibilidade."))
    else:
        imp.append(T(lang, f"<b>FX:</b> the BRL is {num(abs(k['vs']), 1, lang)}% stronger than a year ago. Prioritize USD-denominated spot buys and consider hedging the {budget_y} baseline with Treasury.",
                     f"<b>Câmbio:</b> o real está {num(abs(k['vs']), 1, lang)}% mais forte que há um ano. Priorizar compras spot em dólar e avaliar com a Tesouraria o hedge da base de {budget_y}."))
    sh = k["sh"].drop(index="Outros", errors="ignore"); top = sh.sort_values(Y, ascending=False).head(6)
    leader = top.index[0]; ls = sh.loc[leader]
    trend = "keeps" if ls[Y] < ls[Y - 1] < ls.get(Y - 2, np.inf) else ("loses" if ls[Y] < ls[Y - 1] else "gains")
    gain = (top[Y] - top[Y - 1]).drop(leader); gain = gain[gain > .5].sort_values(ascending=False).head(2)
    if trend != "gains" and len(gain):
        gl = " and ".join(country(c, "en") for c in gain.index) if lang == "en" else " e ".join(country_subject(c, "pt") for c in gain.index)
        lead_en = country_subject(leader, "en"); lead_pt = country_subject(leader, "pt")
        pl = lead_pt.startswith("os ")
        v_seg = "seguem" if pl else "segue"; v_loss = ("continuam perdendo" if pl else "continua perdendo") if trend == "keeps" else ("perdem" if pl else "perde")
        imp.append(T(lang, f"<b>Supply base:</b> {lead_en} still leads but {'keeps losing' if trend == 'keeps' else 'loses'} share, while {gl} gain. Qualify second sources there for single-source parts before demand growth tightens capacity.",
                     f"<b>Base de fornecimento:</b> {lead_pt} {v_seg} na liderança, mas {v_loss} participação, enquanto {gl} ganham espaço. Qualificar segundas fontes nesses países para itens de fonte única antes que o crescimento da demanda aperte a capacidade."))
    else:
        imp.append(T(lang, f"<b>Supply base:</b> {country_subject(leader, 'en')} leads with {pct(ls[Y], 1, lang)} of imports. Map single-source parts against the top origins before demand growth tightens capacity.",
                     f"<b>Base de fornecimento:</b> {country_subject(leader, 'pt')} lidera{'m' if country_subject(leader, 'pt').startswith('os ') else ''} com {pct(ls[Y], 1, lang)} das importações. Mapear os itens de fonte única contra as principais origens antes que a demanda aperte a capacidade."))
    if abs(k["t411"]) >= 40:
        imp.append(T(lang, f"<b>Data check:</b> turbine imports (NCM 8411) {'fell' if k['t411'] < 0 else 'rose'} about {num(abs(k['t411']), 0, lang)}% in {Y}. Confirm classification or reporting changes before using them in forecasts.",
                     f"<b>Checagem de dados:</b> a importação de turbinas (NCM 8411) {'caiu' if k['t411'] < 0 else 'subiu'} cerca de {num(abs(k['t411']), 0, lang)}% em {Y}. Confirmar mudança de classificação ou de registro antes de usar em previsões."))
    imp_html = "".join(f"<li>{i}</li>" for i in imp)

    rows = "".join(f"<tr><td>{country(c, lang)}</td><td>{pct(r[Y-1], 1, lang)}</td><td>{pct(r[Y], 1, lang)}</td><td class='{'bad' if r[Y]-r[Y-1] < -.5 else ('good' if r[Y]-r[Y-1] > .5 else '')}'>{pp(r[Y]-r[Y-1], 1, lang)}</td></tr>" for c, r in top.iterrows())

    nxt_p = pm_m % 12 + 1; nxt_c = L % 12 + 1
    w_fx = T(lang, f"USD/BRL holding above {num(k['u_ref'], 2, lang)} ({ref_short} average) for two weeks means the year-on-year FX gain is gone. <b>Action:</b> reprice open BRL budgets for USD items.",
             f"Dólar acima de {num(k['u_ref'], 2, lang)} (média de {ref_short}) por duas semanas significa que o ganho cambial do ano acabou. <b>Ação:</b> reprecificar os orçamentos em reais de itens em dólar.")
    if av >= 5:
        w_p = T(lang, f"{MONTHS['en'][nxt_p-1]} PPI for avionics above +{num(av - 2, 0, lang)}% YoY confirms a structural step, not a one-off. <b>Action:</b> escalate open avionics renewals to index-linked terms.",
                f"PPI de aviônica de {MONTHS['pt'][nxt_p-1]} acima de +{num(av - 2, 0, lang)}% em 12 meses confirma um degrau estrutural, não pontual. <b>Ação:</b> levar as renovações abertas de aviônica para termos indexados.")
    else:
        w_p = T(lang, f"{MONTHS['en'][nxt_p-1]} PPI for avionics back above +5% YoY would reopen the escalation risk. <b>Action:</b> keep trigger bands in open renewals.",
                f"PPI de aviônica de {MONTHS['pt'][nxt_p-1]} de volta acima de +5% em 12 meses reabriria o risco de reajuste. <b>Ação:</b> manter bandas de gatilho nas renovações abertas.")
    if g >= 0:
        w_d = T(lang, f"Comex {MONTHS['en'][nxt_c-1]} data keeping 8807 growth above {max(0, math.floor(g) - 1)}% YTD signals tighter supplier capacity. <b>Action:</b> secure {Y+1} slots and lead times now.",
                f"Dados de {MONTHS['pt'][nxt_c-1]} do Comex mantendo o crescimento da 8807 acima de {max(0, math.floor(g) - 1)}% no ano indicam capacidade mais apertada nos fornecedores. <b>Ação:</b> garantir agora as janelas e os lead times de {Y+1}.")
    else:
        w_d = T(lang, f"Comex {MONTHS['en'][nxt_c-1]} data showing 8807 imports still falling YTD would confirm softer demand. <b>Action:</b> renegotiate lead times and minimum order quantities.",
                f"Dados de {MONTHS['pt'][nxt_c-1]} do Comex com a 8807 ainda em queda no ano confirmariam demanda mais fraca. <b>Ação:</b> renegociar lead times e lotes mínimos.")
    watch = "".join(f'<div class="card"><div class="eyebrow" style="color:#5E6561">{t}</div><p style="margin:1.2mm 0 0;font-size:8pt;line-height:1.45">{x}</p></div>'
                    for t, x in ((T(lang, "FX", "Câmbio"), w_fx), (T(lang, "Prices", "Preços"), w_p), (T(lang, "Demand", "Demanda"), w_d)))

    MON_EN = MON['en']
    upd = pd.Timestamp(k["comex_updated"]).date() if k["comex_updated"] else None
    ctx = context(edition, lang, "footer")
    src = T(lang, f"Sources: MDIC Comex Stat, imports NCM 8807 and 8411, FOB USD, {per}{f' (published {upd.day} {MON_EN[upd.month-1]} {upd.year})' if upd else ''}. U.S. Bureau of Labor Statistics PPI PCU334511, PCU336413, PCU336412 (latest release: {ppi_lab}). Banco Central do Brasil SGS series 1 and 21619, PTAX selling rate, to {day_month(last, 'en')} {last.year}. {ctx + ' ' if ctx else ''}Public data only; prepared for portfolio purposes, not investment advice.",
              f"Fontes: MDIC Comex Stat, importações NCM 8807 e 8411, FOB em US$, {per}{f' (publicado em {upd:%d/%m/%Y})' if upd else ''}. U.S. Bureau of Labor Statistics, PPI PCU334511, PCU336413 e PCU336412 (última divulgação: {ppi_lab}). Banco Central do Brasil, SGS séries 1 e 21619, PTAX de venda, até {last:%d/%m/%Y}. {ctx + ' ' if ctx else ''}Somente dados públicos; material de portfólio, não é recomendação de investimento.")
    src += " " + bls_notice()

    body = f"""
<div class="hdr"><div class="grid"></div><div class="in"><div>
<div class="eyebrow"><span class="node"></span>{T(lang, 'Aerospace supply market brief · Brazil · Edition', 'Aerospace supply market brief · Brasil · Edição')} {edition_label(edition, lang).upper() if lang == 'en' else edition_label(edition, lang)}</div>
<h1>{headline}</h1></div>
<div class="side"><div class="sm">{T(lang, 'Edition', 'Edição')}</div><div class="big">{edition_label(edition, lang)}</div><div class="sm" style="margin-top:2mm">{T(lang, 'Data to', 'Dados até')}</div><div class="big" style="font-size:9pt">PTAX {day_month(last, lang)} · Comex {MON[lang][L-1]} · PPI {MON[lang][pm_m-1]}</div></div></div></div>
<p class="lead">{lead}</p>
<div class="kpis" style="grid-template-columns:repeat(4,1fr)">{kpis}</div>
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:3mm">
<div class="card"><p class="ct">{T(lang, 'Aircraft parts imports', 'Importação de peças aeronáuticas')}</p><p class="cs">NCM 8807 · {per} · {T(lang, 'USD million', 'US$ milhões')}</p>{c1}</div>
<div class="card"><p class="ct">{T(lang, 'US producer prices, 12 months', 'Preço ao produtor nos EUA, 12 meses')}</p><p class="cs">PPI · {ppi_lab} {T(lang, 'vs', 'vs')} {ppi_prev}</p>{c2}</div>
<div class="card"><p class="ct">{T(lang, 'USD/BRL PTAX, daily', 'PTAX USD/BRL, diária')}</p><p class="cs">{T(lang, 'Last four months to', 'Últimos quatro meses até')} {day_month(last, lang)} · {T(lang, 'selling rate', 'taxa de venda')}</p>{c3}</div>
</div>
<div style="display:grid;grid-template-columns:1.25fr 1fr;gap:5mm">
<div><div class="sec"><span class="no">01</span><h2>{T(lang, 'Implications for procurement', 'Implicações para compras')}</h2></div><ol class="imp">{imp_html}</ol></div>
<div><div class="sec"><span class="no">02</span><h2>{T(lang, 'Origin of 8807 imports', 'Origem da 8807')}</h2><span class="r">{T(lang, 'FOB share', 'FOB')} · {per}</span></div>
<table class="t"><tr><th>{T(lang, 'Origin', 'Origem')}</th><th>{Y-1}</th><th>{Y}</th><th>{T(lang, 'Change', 'Variação')}</th></tr>{rows}</table></div>
</div>
<div><div class="sec"><span class="no">03</span><h2>{T(lang, 'Watch list for the next edition', 'O que acompanhar na próxima edição')}</h2><span class="r">{T(lang, 'Trigger · action', 'Gatilho · ação')}</span></div>
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:3mm">{watch}</div></div>
{footer(src)}
"""
    name = T(lang, "Aerospace_Supply_Market_Brief", "Brief_Mercado_Aeroespacial") + f"_{edition.isoformat()}"
    html = os.path.join(outdir, name + ".html")
    h, lvl = render_fit(body, T(lang, "Aerospace Supply Market Brief", "Brief de Mercado Aeroespacial") + f" · {edition_label(edition, lang)}", lang,
                        html, os.path.join(outdir, name + ".pdf"), os.path.join(outdir, name + ".png") if png else None)
    return dict(name=name, height=h, fit_level=lvl, headline=headline, g=round(g, 2), avionics_ppi=round(av, 2), usd=k["u"], ptax_to=str(last))
