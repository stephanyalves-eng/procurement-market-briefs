"""Supplier Non-Conformance Report for the fictitious EV plant in Brazil (synthetic data), in a simpler format:
how many non-conformances, where they come from, what the defects are, what caused them (6M) and what to do.
Data from pipeline/sqe_synthetic.py; root causes are assigned to closed non-conformances only."""
import os, sys, calendar
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from .style import C, svg, rows_grid, footer, render_fit
from .common import ROOT, MON, MONTHS, T, num, pct, usd, edition_label

sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import sqe_synthetic as sq  # noqa: E402

DEF = lambda k, lang: k if lang == "en" else sq.DEFECT_PT.get(k, k)
CAU = lambda k, lang: k if lang == "en" else sq.CAUSE_PT.get(k, k)
SRC = {"Incoming inspection": ("Incoming inspection", "Inspeção de recebimento"), "Assembly line": ("Assembly line", "Linha de montagem"), "Field": ("Field (customer)", "Campo (cliente)")}
ORG = {"BR": ("Local suppliers", "Fornecedores locais"), "CN": ("China imports", "Importados da China"), "OT": ("Other imports", "Outras importações")}
ORG_S = {"BR": ("Local", "Local"), "CN": ("China", "China"), "OT": ("Other import", "Outra importação")}
SHORT = {"Dimensional out of tolerance": ("Dimensional", "Dimensional"), "Packaging and transport damage": ("Transport damage", "Dano no transporte"),
         "Missing or incomplete PPAP documentation": ("PPAP documents", "Documentos de PPAP"), "Appearance and paint": ("Appearance", "Aparência"),
         "Weld and joining": ("Welding", "Solda"), "Corrosion after sea transport": ("Corrosion", "Corrosão"), "Labeling and documentation": ("Labeling", "Etiquetagem"),
         "Wrong revision (ECN not communicated)": ("Wrong revision", "Revisão errada"), "Functional or electrical test failure": ("Test failure", "Falha em teste")}
SIXM = ["Method", "Machine", "Man", "Material", "Measurement", "Environment"]

# Five Whys: illustrative chains for the most frequent root causes (the last answer is the root cause itself)
WHYS = {
    "Packaging specification not adapted to the route": (
        ["Parts arrived dented or scratched", "Boxes collapsed during transport", "Packaging was designed for road freight, not 45 days at sea plus trucking",
         "The packaging specification was copied from the supplier's domestic standard", "Packaging was not validated for the export route in the PPAP"],
        ["Peças chegaram amassadas ou riscadas", "As caixas cederam no transporte", "A embalagem foi pensada para frete rodoviário, não para 45 dias de navio mais caminhão",
         "A especificação de embalagem foi copiada do padrão doméstico do fornecedor", "A embalagem não foi validada para a rota de exportação no PPAP"]),
    "Humidity in containers on long voyages": (
        ["Metal parts arrived with surface corrosion", "Moisture condensed inside the container", "Temperature swings between Asia and Brazil in the southern summer",
         "No desiccant and no humidity indicator in the container", "Packaging instructions do not define humidity protection for sea freight"],
        ["Peças metálicas chegaram com corrosão superficial", "A umidade condensou dentro do contêiner", "Variação de temperatura entre a Ásia e o Brasil no verão",
         "Sem dessecante nem indicador de umidade no contêiner", "A instrução de embalagem não define proteção contra umidade no frete marítimo"]),
    "Paint line parameters unstable": (
        ["Parts rejected for paint runs and orange peel", "Film thickness varied from part to part", "Booth temperature and humidity drifted during the shift",
         "Parameters are adjusted by feel, without limits on the control plan", "Paint line parameters were not frozen and monitored after launch"],
        ["Peças reprovadas por escorrimento e casca de laranja", "A espessura de camada variou entre peças", "Temperatura e umidade da cabine variaram no turno",
         "Os parâmetros são ajustados no olho, sem limites no plano de controle", "Os parâmetros da linha de pintura não foram congelados e monitorados após o lançamento"]),
    "Worn tooling or fixture": (
        ["Mounting points out of tolerance", "The part shifts in the fixture during machining", "The fixture locators are worn",
         "There is no wear limit or replacement interval for the locators", "The tooling has no preventive maintenance plan"],
        ["Pontos de fixação fora de tolerância", "A peça se desloca no dispositivo durante a usinagem", "Os localizadores do dispositivo estão desgastados",
         "Não há limite de desgaste nem intervalo de troca dos localizadores", "O ferramental não tem plano de manutenção preventiva"]),
    "Engineering change not communicated to the supplier": (
        ["Parts delivered at the previous revision", "The supplier produced to the old drawing", "The supplier never received the new revision",
         "The change notice went only to the plant's internal teams", "The engineering change process has no supplier acknowledgement step"],
        ["Peças entregues na revisão anterior", "O fornecedor produziu pelo desenho antigo", "O fornecedor não recebeu a nova revisão",
         "O aviso de mudança foi só para as áreas internas da fábrica", "O processo de mudança de engenharia não exige confirmação do fornecedor"]),
    "Incorrect stacking or handling": (
        ["Parts damaged on arrival", "Boxes were crushed at the bottom of the pallet", "Pallets were stacked above the allowed height",
         "Stacking limits are not printed on the packaging", "Handling instructions were not agreed with the logistics provider"],
        ["Peças danificadas na chegada", "As caixas da base do palete foram esmagadas", "Os paletes foram empilhados acima da altura permitida",
         "Os limites de empilhamento não estão impressos na embalagem", "As instruções de manuseio não foram acordadas com o operador logístico"]),
}

WHYS.update({
    "Gauge or measurement method not validated": (
        ["Parts released by the supplier were rejected at our dimensional check", "The supplier's gauge read the parts as good", "The gauge and our measuring method gave different results",
         "No measurement system analysis (Gage R&R) was done at the supplier", "Gauge validation is not a release requirement for new parts"],
        ["Peças liberadas pelo fornecedor foram reprovadas na nossa medição dimensional", "O calibrador do fornecedor indicava peça boa", "O calibrador e o nosso método de medição deram resultados diferentes",
         "Não foi feita análise do sistema de medição (Gage R&R) no fornecedor", "A validação do calibrador não é requisito de liberação para peças novas"]),
    "Process parameters not frozen after launch": (
        ["Dimensions drift from lot to lot", "The supplier keeps adjusting the process", "There is no approved parameter window",
         "Parameters from the PPAP run were not recorded", "Process parameters were not frozen and documented after launch"],
        ["As dimensões variam de lote para lote", "O fornecedor segue ajustando o processo", "Não existe janela de parâmetros aprovada",
         "Os parâmetros da corrida de PPAP não foram registrados", "Os parâmetros de processo não foram congelados e documentados após o lançamento"]),
    "Packaging without corrosion inhibitor": (
        ["Metal parts arrived with corrosion", "The parts had no protective oil or VCI film", "The packaging specification does not require corrosion protection",
         "The specification was written for short domestic transit", "Corrosion protection was not considered for the sea route"],
        ["Peças metálicas chegaram com corrosão", "As peças não tinham óleo protetivo nem filme VCI", "A especificação de embalagem não exige proteção contra corrosão",
         "A especificação foi escrita para trânsito doméstico curto", "A proteção contra corrosão não foi prevista para a rota marítima"]),
    "Old drawing used at the supplier": (
        ["Parts produced at the previous revision", "The operator used a printed drawing from the workstation", "The old printout was never removed",
         "There is no control of obsolete documents at the supplier", "The supplier's document control does not withdraw superseded drawings"],
        ["Peças produzidas na revisão anterior", "O operador usou um desenho impresso do posto", "A cópia antiga nunca foi recolhida",
         "Não há controle de documentos obsoletos no fornecedor", "O controle de documentos do fornecedor não recolhe desenhos superados"]),
    "Label and document template not standardized": (
        ["Shipment arrived with wrong or missing labels", "Each shipment used a different label layout", "The supplier has no label template agreed with the plant",
         "Labeling requirements were sent only as text in the purchase order", "The labeling standard was never formalized with the supplier"],
        ["Remessa chegou com etiqueta errada ou faltando", "Cada remessa usou um layout de etiqueta diferente", "O fornecedor não tem modelo de etiqueta acordado com a fábrica",
         "Os requisitos de etiqueta foram enviados só como texto no pedido", "O padrão de etiquetagem nunca foi formalizado com o fornecedor"]),
    "Manual labeling error": (
        ["Labels did not match the parts in the box", "The label was printed and applied by hand", "Two part numbers are packed at the same station",
         "There is no scan check between part and label", "The labeling step is not error-proofed"],
        ["A etiqueta não correspondia às peças da caixa", "A etiqueta foi impressa e colada à mão", "Dois part numbers são embalados no mesmo posto",
         "Não há leitura que confira peça e etiqueta", "A etapa de etiquetagem não é à prova de erro"]),
    "Defective sub-component from a sub-supplier": (
        ["Modules failed the functional test", "An internal sub-component was defective", "The sub-supplier shipped a bad lot",
         "The supplier does not check incoming sub-components", "The supplier's control of its own sub-suppliers is weak"],
        ["Módulos reprovaram no teste funcional", "Um subcomponente interno estava defeituoso", "O subfornecedor enviou um lote ruim",
         "O fornecedor não inspeciona os subcomponentes que recebe", "O controle do fornecedor sobre os próprios subfornecedores é fraco"]),
    "Test station out of calibration": (
        ["Defective units passed the supplier's end-of-line test", "The test station accepted out-of-limit values", "The station was out of calibration",
         "The calibration interval expired without action", "There is no calibration tracking system for test equipment"],
        ["Unidades defeituosas passaram no teste final do fornecedor", "A bancada aceitou valores fora do limite", "A bancada estava fora de calibração",
         "O intervalo de calibração venceu sem ação", "Não há sistema de controle de calibração dos equipamentos de teste"]),
    "Operator not trained on the appearance standard": (
        ["Parts with visible defects were shipped", "The inspector did not consider them defects", "There is no shared appearance standard",
         "No boundary samples at the inspection station", "Inspectors were not trained on the customer's appearance standard"],
        ["Peças com defeitos visíveis foram enviadas", "O inspetor não as considerou defeituosas", "Não há padrão de aparência compartilhado",
         "Não existem amostras-limite no posto de inspeção", "Os inspetores não foram treinados no padrão de aparência do cliente"]),
    "PPAP checklist not followed": (
        ["Parts arrived without complete PPAP documents", "The submission missed required elements", "The supplier did not use the PPAP checklist",
         "The checklist was not part of the supplier kickoff", "The PPAP requirements were not explained at the start of the project"],
        ["Peças chegaram sem a documentação completa de PPAP", "A submissão deixou de fora elementos obrigatórios", "O fornecedor não usou o checklist de PPAP",
         "O checklist não fez parte da reunião de início com o fornecedor", "Os requisitos de PPAP não foram explicados no início do projeto"]),
    "New supplier unfamiliar with PPAP requirements": (
        ["PPAP rejected for missing or wrong elements", "The supplier did not know what each element requires", "It is the supplier's first automotive customer",
         "No PPAP training was offered during development", "Supplier development does not include PPAP onboarding"],
        ["PPAP reprovado por elementos ausentes ou errados", "O fornecedor não sabia o que cada elemento exige", "É o primeiro cliente automotivo do fornecedor",
         "Não houve treinamento de PPAP no desenvolvimento", "O desenvolvimento de fornecedores não inclui integração em PPAP"]),
    "Welding parameters drifting": (
        ["Weld joints failed the destructive test", "Weld penetration was insufficient", "Current and wire speed drifted during the shift",
         "Parameters are not monitored in real time", "The welding process has no parameter monitoring or alarm"],
        ["Soldas reprovaram no ensaio destrutivo", "A penetração da solda foi insuficiente", "Corrente e velocidade do arame variaram no turno",
         "Os parâmetros não são monitorados em tempo real", "O processo de solda não tem monitoramento nem alarme de parâmetros"]),
    "Welder qualification not verified": (
        ["Inconsistent weld quality between shifts", "Some welders produce more defects", "Not every welder is qualified for this joint",
         "Qualification records were not checked before production", "Welder qualification is not verified in the process audit"],
        ["Qualidade de solda diferente entre turnos", "Alguns soldadores geram mais defeitos", "Nem todo soldador é qualificado para esta junta",
         "Os registros de qualificação não foram conferidos antes da produção", "A qualificação dos soldadores não é verificada na auditoria de processo"]),
    "Engineering change not communicated to the supplier": WHYS["Engineering change not communicated to the supplier"],
})


def build(edition, cutoff, lang, outdir, png=True):
    sup, R, I, P, A = sq.view(cutoff); I = sq.root_cause(I)
    CUR = cutoff.strftime("%Y-%m"); dim = calendar.monthrange(cutoff.year, cutoff.month)[1]; mtd = cutoff.day < dim
    per = pd.Period(CUR, "M"); PREV = str(per - 1); M6 = [str(per - i) for i in range(5, -1, -1)]; M12 = [str(per - i) for i in range(11, -1, -1)]
    mname = lambda m: MON[lang][int(m[5:]) - 1]
    I["m"] = I.data_abertura.dt.to_period("M").astype(str); I["mc"] = I.data_encerramento_8d.dt.to_period("M").astype(str)
    I["dias"] = (I.data_encerramento_8d - I.data_abertura).dt.days
    names = sup.set_index("id_fornecedor").fornecedor
    c_end = pd.Timestamp(cutoff) + pd.Timedelta(hours=23, minutes=59)

    cur, prev = I[I.m == CUR], I[I.m == PREV]
    closed_m = I[I.mc == CUR]; open_ = I[I.status == "Open"]
    W = I[I.m.isin(M6)]                       # last six months: enough cases for Pareto and root cause
    WC = W[W.status == "Closed"]
    par = W.defeito.value_counts().head(6)
    six = WC.categoria_6m.value_counts().reindex(SIXM).fillna(0).astype(int)
    causes = WC.causa_raiz.value_counts()
    top_def = par.index[0]
    top_cat = six.idxmax(); top_cat_share = six.max() / max(six.sum(), 1) * 100
    causes = WC[WC.categoria_6m == top_cat].causa_raiz.value_counts(); top_cause = causes.index[0]   # Five Whys on the top cause of the top category
    src = W.deteccao.value_counts(); esc = (W.deteccao != "Incoming inspection").mean() * 100
    # suppliers with most non-conformances
    TS = W.groupby("id_fornecedor").agg(n=("id_problema", "size"), ab=("status", lambda s: (s == "Open").sum())).sort_values(["n", "ab"], ascending=False).head(5)
    TS["defeito"] = [W[W.id_fornecedor == i].defeito.value_counts().index[0] for i in TS.index]
    TS["causa"] = [(WC[WC.id_fornecedor == i].categoria_6m.value_counts().index[0] if (WC.id_fornecedor == i).any() else "Under investigation") for i in TS.index]

    # ---------- charts ----------
    g = I[I.m.isin(M12)].groupby(["m", "origem"]).size().unstack(fill_value=0).reindex(M12).fillna(0)
    f, ax = plt.subplots(figsize=(4.2, 1.45)); f.subplots_adjust(left=.07, right=.99, top=.84, bottom=.15)
    x = np.arange(12); base = np.zeros(12); cols = {"CN": C["cat"][2], "BR": C["sage500"], "OT": C["context"]}
    for o in ("CN", "BR", "OT"):
        if o in g: ax.bar(x, g[o].values, bottom=base, color=cols[o], width=.7, label=ORG[o][0 if lang == "en" else 1]); base += g[o].values
    for i_, v in enumerate(base): ax.text(i_, v + .6, str(int(v)), ha="center", fontsize=6, color=C["ink"] if i_ == 11 else C["ink3"])
    rows_grid(ax); ax.set_xticks(x, [mname(m) for m in M12], fontsize=6.2); ax.tick_params(labelsize=6.2); ax.set_ylim(0, base.max() * 1.2)
    ax.legend(frameon=False, fontsize=6.2, ncol=3, loc="upper left", bbox_to_anchor=(0, 1.25), handlelength=1); c_trend = svg(f)

    mx = par.max(); n6 = len(W)
    pareto = "".join(f'<div class="pr"><span>{DEF(k, lang)}</span><div class="hb"><span style="width:{v / mx * 100:.0f}%"></span></div><b>{v}</b><em>{pct(v / n6 * 100, 0, lang)}</em></div>' for k, v in par.items())
    m6 = max(six.max(), 1); nwc = max(six.sum(), 1)
    sixm = "".join(f'<div class="pr"><span>{T(lang, k, sq.CAUSE_PT[k])}</span><div class="hb"><span style="width:{v / m6 * 100:.0f}%;{"background:#9B3434" if k == top_cat else ""}"></span></div><b>{v}</b><em>{pct(v / nwc * 100, 0, lang)}</em></div>' for k, v in six.items())
    srcb = "".join(f'<div class="lg"><i style="background:{c}"></i>{SRC[k][0 if lang == "en" else 1]}<b>{pct(src.get(k, 0) / n6 * 100, 0, lang)}</b></div>'
                   for k, c in (("Incoming inspection", C["forest700"]), ("Assembly line", C["signal"]), ("Field", C["bad"])))
    srcbar = "".join(f'<span style="width:{src.get(k, 0) / n6 * 100:.2f}%;background:{c}"></span>' for k, c in (("Incoming inspection", C["forest700"]), ("Assembly line", C["signal"]), ("Field", C["bad"])))

    chain = WHYS.get(top_cause)
    if chain:
        steps = chain[0 if lang == "en" else 1]
    else:
        steps = [DEF(top_def, lang), "–", "–", "–", CAU(top_cause, lang)]
    whys = "".join(f'<li><span class="w">{T(lang, "Why", "Por quê") + " " + str(i + 1) if i < len(steps) - 2 else T(lang, "Root cause", "Causa raiz")}</span><span>{s}</span></li>' for i, s in enumerate(steps[1:]))
    n_cause = int(causes.iloc[0])

    tsr = "".join(f'<tr><td>{names[i]}<div class="sub">{ORG_S[sup.set_index("id_fornecedor").origem[i]][0 if lang == "en" else 1]}</div></td><td>{int(r.n)}</td><td>{int(r.ab)}</td>'
                  f'<td style="text-align:left">{SHORT.get(r.defeito, (r.defeito, r.defeito))[0 if lang == "en" else 1]}</td><td style="text-align:left">{T(lang, r.causa, sq.CAUSE_PT.get(r.causa, "Em investigação"))}</td></tr>' for i, r in TS.iterrows())

    # ---------- text ----------
    up = len(cur) > len(prev)
    headline = T(lang,
        f"{len(cur)} supplier non-conformances in {MONTHS['en'][cutoff.month-1]}, {'up' if up else 'down'} from {len(prev)}; {DEF(top_def, lang).lower()} leads, and the {top_cat} category explains {pct(top_cat_share, 0, lang)} of the root causes found",
        f"{len(cur)} não conformidades em {MONTHS['pt'][cutoff.month-1]} ({len(prev)} em {MONTHS['pt'][(cutoff.month-2) % 12]}); {DEF(top_def, lang).lower()} lidera e {sq.CAUSE_PT[top_cat]} explica {pct(top_cat_share, 0, lang)} das causas raiz")
    ACT = {"Method": (["Standardize the procedure behind the cause (work instruction, checklist or packaging specification) and train the supplier on it.",
                       "Add the check to the supplier's control plan and to the next process audit."],
                      ["Padronizar o procedimento por trás da causa (instrução de trabalho, checklist ou especificação de embalagem) e treinar o fornecedor.",
                       "Incluir a verificação no plano de controle do fornecedor e na próxima auditoria de processo."]),
           "Machine": (["Preventive maintenance plan for the tooling and equipment involved, with wear limits.", "Monitor the key process parameter with a simple control chart at the supplier."],
                       ["Plano de manutenção preventiva do ferramental e dos equipamentos envolvidos, com limites de desgaste.", "Acompanhar o parâmetro-chave do processo com um gráfico de controle simples no fornecedor."]),
           "Man": (["Training and skill check for the operators involved, with a visual standard at the workstation.", "Error-proofing (poka-yoke) where the step depends on attention."],
                   ["Treinamento e verificação de habilidade dos operadores envolvidos, com padrão visual no posto.", "À prova de erro (poka-yoke) onde a etapa depende de atenção."]),
           "Environment": (["Humidity protection for sea freight: desiccant, humidity indicator and sealed packaging.", "Monitor corrosion by route and season to confirm the effect."],
                           ["Proteção contra umidade no frete marítimo: dessecante, indicador de umidade e embalagem selada.", "Acompanhar a corrosão por rota e estação para confirmar o efeito."]),
           "Material": (["Require incoming certificates and sample tests from the sub-supplier.", "Add the sub-supplier to the supplier's own audit plan."],
                        ["Exigir certificados e testes por amostragem do subfornecedor.", "Incluir o subfornecedor no plano de auditoria do próprio fornecedor."]),
           "Measurement": (["Validate gauges and measurement methods (MSA) before releasing parts.", "Calibrate and label every gauge used in final inspection."],
                           ["Validar calibradores e métodos de medição (MSA) antes de liberar peças.", "Calibrar e identificar todo calibrador usado na inspeção final."])}
    acts = ACT[top_cat][0 if lang == "en" else 1]
    A_ = [T(lang, f"<b>Correct</b> ({CAU(top_cause, lang).lower()}): {acts[0]}", f"<b>Corrigir</b> ({CAU(top_cause, lang).lower()}): {acts[0]}"),
          T(lang, f"<b>Prevent:</b> {acts[1]}", f"<b>Prevenir:</b> {acts[1]}"),
          T(lang, f"<b>Close the open cases:</b> {len(open_)} non-conformances are under investigation; root cause (D4) within 15 days for each.",
            f"<b>Fechar os casos abertos:</b> {len(open_)} não conformidades em investigação; causa raiz (D4) em até 15 dias para cada uma."),
          T(lang, f"<b>Catch earlier:</b> {pct(esc, 0, lang)} of non-conformances were found on the line or by the customer; reinforce incoming inspection for the suppliers in the table.",
            f"<b>Detectar antes:</b> {pct(esc, 0, lang)} foram achadas na linha ou no cliente; reforçar a inspeção de recebimento dos fornecedores da tabela.")]
    ac = "".join(f'<li><i class="n">{i + 1}</i><span>{t}</span></li>' for i, t in enumerate(A_))

    EXTRA = """
.lead { font-size: 8.5pt; line-height:1.42; }
.hb { background:#E7E2D9; height:2.4mm; border-radius:.4mm; overflow:hidden; } .hb span { display:block; height:100%; background:#06402B; }
.pr { display:grid; grid-template-columns: 47% 1fr 6mm 9mm; align-items:center; gap:1.6mm; font-size:7.1pt; margin-bottom:.8mm; }
.pr b { font-weight:500; text-align:right; } .pr em { font-style:normal; text-align:right; color:#4F615A; font-family:'IBM Plex Mono',monospace; font-size:6.4pt; }
.stk { display:flex; height:4mm; border-radius:.5mm; overflow:hidden; margin:1.2mm 0 1.6mm; } .stk span { display:block; height:100%; }
.lgs { display:grid; grid-template-columns:1fr; gap:.8mm; font-size:7pt; color:#4F615A; }
.lg { display:flex; align-items:center; gap:1.4mm; } .lg i { width:2mm; height:2mm; display:inline-block; flex:none; } .lg b { margin-left:auto; font-weight:500; color:#2B2F2E; }
ol.why { list-style:none; margin:1mm 0 0; padding:0; font-size:7.4pt; line-height:1.38; } ol.why li { display:grid; grid-template-columns:14mm 1fr; gap:2mm; padding:.7mm 0; border-bottom:1px solid #E7E2D9; }
ol.why .w { font-family:'IBM Plex Mono',monospace; font-size:6.2pt; letter-spacing:.06em; text-transform:uppercase; color:#4F615A; padding-top:.3mm; }
ol.why li:last-child { border-bottom:none; } ol.why li:last-child span:last-child { font-weight:500; color:#9B3434; }
.prob { background:#F3DEDC; border-radius:.6mm; padding:1.6mm 2mm; font-size:7.6pt; margin-top:1mm; } .prob b { font-weight:500; }
table.t td .sub { font-size:6.1pt; color:#4F615A; margin-top:.2mm; }
ul.pc { list-style:none; margin:0; padding:0; font-size:7.5pt; line-height:1.42; } ul.pc li { display:flex; gap:2mm; margin-bottom:1.3mm; }
ul.pc i.n { flex:none; width:4mm; height:4mm; margin-top:.2mm; background:#06402B; color:#FBF9F4; font-style:normal; font-family:'IBM Plex Mono',monospace; font-size:6.5pt; display:flex; align-items:center; justify-content:center; border-radius:.5mm; }
.syn { display:inline-block; font-family:'IBM Plex Mono',monospace; font-weight:500; font-size:6pt; letter-spacing:.08em; text-transform:uppercase; color:#795300; background:transparent; border:1px solid #795300; padding:.4mm 1.4mm; border-radius:1mm; margin-top:2.5mm; }
.page { gap: 2.2mm; padding-top: 7.5mm; padding-bottom: 6mm; } .kpi { padding: 2.2mm 3mm; } .kpi .v { font-size: 15pt; } .card { padding: 2.3mm 3mm; } .sec { margin-bottom: 1.2mm; } .hdr { padding: 4mm 6mm 4.5mm; } .hdr h1 { font-size: 14.5pt; }
"""
    month_title = T(lang, f"{MONTHS['en'][cutoff.month-1]} {cutoff.year}", f"{MONTHS['pt'][cutoff.month-1].capitalize()} de {cutoff.year}")
    span = T(lang, f"1–{cutoff.day} {MON['en'][cutoff.month-1]}" if mtd else "Full month", f"1 a {cutoff.day}/{cutoff.month:02d}" if mtd else "Mês fechado")
    w6 = f"{mname(M6[0])}–{mname(CUR)}"
    avg_days = closed_m.dias.mean() if len(closed_m) else np.nan
    body = f"""<style>{EXTRA}</style>
<div class="hdr"><div class="grid"></div><div class="in"><div>
<div class="eyebrow"><span class="node"></span>{T(lang, 'Supplier non-conformance report · EV assembly plant · Brazil', 'Não conformidades de fornecedores · Montadora de VE · Brasil')}</div>
<h1>{headline}</h1>
<span class="syn">{T(lang, 'SYNTHETIC DATA · FICTITIOUS PLANT WITH A CHINESE PARENT', 'DADOS SINTÉTICOS · MONTADORA FICTÍCIA DE CONTROLE CHINÊS')}</span></div>
<div class="side"><div class="sm">{T(lang, 'Reporting month', 'Mês de referência')}</div><div class="big">{month_title}</div><div class="sm" style="margin-top:2mm">{T(lang, 'Period', 'Período')}</div><div class="big" style="font-size:9pt">{span} · {T(lang, 'edition', 'edição')} {edition_label(edition, lang)}</div></div></div></div>
<p class="lead">{T(lang, f"A non-conformance is a part that does not meet the requirement: wrong dimension, damage, missing document. This page counts them, shows which defects repeat, and uses the 6M method (Ishikawa) and the Five Whys to find the cause behind them. Pareto and root causes use the last six months ({w6}); root causes come only from closed cases.",
    f"Não conformidade é a peça fora do requisito: dimensão, dano, documento. A página conta as ocorrências, mostra os defeitos que se repetem e usa os 6M (Ishikawa) e os 5 Porquês para achar a causa. Pareto e causas usam os últimos seis meses ({w6}); a causa vem só dos casos encerrados.")}</p>
<div class="kpis" style="grid-template-columns:repeat(4,1fr)">
<div class="kpi inv"><div class="lb">{T(lang, 'Non-conformances opened', 'Não conformidades abertas')}</div><div class="v">{len(cur)}</div><div class="d">{mname(PREV)} {len(prev)} · {T(lang, 'six-month average', 'média de seis meses')} {num(len(W) / 6, 0, lang)}</div></div>
<div class="kpi"><div class="lb">{T(lang, 'Closed in the month', 'Encerradas no mês')}</div><div class="v">{len(closed_m)}</div><div class="d">{T(lang, 'average', 'média de')} {num(avg_days, 0, lang)} {T(lang, 'days to close', 'dias para encerrar')} · {len(open_)} {T(lang, 'still open', 'em aberto')}</div></div>
<div class="kpi"><div class="lb">{T(lang, 'Top defect', 'Defeito mais frequente')}</div><div class="v" style="font-size:10.5pt;line-height:1.2">{DEF(top_def, lang)}</div><div class="d">{par.iloc[0]} {T(lang, 'cases', 'casos')} · {pct(par.iloc[0] / n6 * 100, 0, lang)} {T(lang, 'of the total', 'do total')}</div></div>
<div class="kpi"><div class="lb">{T(lang, 'Top root cause (6M)', 'Causa raiz principal (6M)')}</div><div class="v bad" style="font-size:13pt">{T(lang, top_cat, sq.CAUSE_PT[top_cat])}</div><div class="d">{pct(top_cat_share, 0, lang)} {T(lang, 'of closed cases', 'dos casos encerrados')}</div></div>
</div>
<div style="display:grid;grid-template-columns:1.6fr 1fr;gap:4mm">
<div><div class="sec"><span class="no">01</span><h2>{T(lang, 'Non-conformances by month', 'Não conformidades por mês')}</h2><span class="r">12 {T(lang, 'months', 'meses')}</span></div>
<div class="card">{c_trend}</div></div>
<div><div class="sec"><span class="no">02</span><h2>{T(lang, 'Where they were found', 'Onde foram detectadas')}</h2><span class="r">{w6}</span></div>
<div class="card"><div class="stk">{srcbar}</div><div class="lgs">{srcb}</div><p class="cs" style="margin:1.6mm 0 0">{T(lang, 'The later a defect is found, the more it costs: on the line it stops production, at the customer it becomes a warranty case.', 'Quanto mais tarde o defeito aparece, mais caro: na linha ele para a produção, no cliente vira garantia.')}</p></div></div>
</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:4mm">
<div><div class="sec"><span class="no">03</span><h2>{T(lang, 'Which defects repeat (Pareto)', 'Quais defeitos se repetem (Pareto)')}</h2><span class="r">{n6} {T(lang, 'cases', 'casos')}</span></div>
<div class="card">{pareto}</div></div>
<div><div class="sec"><span class="no">04</span><h2>{T(lang, 'Root cause by 6M (Ishikawa)', 'Causa raiz pelos 6M (Ishikawa)')}</h2><span class="r">{int(six.sum())} {T(lang, 'closed', 'encerrados')}</span></div>
<div class="card">{sixm}</div></div>
</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:4mm">
<div><div class="sec"><span class="no">05</span><h2>{T(lang, 'Five Whys: top cause in ' + top_cat, '5 Porquês: causa principal em ' + sq.CAUSE_PT[top_cat])}</h2><span class="r">{n_cause} {T(lang, 'cases', 'casos')}</span></div>
<div class="card"><div class="prob"><b>{T(lang, 'Problem', 'Problema')}:</b> {steps[0]}</div><ol class="why">{whys}</ol></div></div>
<div><div class="sec"><span class="no">06</span><h2>{T(lang, 'Suppliers with most cases', 'Fornecedores com mais casos')}</h2><span class="r">{w6}</span></div>
<table class="t"><tr><th>{T(lang, 'Supplier', 'Fornecedor')}</th><th>{T(lang, 'Cases', 'Casos')}</th><th>{T(lang, 'Open', 'Abertos')}</th><th style="text-align:left">{T(lang, 'Main defect', 'Defeito principal')}</th><th style="text-align:left">6M</th></tr>{tsr}</table></div>
</div>
<div><div class="sec"><span class="no">07</span><h2>{T(lang, 'Actions for ', 'Ações para ')}{MONTHS[lang][cutoff.month % 12]}</h2><span class="r">{T(lang, f'Driven by the top cause: {top_cat}', f'Guiadas pela causa principal: {sq.CAUSE_PT[top_cat]}')}</span></div>
<div class="card"><ul class="pc" style="columns:2;column-gap:5mm;display:block">{''.join(f'<li style="break-inside:avoid"><i class="n">{i + 1}</i><span>{t}</span></li>' for i, t in enumerate(A_))}</ul></div></div>
{footer(T(lang, "Synthetic data for a fictitious EV assembler in Brazil with a Chinese parent company; plant, suppliers and cases are invented. Root cause categories follow the 6M method (Method, Machine, Man, Material, Measurement, Environment); the Five Whys chain is an illustrative example for the top cause of the leading 6M category. Same dataset as the Monthly Supplier Quality Report.",
          "Dados sintéticos de uma montadora fictícia de veículos elétricos no Brasil com controle chinês; planta, fornecedores e casos são inventados. As categorias de causa raiz seguem o método 6M (Método, Máquina, Mão de obra, Material, Medição, Meio ambiente); a cadeia de 5 Porquês é um exemplo ilustrativo da causa principal da categoria 6M líder. Mesma base do Relatório Mensal de Qualidade de Fornecedores."))}
"""
    name = T(lang, "Supplier_Non_Conformance_Report", "Relatorio_Nao_Conformidades_Fornecedores") + f"_{CUR}"
    html = os.path.join(outdir, name + ".html")
    h, lvl = render_fit(body, T(lang, "Supplier Non-Conformance Report", "Relatório de Não Conformidades de Fornecedores") + f" · {month_title}", lang,
                        html, os.path.join(outdir, name + ".pdf"), os.path.join(outdir, name + ".png") if png else None)
    return dict(name=name, height=h, fit_level=lvl, headline=headline, ncs=len(cur), top_defect=top_def, top_cause=top_cause, top_6m=top_cat)
