"""
Gera as bases SINTÉTICAS do portfólio (compras de materiais diretos aeroespaciais).
Nenhum dado é da Embraer: nomes, códigos e valores são fictícios e gerados com semente fixa.
Os preços seguem os índices públicos reais (BLS PPI) e o câmbio real (BCB PTAX),
salvos em dados/publicos/, para que as análises de variação de preço façam sentido.
"""
import numpy as np, pandas as pd, random, os, json
from datetime import date, timedelta

rng = np.random.default_rng(42); random.seed(42)
BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "dados", "sinteticos"); os.makedirs(OUT, exist_ok=True)
ppi = pd.read_csv(os.path.join(BASE, "dados", "publicos", "bls_ppi_aeroespacial_metais_mensal.csv"))
fx = pd.read_csv(os.path.join(BASE, "dados", "publicos", "bcb_cambio_ipca_mensal.csv"))

# ---------- Fornecedores ----------
categorias = {  # categoria: (índice PPI que rege o preço, peso no spend)
    "Propulsão": ("ppi_motores_aeronauticos_PCU336412", 0.34),
    "Aviônica": ("ppi_avionica_navegacao_PCU334511", 0.26),
    "Estruturas e usinados": ("ppi_pecas_aeronauticas_PCU336413", 0.18),
    "Trem de pouso e hidráulica": ("ppi_pecas_aeronauticas_PCU336413", 0.12),
    "Elétrica e chicotes": ("ppi_pecas_aeronauticas_PCU336413", 0.06),
    "Matéria-prima metálica": ("ppi_aco_laminados_WPU1017", 0.04),
}
paises = [("Estados Unidos", "USD", 0.46), ("França", "EUR", 0.14), ("Canadá", "USD", 0.08), ("Alemanha", "EUR", 0.07),
          ("Brasil", "BRL", 0.09), ("Portugal", "EUR", 0.05), ("Reino Unido", "USD", 0.04), ("México", "USD", 0.04), ("Itália", "EUR", 0.03)]
prefixos = ["Aero", "Avio", "Sky", "Jet", "Turbo", "Prime", "Atlas", "Nova", "Vector", "Orbit", "Delta", "Apex", "Falcon", "Zenith", "Polar", "Helix", "Strato", "Titan", "Aurora", "Cirrus"]
sufixos = ["Dynamics", "Systems", "Components", "Precision", "Technologies", "Industries", "Aerospace", "Controls", "Machining", "Avionics"]
nomes = random.sample([f"{p} {s}" for p in prefixos for s in sufixos], 200)
forn = []
for i, n in enumerate(nomes):
    cat = rng.choice(list(categorias), p=[v[1] for v in categorias.values()])
    pi = rng.choice(len(paises), p=[p[2] for p in paises]); pais, moeda, _ = paises[pi]
    tier = rng.choice(["Estratégico", "Preferencial", "Aprovado", "Em desenvolvimento"], p=[0.12, 0.28, 0.5, 0.10])
    forn.append(dict(id_fornecedor=f"F{1000+i}", fornecedor=n + (" Ltda" if pais == "Brasil" else " Inc" if moeda == "USD" else " SA"),
        pais=pais, moeda=moeda, categoria=cat, segmentacao=tier,
        certificacao_as9100=rng.choice(["Sim", "Sim", "Sim", "Sim", "Vencida", "Não"]),
        lead_time_contratual_dias=int(rng.choice([30, 45, 60, 90, 120, 180], p=[.1, .2, .3, .2, .12, .08])),
        prazo_pagamento_dias=int(rng.choice([30, 45, 60, 90], p=[.25, .25, .35, .15])),
        otd_base=float(np.clip(rng.normal(0.88, 0.07), 0.6, 0.995)), ppm_base=float(rng.gamma(2, 900))))
F = pd.DataFrame(forn)

# ---------- Materiais (part numbers) ----------
mats = []
desc = {"Propulsão": ["Pá de turbina", "Selo de compressor", "Bico injetor", "Rolamento principal", "Sensor de EGT", "Kit de reparo de combustor"],
        "Aviônica": ["Display multifunção", "Unidade de dados de ar", "Antena VHF", "Placa de controle FMS", "Transponder", "Giroscópio MEMS"],
        "Estruturas e usinados": ["Nervura usinada", "Longarina", "Suporte em titânio", "Painel de acesso", "Fitting de asa", "Bucha de bronze"],
        "Trem de pouso e hidráulica": ["Atuador hidráulico", "Amortecedor", "Válvula seletora", "Freio de carbono", "Mangueira de alta pressão", "Roda do trem principal"],
        "Elétrica e chicotes": ["Chicote elétrico", "Conector circular", "Relé de potência", "Disjuntor", "Gerador de partida", "Painel de iluminação"],
        "Matéria-prima metálica": ["Chapa de alumínio 7075", "Barra de titânio Ti-6Al-4V", "Tarugo de aço 4340", "Perfil extrudado 2024", "Chapa de Inconel 718", "Barra de aço 17-4PH"]}
faixa = {"Propulsão": (800, 90000), "Aviônica": (1500, 120000), "Estruturas e usinados": (150, 25000),
         "Trem de pouso e hidráulica": (600, 80000), "Elétrica e chicotes": (40, 15000), "Matéria-prima metálica": (80, 6000)}
for i in range(650):
    cat = rng.choice(list(categorias), p=[v[1] for v in categorias.values()])
    lo, hi = faixa[cat]
    preco = float(np.exp(rng.uniform(np.log(lo), np.log(hi))))
    cand = F[F.categoria == cat]
    nfont = int(rng.choice([1, 2, 3], p=[0.38, 0.42, 0.20]))
    fs = cand.sample(min(nfont, len(cand)), random_state=int(rng.integers(1e9))).id_fornecedor.tolist()
    mats.append(dict(part_number=f"PN-{rng.integers(10,99)}{chr(65+i%26)}{1000+i}", descricao=rng.choice(desc[cat]) + f" {chr(65+i%26)}{i%50}",
        categoria=cat, ncm=("8411.99.00" if cat == "Propulsão" else "8807.30.00" if cat in ("Estruturas e usinados", "Trem de pouso e hidráulica") else "8526.91.00" if cat == "Aviônica" else "8544.42.00" if cat == "Elétrica e chicotes" else "7606.12.90"),
        eccn=rng.choice(["EAR99", "9A991", "9A610", "7A994"], p=[.45, .3, .1, .15]),
        preco_base_usd_2024=round(preco, 2), fonte_unica="Sim" if len(fs) == 1 else "Não",
        fornecedores_aprovados=";".join(fs), item_critico=rng.choice(["Sim", "Não"], p=[.25, .75])))
M = pd.DataFrame(mats)
M['peso'] = rng.lognormal(0, 1.6, len(M)); M['peso'] /= M.peso.sum()
forn_peso = dict(zip(F.id_fornecedor, rng.lognormal(0, 1.2, len(F))))

# ---------- Pedidos de compra (jan/2024 a set/2026) ----------
meses = pd.period_range("2024-01", "2026-09", freq="M")
ppi_i = ppi.set_index("mes"); fx_i = fx.set_index("mes")
linhas = []; po = 4500000000
for mes in meses:
    sazonal = 1 + 0.12 * np.sin((mes.month - 3) / 12 * 2 * np.pi)
    n = int(rng.poisson(330 * sazonal * (1.06 if mes.year == 2025 else 1.1 if mes.year == 2026 else 1)))
    for _ in range(n):
        m = M.iloc[int(rng.choice(len(M), p=M.peso))]
        opc = m.fornecedores_aprovados.split(";"); w = np.array([forn_peso[x] for x in opc]); fid = opc[int(rng.choice(len(opc), p=w / w.sum()))]; f = F.set_index("id_fornecedor").loc[fid]
        col = categorias[m.categoria][0]
        idx = ppi_i.loc[str(mes), col] / ppi_i.loc["2024-01", col]
        preco_usd = m.preco_base_usd_2024 * idx * rng.normal(1, 0.03)
        qtd = int(1 + rng.poisson(1 if m.preco_base_usd_2024 > 20000 else 5))
        data_po = date(mes.year, mes.month, int(rng.integers(1, 28)))
        prometida = data_po + timedelta(days=int(f.lead_time_contratual_dias))
        atraso = 0 if rng.random() < f.otd_base else int(rng.gamma(2, 9)) + 1
        recebida = prometida + timedelta(days=atraso - int(rng.integers(0, 6)) if atraso == 0 else atraso)
        moeda = f.moeda
        taxa = {"USD": 1.0, "EUR": fx_i.loc[str(mes), "usd_brl_ptax_media"] / fx_i.loc[str(mes), "eur_brl_ptax_media"],
                "BRL": fx_i.loc[str(mes), "usd_brl_ptax_media"]}[moeda]
        preco_moeda = preco_usd * taxa
        po += 1
        linhas.append(dict(pedido=po, item=10, data_pedido=data_po.isoformat(), id_fornecedor=fid, part_number=m.part_number,
            categoria=m.categoria, quantidade=qtd, moeda=moeda, preco_unitario_moeda=round(preco_moeda, 2),
            valor_total_moeda=round(preco_moeda * qtd, 2), usd_brl_mes=fx_i.loc[str(mes), "usd_brl_ptax_media"],
            valor_total_usd=round(preco_usd * qtd, 2), incoterm=rng.choice(["FCA", "EXW", "DAP", "CIP"], p=[.5, .2, .2, .1]),
            data_prometida=prometida.isoformat(), data_recebimento=(recebida.isoformat() if recebida <= date(2026, 9, 30) else ""),
            comprador=rng.choice(["Comprador A", "Comprador B", "Comprador C", "Comprador D"])))
P = pd.DataFrame(linhas)

# ---------- RFQs, savings e cost avoidance ----------
rfq = []
for i in range(420):
    m = M.iloc[int(rng.integers(len(M)))]
    data = date(2024, 1, 1) + timedelta(days=int(rng.integers(0, 1000)))
    if data > date(2026, 9, 30): data = date(2026, 9, int(rng.integers(1, 28)))
    historico = rng.random() > 0.22
    novos = int(rng.choice([0, 1, 2], p=[.55, .3, .15])) if m.fonte_unica == "Sim" else int(rng.choice([0, 1], p=[.8, .2]))
    base = m.preco_base_usd_2024 * rng.normal(1.04, 0.03)
    inicial = base * rng.normal(1.04 + (0.02 if novos == 0 else 0), 0.035)
    reducao = rng.normal(0.05, 0.025) + 0.05 * novos
    final = inicial * (1 - max(0.0, reducao))
    vol = int(1 + rng.poisson(12 if m.preco_base_usd_2024 < 20000 else 3))
    if historico:
        tipo = "Savings" if final < base else "Aumento"
        impacto = (base - final) * vol
    else:
        tipo = "Cost avoidance"; impacto = (inicial - final) * vol
    rfq.append(dict(rfq=f"RFQ-{24000+i}", data_abertura=data.isoformat(),
        data_fechamento=(data + timedelta(days=int(rng.integers(5, 40)))).isoformat(),
        part_number=m.part_number, categoria=m.categoria, fonte_unica_antes=m.fonte_unica, item_com_historico="Sim" if historico else "Não",
        fornecedores_convidados=int(rng.integers(2, 6)) + novos, novos_fabricantes_incluidos=novos,
        preco_referencia_usd=round(base, 2) if historico else "", cotacao_inicial_usd=round(inicial, 2), preco_final_usd=round(final, 2),
        volume_anual=vol, tipo_resultado=tipo, impacto_usd=round(impacto, 2),
        validado_finance=rng.choice(["Sim", "Pendente"], p=[.8, .2]) if tipo != "Aumento" else "N/A"))
R = pd.DataFrame(rfq)

# ---------- Notas de qualidade (estilo SAP QM, fictícias) ----------
tipos = [("Q2", "Certificação do fabricante ausente", 0.32), ("Q2", "Reprovação na inspeção de recebimento", 0.30),
         ("Q2", "Revisão de peça superada", 0.16), ("Q2", "Dano no transporte", 0.12), ("Q3", "Divergência de documentação (CoC/FAI)", 0.10)]
nq = []
rec = P[P.data_recebimento != ""].sample(frac=1, random_state=1)
for _, r in rec.iterrows():
    f = F.set_index("id_fornecedor").loc[r.id_fornecedor]
    if rng.random() < min(0.10, f.ppm_base / 45000):
        t = tipos[int(rng.choice(len(tipos), p=[x[2] for x in tipos]))]
        abertura = date.fromisoformat(r.data_recebimento) + timedelta(days=int(rng.integers(0, 4)))
        dias = int(rng.gamma(2.2, 9))
        fech = abertura + timedelta(days=dias)
        nq.append(dict(nota=f"QN{300000+len(nq)}", tipo_nota=t[0], data_abertura=abertura.isoformat(),
            data_encerramento=fech.isoformat() if fech <= date(2026, 9, 30) else "", status="Encerrada" if fech <= date(2026, 9, 30) else "Aberta",
            pedido=r.pedido, id_fornecedor=r.id_fornecedor, part_number=r.part_number, motivo=t[1],
            qtd_rejeitada=int(max(1, round(r.quantidade * rng.uniform(.05, .4)))), qtd_recebida=r.quantidade,
            disposicao=rng.choice(["Devolução ao fornecedor", "Retrabalho pelo fornecedor", "Uso como está (concessão)", "Sucata"], p=[.5, .25, .15, .1]),
            causa_raiz=rng.choice(["Documentação", "Processo do fornecedor", "Embalagem", "Controle de revisão", "Subfornecedor"])))
Q = pd.DataFrame(nq)

# ---------- Due diligence (para o agente no Replit) ----------
dd = []
for _, f in F.iterrows():
    ult = date(2023, 1, 1) + timedelta(days=int(rng.integers(0, 1300)))
    dd.append(dict(id_fornecedor=f.id_fornecedor, fornecedor=f.fornecedor, pais=f.pais, categoria=f.categoria,
        data_ultima_due_diligence=ult.isoformat(), alteracao_cadastral_12m=rng.choice(["Sim", "Não"], p=[.15, .85]),
        alteracao_societaria_12m=rng.choice(["Sim", "Não"], p=[.06, .94]),
        alerta_screening=rng.choice(["Nenhum", "Mídia negativa", "Possível homônimo em lista restritiva", "PEP relacionado"], p=[.86, .07, .04, .03]),
        pais_risco_alto="Não", interage_governo=rng.choice(["Sim", "Não"], p=[.1, .9]),
        gasto_12m_usd=round(float(P[P.id_fornecedor == f.id_fornecedor].pipe(lambda d: d[d.data_pedido >= "2025-10-01"].valor_total_usd.sum())), 2)))
D = pd.DataFrame(dd)

# ---------- Metas mensais ----------
metas = pd.DataFrame([dict(mes=str(m), meta_savings_usd=150000 if m.year == 2024 else 175000 if m.year == 2025 else 190000,
    meta_otd_pct=90, meta_ppm=1500, meta_lead_time_rfq_dias=10) for m in meses])

F.drop(columns=["otd_base", "ppm_base"]).to_csv(os.path.join(OUT, "fornecedores.csv"), index=False)
M.drop(columns=['peso']).to_csv(os.path.join(OUT, "materiais.csv"), index=False)
P.to_csv(os.path.join(OUT, "pedidos_compra.csv"), index=False)
R.to_csv(os.path.join(OUT, "rfqs_savings.csv"), index=False)
Q.to_csv(os.path.join(OUT, "notas_qualidade.csv"), index=False)
D.to_csv(os.path.join(OUT, "due_diligence_fornecedores.csv"), index=False)
metas.to_csv(os.path.join(OUT, "metas_mensais.csv"), index=False)
print({k: len(v) for k, v in dict(fornecedores=F, materiais=M, pedidos=P, rfqs=R, notas=Q, dd=D, metas=metas).items()})
