"""
Estende as bases SINTÉTICAS até 28/10/2026 sem alterar nenhum registro histórico gerado.

1. Reexecuta gerar_dados_sinteticos.py em memória (semente 42) e confere que pedidos,
   RFQs e notas batem com os CSVs salvos.
2. Recebimentos de pedidos abertos cuja data real cai até 28/10/2026 passam a constar.
3. Notas de qualidade abertas que encerram até 28/10/2026 passam a "Encerrada".
4. Gera, com semente própria (20261029), pedidos de 1 a 28/10/2026, notas de qualidade
   sobre os novos recebimentos e RFQs fechadas em outubro.
5. Acrescenta a meta de outubro (mesmos valores de setembro).
Preço: PPI de setembro (último publicado) para outubro. Câmbio: PTAX média de outubro
até a data de corte, lida de dados/publicos/bcb_cambio_ipca_mensal.csv.
"""
import os, numpy as np, pandas as pd
from datetime import date, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
SIN = os.path.join(BASE, "dados", "sinteticos")
CORTE = date(2026, 10, 28)

# ---------- 1. reproduz o gerador em memória ----------
src = open(os.path.join(BASE, "gerar_dados_sinteticos.py"), encoding="utf-8").read()
src = src[:src.index('F.drop(columns=["otd_base", "ppm_base"]).to_csv')]
# guarda as datas reais escondidas (não muda nenhum sorteio)
src = src.replace('comprador=rng.choice(["Comprador A", "Comprador B", "Comprador C", "Comprador D"])))',
                  'comprador=rng.choice(["Comprador A", "Comprador B", "Comprador C", "Comprador D"]), _receb_real=recebida.isoformat()))')
src = src.replace("causa_raiz=rng.choice([\"Documentação\", \"Processo do fornecedor\", \"Embalagem\", \"Controle de revisão\", \"Subfornecedor\"])))",
                  "causa_raiz=rng.choice([\"Documentação\", \"Processo do fornecedor\", \"Embalagem\", \"Controle de revisão\", \"Subfornecedor\"]), _fech_real=fech.isoformat()))")
ns = {"__file__": os.path.join(BASE, "gerar_dados_sinteticos.py")}
exec(compile(src, "gerador", "exec"), ns)
F, M, P0, R0, Q0 = ns["F"], ns["M"], ns["P"], ns["R"], ns["Q"]
categorias, forn_peso = ns["categorias"], ns["forn_peso"]

P = pd.read_csv(os.path.join(SIN, "pedidos_compra.csv"), dtype={"data_recebimento": str}, keep_default_na=False)
R = pd.read_csv(os.path.join(SIN, "rfqs_savings.csv"), keep_default_na=False)
Q = pd.read_csv(os.path.join(SIN, "notas_qualidade.csv"), keep_default_na=False)
assert len(P) == len(P0) and (P.pedido.values == P0.pedido.values).all() and np.allclose(P.valor_total_usd, P0.valor_total_usd), "pedidos divergem do gerador"
assert len(R) == len(R0) and len(Q) == len(Q0), "RFQs ou notas divergem do gerador"

# ---------- 2. recebimentos até o corte ----------
abertos = P.data_recebimento == ""
novos_rec = abertos & (P0._receb_real <= CORTE.isoformat())
P.loc[novos_rec, "data_recebimento"] = P0.loc[novos_rec, "_receb_real"]

# ---------- 3. notas que encerram até o corte ----------
fecha = (Q.status == "Aberta") & (Q0._fech_real <= CORTE.isoformat())
Q.loc[fecha, "data_encerramento"] = Q0.loc[fecha, "_fech_real"]; Q.loc[fecha, "status"] = "Encerrada"

# ---------- 4. outubro com semente própria ----------
rng = np.random.default_rng(20261029)
ppi = pd.read_csv(os.path.join(BASE, "dados", "publicos", "bls_ppi_aeroespacial_metais_mensal.csv")).set_index("mes")
fx = pd.read_csv(os.path.join(BASE, "dados", "publicos", "bcb_cambio_ipca_mensal.csv")).set_index("mes")
assert "2026-10" in fx.index, "falta a PTAX de outubro em bcb_cambio_ipca_mensal.csv"
mes_ppi = "2026-09"  # último PPI publicado
usd, eur = fx.loc["2026-10", "usd_brl_ptax_media"], fx.loc["2026-10", "eur_brl_ptax_media"]
Fi = F.set_index("id_fornecedor")
sazonal = 1 + 0.12 * np.sin((10 - 3) / 12 * 2 * np.pi)
n = int(rng.poisson(330 * sazonal * 1.1 * CORTE.day / 31))
po = int(P.pedido.max()); linhas = []
for _ in range(n):
    m = M.iloc[int(rng.choice(len(M), p=M.peso))]
    opc = m.fornecedores_aprovados.split(";"); w = np.array([forn_peso[x] for x in opc]); fid = opc[int(rng.choice(len(opc), p=w / w.sum()))]; f = Fi.loc[fid]
    col = categorias[m.categoria][0]
    preco_usd = m.preco_base_usd_2024 * ppi.loc[mes_ppi, col] / ppi.loc["2024-01", col] * rng.normal(1, 0.03)
    qtd = int(1 + rng.poisson(1 if m.preco_base_usd_2024 > 20000 else 5))
    data_po = date(2026, 10, int(rng.integers(1, CORTE.day + 1)))
    prometida = data_po + timedelta(days=int(f.lead_time_contratual_dias))
    atraso = 0 if rng.random() < f.otd_base else int(rng.gamma(2, 9)) + 1
    recebida = prometida + timedelta(days=atraso - int(rng.integers(0, 6)) if atraso == 0 else atraso)
    taxa = {"USD": 1.0, "EUR": usd / eur, "BRL": usd}[f.moeda]
    po += 1
    linhas.append(dict(pedido=po, item=10, data_pedido=data_po.isoformat(), id_fornecedor=fid, part_number=m.part_number,
        categoria=m.categoria, quantidade=qtd, moeda=f.moeda, preco_unitario_moeda=round(preco_usd * taxa, 2),
        valor_total_moeda=round(preco_usd * taxa * qtd, 2), usd_brl_mes=usd, valor_total_usd=round(preco_usd * qtd, 2),
        incoterm=rng.choice(["FCA", "EXW", "DAP", "CIP"], p=[.5, .2, .2, .1]), data_prometida=prometida.isoformat(),
        data_recebimento=recebida.isoformat() if recebida <= CORTE else "",
        comprador=rng.choice(["Comprador A", "Comprador B", "Comprador C", "Comprador D"])))
P = pd.concat([P, pd.DataFrame(linhas)], ignore_index=True)

# notas sobre os recebimentos novos (mesma regra do gerador)
tipos = [("Q2", "Certificação do fabricante ausente", 0.32), ("Q2", "Reprovação na inspeção de recebimento", 0.30),
         ("Q2", "Revisão de peça superada", 0.16), ("Q2", "Dano no transporte", 0.12), ("Q3", "Divergência de documentação (CoC/FAI)", 0.10)]
rec_novos = P[(P.data_recebimento > "2026-09-30") & (P.data_recebimento <= CORTE.isoformat())]
nq = []; seq = int(Q.nota.str[2:].astype(int).max())
for _, r in rec_novos.iterrows():
    f = Fi.loc[r.id_fornecedor]
    if rng.random() < min(0.10, f.ppm_base / 45000):
        t = tipos[int(rng.choice(len(tipos), p=[x[2] for x in tipos]))]
        abertura = min(date.fromisoformat(r.data_recebimento) + timedelta(days=int(rng.integers(0, 4))), CORTE)
        fech = abertura + timedelta(days=int(rng.gamma(2.2, 9))); seq += 1
        nq.append(dict(nota=f"QN{seq}", tipo_nota=t[0], data_abertura=abertura.isoformat(),
            data_encerramento=fech.isoformat() if fech <= CORTE else "", status="Encerrada" if fech <= CORTE else "Aberta",
            pedido=r.pedido, id_fornecedor=r.id_fornecedor, part_number=r.part_number, motivo=t[1],
            qtd_rejeitada=int(max(1, round(r.quantidade * rng.uniform(.05, .4)))), qtd_recebida=r.quantidade,
            disposicao=rng.choice(["Devolução ao fornecedor", "Retrabalho pelo fornecedor", "Uso como está (concessão)", "Sucata"], p=[.5, .25, .15, .1]),
            causa_raiz=rng.choice(["Documentação", "Processo do fornecedor", "Embalagem", "Controle de revisão", "Subfornecedor"])))
Q = pd.concat([Q, pd.DataFrame(nq)], ignore_index=True)

# RFQs fechadas em outubro (ritmo médio histórico, mesmas regras)
n_rfq = int(rng.poisson(len(R) / 33 * CORTE.day / 31)); rfq = []; base_id = int(R.rfq.str[4:].astype(int).max())
for i in range(n_rfq):
    m = M.iloc[int(rng.integers(len(M)))]
    fechamento = date(2026, 10, int(rng.integers(1, CORTE.day + 1))); abertura = fechamento - timedelta(days=int(rng.integers(5, 40)))
    historico = rng.random() > 0.22
    novos = int(rng.choice([0, 1, 2], p=[.55, .3, .15])) if m.fonte_unica == "Sim" else int(rng.choice([0, 1], p=[.8, .2]))
    base = m.preco_base_usd_2024 * rng.normal(1.04, 0.03)
    inicial = base * rng.normal(1.04 + (0.02 if novos == 0 else 0), 0.035)
    final = inicial * (1 - max(0.0, rng.normal(0.05, 0.025) + 0.05 * novos))
    vol = int(1 + rng.poisson(12 if m.preco_base_usd_2024 < 20000 else 3))
    tipo, impacto = (("Savings" if final < base else "Aumento"), (base - final) * vol) if historico else ("Cost avoidance", (inicial - final) * vol)
    rfq.append(dict(rfq=f"RFQ-{base_id+1+i}", data_abertura=abertura.isoformat(), data_fechamento=fechamento.isoformat(),
        part_number=m.part_number, categoria=m.categoria, fonte_unica_antes=m.fonte_unica, item_com_historico="Sim" if historico else "Não",
        fornecedores_convidados=int(rng.integers(2, 6)) + novos, novos_fabricantes_incluidos=novos,
        preco_referencia_usd=round(base, 2) if historico else "", cotacao_inicial_usd=round(inicial, 2), preco_final_usd=round(final, 2),
        volume_anual=vol, tipo_resultado=tipo, impacto_usd=round(impacto, 2),
        validado_finance=rng.choice(["Sim", "Pendente"], p=[.8, .2]) if tipo != "Aumento" else "N/A"))
R = pd.concat([R, pd.DataFrame(rfq)], ignore_index=True)

# ---------- 5. meta de outubro ----------
T = pd.read_csv(os.path.join(SIN, "metas_mensais.csv"))
if "2026-10" not in set(T.mes):
    T = pd.concat([T, T[T.mes == "2026-09"].assign(mes="2026-10")], ignore_index=True)

P.to_csv(os.path.join(SIN, "pedidos_compra.csv"), index=False)
Q.to_csv(os.path.join(SIN, "notas_qualidade.csv"), index=False)
R.to_csv(os.path.join(SIN, "rfqs_savings.csv"), index=False)
T.to_csv(os.path.join(SIN, "metas_mensais.csv"), index=False)
print(dict(recebimentos_novos=int(novos_rec.sum()), notas_encerradas=int(fecha.sum()), pedidos_outubro=len(linhas),
           notas_novas=len(nq), rfqs_outubro=len(rfq), ptax_out=(usd, eur)))
