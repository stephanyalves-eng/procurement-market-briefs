"""Brazil EV Supply Chain Brief: electrified car, Li-ion battery and auto parts imports (Comex Stat) against the import duty schedule."""
import os
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from .style import C, svg, rows_grid, footer, render_fit
from .common import PUB, MON, MONTHS, T, num, pct, pp, usd, country, edition_label, period_label, ptax, fx_event, day_month

TIPO = {"870380": "BEV", "870360": "PHEV", "870370": "PHEV", "870340": "HEV", "870350": "HEV", "850760": "Li-ion"}
STEPS = [("2024-07", "BEV 18%", "BEV 18%"), ("2025-07", "BEV 25%", "BEV 25%"), ("2026-07", "All 35%", "Todos 35%"), ("2027-01", "Kits 35%", "Kits 35%")]


def build(edition, lang, outdir, png=True):
    d = pd.read_csv(os.path.join(PUB, "comex_auto_8703_8708_8507.csv"), dtype={"ncm": str})
    d["ano"] = d.mes.str[:4].astype(int); d["mm"] = d.mes.str[5:].astype(int)
    d["t"] = d.ncm.str[:6].map(TIPO); d.loc[d.ncm.str.startswith("8708"), "t"] = "Parts"
    Y = d.ano.max(); Lm = d[d.ano == Y].mm.max(); ytd = d[d.mm <= Lm]; per = period_label(1, Lm, lang)
    E = ytd[ytd.t.isin(["BEV", "PHEV", "HEV"])]
    un = E.groupby("ano").qtd_estatistica.sum(); fob_u = E.groupby("ano").valor_fob_usd.sum() / un

    def china(df, col):
        s = df.groupby(["ano", "pais_origem"])[col].sum().unstack(fill_value=0); return s.get("China", 0) / s.sum(axis=1) * 100
    ch_e = china(E, "qtd_estatistica"); ch_b = china(ytd[ytd.t == "Li-ion"], "valor_fob_usd"); ch_p = china(ytd[ytd.t == "Parts"], "valor_fob_usd")
    bat = ytd[ytd.t == "Li-ion"].groupby("ano").valor_fob_usd.sum() / 1e6; prt = ytd[ytd.t == "Parts"].groupby("ano").valor_fob_usd.sum() / 1e9
    eY = E[E.ano == Y]; mayjun = eY[eY.mm.isin([5, 6])].qtd_estatistica.sum() / eY.qtd_estatistica.sum() * 100 if Lm >= 6 else None
    by_t = eY.groupby("t").qtd_estatistica.sum()
    y0 = max(Y - 3, int(ch_e.index.min()))
    k = dict(u=un[Y], u0=un[Y - 1], g=(un[Y] / un[Y - 1] - 1) * 100, ch=ch_e[Y], bat=bat[Y], bat_g=(bat[Y] / bat[Y - 1] - 1) * 100,
             prt=prt[Y], prt_g=(prt[Y] / prt[Y - 1] - 1) * 100, chp=ch_p[Y], chp0=ch_p[Y - 1], chb=ch_b[Y], fu0=fob_u[y0], fu=fob_u[Y])
    up = k["g"] >= 0; after_2027 = edition.year >= 2027

    # chart 1: monthly stacked units with the duty steps
    m = d[d.t.isin(["BEV", "PHEV", "HEV"]) & (d.mes >= f"{Y - 2}-01")].pivot_table(index="mes", columns="t", values="qtd_estatistica", aggfunc="sum").fillna(0) / 1e3
    f, ax = plt.subplots(figsize=(5.2, 2.0)); f.subplots_adjust(left=.06, right=.995, top=.86, bottom=.13)
    x = np.arange(len(m)); base = np.zeros(len(m)); cols = {"BEV": C["forest700"], "PHEV": C["sage500"], "HEV": C["cat"][2]}
    for t in ["BEV", "PHEV", "HEV"]:
        if t in m: ax.bar(x, m[t], bottom=base, color=cols[t], width=.78, label=t); base += m[t].values
    rows_grid(ax)
    for mes, en, pt_ in STEPS:
        if mes in m.index:
            i = list(m.index).index(mes); ax.axvline(i - .5, color=C["bad"], lw=.9, ls=(0, (3, 2)))
            ax.text(i - .2, base.max() * 1.02, T(lang, en, pt_), fontsize=6.4, color=C["bad"], va="bottom")
    tk = [i for i, s in enumerate(m.index) if s.endswith("-01") or s.endswith("-07")]
    ax.set_xticks(tk, [f"{MON[lang][int(m.index[i][5:]) - 1]} {m.index[i][2:4]}" for i in tk], fontsize=6.5)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: num(v, 0, lang)))
    ax.tick_params(labelsize=6.5); ax.set_ylim(0, base.max() * 1.16)
    ax.legend(frameon=False, fontsize=6.5, ncol=3, loc="upper left", bbox_to_anchor=(0, 1.2), handlelength=1); c1 = svg(f)

    # chart 2: China share
    lab = [T(lang, "Electrified cars\n(units)", "Carros eletrificados\n(unidades)"), T(lang, "Li-ion batteries\n(USD)", "Baterias íon-lítio\n(US$)"), T(lang, "Auto parts\n(USD)", "Autopeças\n(US$)")]
    v0 = [ch_e[y0], ch_b[y0], ch_p[y0]]; v1 = [ch_e[Y], ch_b[Y], ch_p[Y]]
    f, ax = plt.subplots(figsize=(2.55, 2.0)); f.subplots_adjust(left=.36, right=.97, top=.9, bottom=.04)
    yy = np.arange(3)[::-1]
    ax.barh(yy + .19, v0, height=.36, color=C["context"], label=str(y0)); ax.barh(yy - .19, v1, height=.36, color=C["bad"], label=str(Y))
    for y_, a, b in zip(yy, v0, v1):
        ax.text(a + 1.5, y_ + .19, pct(a, 0, lang), va="center", fontsize=6.6, color=C["ink3"]); ax.text(b + 1.5, y_ - .19, pct(b, 0, lang), va="center", fontsize=6.8)
    ax.set_yticks(yy, lab, fontsize=6.6); ax.set_xticks([]); ax.spines["bottom"].set_visible(False); ax.tick_params(length=0); ax.set_xlim(0, 118)
    ax.legend(frameon=False, fontsize=6.5, ncol=2, loc="upper left", bbox_to_anchor=(-.5, 1.13), handlelength=1); c2 = svg(f)

    Pp = ytd[ytd.t == "Parts"].pivot_table(index="pais_origem", columns="ano", values="valor_fob_usd", aggfunc="sum").fillna(0)
    S = Pp / Pp.sum() * 100; top = S.drop(index="Outros", errors="ignore").sort_values(Y, ascending=False).head(6)
    rows = "".join(f"<tr><td>{country(c, lang)}</td><td>{pct(r[Y-1], 1, lang)}</td><td>{pct(r[Y], 1, lang)}</td><td class='{'bad' if r[Y]-r[Y-1] > 2 else ''}'>{pp(r[Y]-r[Y-1], 1, lang)}</td></tr>" for c, r in top.iterrows())
    tar = [("Jan 2024", "jan/2024", "10%", "12%", "15%", "Schedule starts", "Início do cronograma"), ("Jul 2024", "jul/2024", "18%", "20%", "25%", "", ""),
           ("Jul 2025", "jul/2025", "25%", "28%", "30%", "", ""), ("Jul 2026", "jul/2026", "35%", "35%", "35%", "SKD kits 35%; CKD 14% to Dec", "SKD 35%; CKD 14% até dez."),
           ("Jan 2027", "jan/2027", "35%", "35%", "35%", "All kits 35%", "Todos os kits 35%")]
    trows = "".join(f"<tr><td>{T(lang, a, a2)}</td><td>{b}</td><td>{c}</td><td>{e}</td><td style='text-align:left'>{T(lang, k1, k2)}</td></tr>" for a, a2, b, c, e, k1, k2 in tar)

    # text
    when = T(lang, "Since January 2027" if after_2027 else "From 2027", "Desde janeiro de 2027" if after_2027 else "A partir de 2027")
    headline = T(lang, f"Electrified car imports {'rose' if up else 'fell'} {num(abs(k['g']), 0, lang)}% to {num(k['u'] / 1e3, 0, lang)}k units, {num(k['ch'], 0, lang)}% from China, and spiked before every July tariff step. {when}, localization is the only cost lever left",
                 f"Importação de carros eletrificados {'sobe' if up else 'cai'} {num(abs(k['g']), 0, lang)}% para {num(k['u'] / 1e3, 0, lang)} mil unidades, {num(k['ch'], 0, lang)}% da China, com picos antes de cada aumento de imposto em julho. {when}, nacionalizar é a alavanca de custo que resta")
    fl = (T(lang, f" {num(mayjun, 0, lang)}% of the year's volume landed in May and June, ahead of the July step that took all electrified categories to 35%.",
            f" {num(mayjun, 0, lang)}% do volume do ano chegou em maio e junho, antes do degrau de julho que levou todas as categorias de eletrificados a 35%.") if mayjun is not None else "")
    lead = T(lang, f"Brazil imported {num(k['u'] / 1e3, 0, lang)}k battery-electric, plug-in and hybrid cars in {per} {Y} ({num(by_t.get('BEV', 0) / 1e3, 0, lang)}k BEV, {num(by_t.get('PHEV', 0) / 1e3, 0, lang)}k PHEV, {num(by_t.get('HEV', 0) / 1e3, 0, lang)}k HEV), against {num(k['u0'] / 1e3, 0, lang)}k a year earlier.{fl} Average FOB value fell from USD {num(k['fu0'] / 1e3, 1, lang)}k in {y0} to {num(k['fu'] / 1e3, 1, lang)}k per unit, consistent with kits for local assembly and cheaper models entering the mix. With kit duties converging to 35% in January 2027, the remaining lever is local content: batteries, body parts and tires.",
             f"O Brasil importou {num(k['u'] / 1e3, 0, lang)} mil carros elétricos, plug-in e híbridos em {per} de {Y} ({num(by_t.get('BEV', 0) / 1e3, 0, lang)} mil BEV, {num(by_t.get('PHEV', 0) / 1e3, 0, lang)} mil PHEV, {num(by_t.get('HEV', 0) / 1e3, 0, lang)} mil HEV), contra {num(k['u0'] / 1e3, 0, lang)} mil um ano antes.{fl} O valor FOB médio caiu de US$ {num(k['fu0'] / 1e3, 1, lang)} mil em {y0} para US$ {num(k['fu'] / 1e3, 1, lang)} mil por unidade, coerente com a entrada de kits para montagem local e de modelos mais baratos. Com o imposto dos kits convergindo para 35% em janeiro de 2027, a alavanca que resta é o conteúdo local: baterias, peças de carroceria e pneus.")
    kpi2 = (f'<div class="kpi"><div class="lb">{T(lang, "Front-loading", "Antecipação")}</div><div class="v warn">{pct(mayjun, 0, lang)}</div><div class="d">{T(lang, f"of {per} units imported in May and June", f"das unidades de {per} importadas em maio e junho")}</div></div>'
            if mayjun is not None else f'<div class="kpi"><div class="lb">{T(lang, "China share", "Participação da China")}</div><div class="v warn">{pct(k["ch"], 0, lang)}</div><div class="d">{T(lang, "of electrified car units", "das unidades de carros eletrificados")}</div></div>')
    dd = ptax(edition); ev = fx_event(dd)
    fx_txt = (T(lang, f"USD/BRL {'jumped' if ev['chg'] > 0 else 'fell'} {num(abs(ev['chg']), 0, lang)}% in one session on {day_month(ev['date'], 'en')}.", f"o dólar {'subiu' if ev['chg'] > 0 else 'caiu'} {num(abs(ev['chg']), 0, lang)}% em um pregão em {day_month(ev['date'], 'pt')}.")
              if ev else T(lang, "the BRL can move several percent in a month.", "o real pode oscilar vários pontos percentuais em um mês."))
    imp = [T(lang, "<b>Localize by duty saved, not by part count:</b> at 35%, every USD 1,000 of imported kit content carries about USD 350 of import duty before other taxes. Rank parts by duty saved per tooling dollar; bumpers, tires, seats, glass and harnesses usually come first.",
             "<b>Nacionalizar pelo imposto evitado, não pelo número de peças:</b> a 35%, cada US$ 1.000 de conteúdo importado em kit carrega cerca de US$ 350 de imposto de importação, antes dos demais tributos. Priorizar pelo imposto evitado por real investido em ferramental; para-choques, pneus, bancos, vidros e chicotes costumam vir primeiro."),
           T(lang, f"<b>Batteries are the largest block:</b> Li-ion imports {'grew' if k['bat_g'] >= 0 else 'changed'} {pct(k['bat_g'], 0, lang, k['bat_g'] < 0)} with {pct(k['chb'], 0, lang)} from China. A staged path (imported cells, local pack assembly, then local modules) captures value while cell supply stays concentrated.",
             f"<b>Bateria é o maior bloco:</b> a importação de íon-lítio {'cresceu' if k['bat_g'] >= 0 else 'variou'} {pct(k['bat_g'], 0, lang, k['bat_g'] < 0)}, com {pct(k['chb'], 0, lang)} da China. Um caminho em etapas (célula importada, montagem local do pack, depois módulos locais) captura valor enquanto o fornecimento de células segue concentrado."),
           T(lang, f"<b>Build the local supplier pipeline now:</b> China went from {pct(k['chp0'], 0, lang)} to {pct(k['chp'], 0, lang)} of auto parts imports in one year. PPAP and validation lead times mean 2027 nationalization targets need supplier nominations in the coming months.",
             f"<b>Montar já a base de fornecedores locais:</b> a China passou de {pct(k['chp0'], 0, lang)} para {pct(k['chp'], 0, lang)} da importação de autopeças em um ano. Os prazos de PPAP e validação fazem com que as metas de nacionalização de 2027 exijam nomeação de fornecedores nos próximos meses."),
           T(lang, "<b>Smooth the inbound plan:</b> no step remains after January 2027, so the May–June peaks that drove inventory and working capital can end. Renegotiate freight and storage on flatter volumes.",
             "<b>Nivelar o plano de entrada:</b> não há degrau depois de janeiro de 2027, então os picos de maio e junho que inflaram estoque e capital de giro podem acabar. Renegociar frete e armazenagem com volumes mais estáveis."),
           T(lang, f"<b>Price FX into imported content:</b> {fx_txt} Use FX adjustment clauses or hedging for USD and CNY content.",
             f"<b>Precificar o câmbio no conteúdo importado:</b> {fx_txt} Usar cláusula de ajuste cambial ou hedge para o conteúdo em USD e CNY.")]
    body = f"""<style>.page {{ gap: 2.9mm; }}</style>
<div class="hdr"><div class="grid"></div><div class="in"><div>
<div class="eyebrow"><span class="node"></span>{T(lang, 'Brazil EV supply chain brief · Automotive sourcing · Edition', 'Brazil EV supply chain brief · Sourcing automotivo · Edição')} {edition_label(edition, lang).upper() if lang == 'en' else edition_label(edition, lang)}</div>
<h1>{headline}</h1></div>
<div class="side"><div class="sm">{T(lang, 'Edition', 'Edição')}</div><div class="big">{edition_label(edition, lang)}</div><div class="sm" style="margin-top:2mm">{T(lang, 'Data to', 'Dados até')}</div><div class="big" style="font-size:9pt">Comex Stat {T(lang, f"{MON['en'][Lm-1]} {Y}", f"{MON['pt'][Lm-1]}/{Y}")}</div></div></div></div>
<p class="lead">{lead}</p>
<div class="kpis" style="grid-template-columns:repeat(4,1fr)">
<div class="kpi inv"><div class="lb">{T(lang, 'Electrified car imports', 'Carros eletrificados')}</div><div class="v">{pct(k['g'], 0, lang, True)}</div><div class="d">{T(lang, f"{num(k['u']/1e3, 0, lang)}k units, {per} {Y} vs {num(k['u0']/1e3, 0, lang)}k", f"{num(k['u']/1e3, 0, lang)} mil unidades, {per} {Y} vs {num(k['u0']/1e3, 0, lang)} mil")}</div></div>
{kpi2}
<div class="kpi"><div class="lb">{T(lang, 'Li-ion battery imports', 'Baterias íon-lítio')}</div><div class="v">{pct(k['bat_g'], 0, lang, True)}</div><div class="d">{usd(lang)} {num(k['bat'], 0, lang)} {T(lang, 'M', 'mi')} · {pct(k['chb'], 0, lang)} {T(lang, 'from China', 'da China')}</div></div>
<div class="kpi"><div class="lb">{T(lang, 'Auto parts imports', 'Autopeças')}</div><div class="v">{usd(lang)} {num(k['prt'], 1, lang)} {T(lang, 'bn', 'bi')}</div><div class="d">{pct(k['prt_g'], 1, lang, True)} · {T(lang, 'China share', 'China')} {pct(k['chp0'], 0, lang)} {T(lang, 'to', 'para')} {pct(k['chp'], 0, lang)}</div></div>
</div>
<div style="display:grid;grid-template-columns:2fr 1fr;gap:3mm">
<div class="card"><p class="ct">{T(lang, 'Electrified car imports by month, thousand units', 'Importação mensal de carros eletrificados, mil unidades')}</p><p class="cs">NCM 8703.40/50 (HEV), 8703.60/70 (PHEV), 8703.80 (BEV) · {T(lang, f"Jan {Y-2} to {MON['en'][Lm-1]} {Y} · dashed lines mark duty steps", f"jan/{Y-2} a {MON['pt'][Lm-1]}/{Y} · linhas tracejadas marcam os degraus do imposto")}</p>{c1}</div>
<div class="card"><p class="ct">{T(lang, 'China share of imports', 'Participação da China')}</p><p class="cs">{per} {y0} vs {per} {Y}</p>{c2}</div>
</div>
<div style="display:grid;grid-template-columns:1.25fr 1fr;gap:5mm">
<div><div class="sec"><span class="no">01</span><h2>{T(lang, 'Implications for sourcing', 'Implicações para compras')}</h2></div><ol class="imp">{''.join(f'<li>{i}</li>' for i in imp)}</ol></div>
<div><div class="sec"><span class="no">02</span><h2>{T(lang, 'Import duty schedule', 'Imposto de importação')}</h2><span class="r">Gecex · {T(lang, 'cars', 'carros')}</span></div>
<table class="t"><tr><th>{T(lang, 'From', 'Desde')}</th><th>BEV</th><th>PHEV</th><th>HEV</th><th style="text-align:left">Kits</th></tr>{trows}</table>
<div class="sec" style="margin-top:3mm"><span class="no">03</span><h2>{T(lang, 'Origin of auto parts', 'Origem das autopeças')}</h2><span class="r">8708 · {T(lang, 'FOB share', 'FOB')}</span></div>
<table class="t"><tr><th>{T(lang, 'Origin', 'Origem')}</th><th>{Y-1}</th><th>{Y}</th><th>{T(lang, 'Change', 'Variação')}</th></tr>{rows}</table></div>
</div>
{footer(T(lang, f"Sources: MDIC Comex Stat, imports by NCM and country, headings 8703, 8708 and 8507.60, {per} {y0} to {Y}, FOB USD and statistical units; kits for local assembly may be reported under the same vehicle codes. Duty schedule: Gecex/MDIC resolutions on electrified vehicles (Nov 2023) and 2026 kit rates as reported by the trade press. FX: Banco Central do Brasil PTAX. Public data only; prepared for portfolio purposes, with no company confidential information.",
          f"Fontes: MDIC Comex Stat, importações por NCM e país, posições 8703, 8708 e 8507.60, {per} de {y0} a {Y}, FOB em US$ e unidades estatísticas; kits para montagem local podem ser registrados nos mesmos códigos de veículo. Imposto: resoluções Gecex/MDIC sobre veículos eletrificados (nov/2023) e alíquotas de kits de 2026 conforme a imprensa especializada. Câmbio: PTAX do Banco Central do Brasil. Somente dados públicos; material de portfólio, sem informação confidencial de empresa."))}
"""
    name = T(lang, "Brazil_EV_Supply_Chain_Brief", "Brief_Cadeia_Veiculos_Eletricos") + f"_{edition.isoformat()}"
    html = os.path.join(outdir, name + ".html")
    h, lvl = render_fit(body, T(lang, "Brazil EV Supply Chain Brief", "Brief da Cadeia de Veículos Elétricos") + f" · {edition_label(edition, lang)}", lang,
                        html, os.path.join(outdir, name + ".pdf"), os.path.join(outdir, name + ".png") if png else None)
    return dict(name=name, height=h, fit_level=lvl, headline=headline, units=int(k["u"]), growth=round(k["g"], 1), china=round(k["ch"], 1))
