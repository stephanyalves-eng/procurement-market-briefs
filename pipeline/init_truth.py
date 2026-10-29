"""One-time setup: rebuilds the hidden "truth" of the synthetic dataset as of 28 Oct 2026.

The synthetic tables in data/synthetic/ only show what a buyer would see on a given day: a purchase
order placed today has no receipt date yet, an open quality notification has no closing date. The
generator knows those future dates. To keep extending the dataset month after month without ever
rewriting history, the pipeline stores them in data/synthetic/_truth/.

This script recovers them by replaying, with the same seeds, the two scripts that produced the
October 2026 edition (pipeline/legacy/), and checks that the replay matches the published tables
row for row before writing anything. It only needs to run once.
"""
import os, sys, tempfile, shutil, json
import numpy as np, pandas as pd
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYN = os.path.join(ROOT, "data", "synthetic"); TRUTH = os.path.join(SYN, "_truth")
LEG = os.path.join(ROOT, "pipeline", "legacy")
CUTOFF = date(2026, 10, 28)
BACKUP = sys.argv[1] if len(sys.argv) > 1 else None  # tables before the October extension

# 1. replay the generator (seed 42), keeping the hidden dates
tmp = tempfile.mkdtemp(); os.makedirs(os.path.join(tmp, "dados", "publicos"))
for f in ("bls_ppi_aeroespacial_metais_mensal.csv", "bcb_cambio_ipca_mensal.csv"):
    shutil.copy(os.path.join(ROOT, "data", "public", f), os.path.join(tmp, "dados", "publicos", f))
src = open(os.path.join(LEG, "gerar_dados_sinteticos.py"), encoding="utf-8").read()
src = src[:src.index('F.drop(columns=["otd_base", "ppm_base"]).to_csv')]
src = src.replace('comprador=rng.choice(["Comprador A", "Comprador B", "Comprador C", "Comprador D"])))',
                  'comprador=rng.choice(["Comprador A", "Comprador B", "Comprador C", "Comprador D"]), _receb_real=recebida.isoformat()))')
src = src.replace("causa_raiz=rng.choice([\"Documentação\", \"Processo do fornecedor\", \"Embalagem\", \"Controle de revisão\", \"Subfornecedor\"])))",
                  "causa_raiz=rng.choice([\"Documentação\", \"Processo do fornecedor\", \"Embalagem\", \"Controle de revisão\", \"Subfornecedor\"]), _fech_real=fech.isoformat()))")
ns = {"__file__": os.path.join(tmp, "gerar_dados_sinteticos.py")}
exec(compile(src, "generator", "exec"), ns)
F, M, P0, R0, Q0 = ns["F"], ns["M"], ns["P"], ns["R"], ns["Q"]
categorias, forn_peso = ns["categorias"], ns["forn_peso"]

# 2. replay the October extension (seed 20261029) from the pre-extension tables
B = BACKUP or os.path.join(SYN, "_backup_2026-10-28")
P = pd.read_csv(os.path.join(B, "pedidos_compra.csv"), dtype={"data_recebimento": str}, keep_default_na=False)
R = pd.read_csv(os.path.join(B, "rfqs_savings.csv"), keep_default_na=False)
Q = pd.read_csv(os.path.join(B, "notas_qualidade.csv"), keep_default_na=False)
assert len(P) == len(P0) and (P.pedido.values == P0.pedido.values).all()
P["_receb_real"] = P0._receb_real.values; Q["_fech_real"] = Q0._fech_real.values
abertos = P.data_recebimento == ""; novos = abertos & (P._receb_real <= CUTOFF.isoformat())
P.loc[novos, "data_recebimento"] = P.loc[novos, "_receb_real"]
fecha = (Q.status == "Aberta") & (Q._fech_real <= CUTOFF.isoformat())
Q.loc[fecha, "data_encerramento"] = Q.loc[fecha, "_fech_real"]; Q.loc[fecha, "status"] = "Encerrada"

rng = np.random.default_rng(20261029)
pub = os.path.join(ROOT, "data", "public")
ppi = pd.read_csv(os.path.join(pub, "bls_ppi_aeroespacial_metais_mensal.csv")).set_index("mes")
fx = pd.read_csv(os.path.join(pub, "bcb_cambio_ipca_mensal.csv")).set_index("mes")
usd, eur = fx.loc["2026-10", "usd_brl_ptax_media"], fx.loc["2026-10", "eur_brl_ptax_media"]
Fi = F.set_index("id_fornecedor")
saz = 1 + 0.12 * np.sin((10 - 3) / 12 * 2 * np.pi)
n = int(rng.poisson(330 * saz * 1.1 * CUTOFF.day / 31)); po = int(P.pedido.max()); rows = []
for _ in range(n):
    m = M.iloc[int(rng.choice(len(M), p=M.peso))]
    opc = m.fornecedores_aprovados.split(";"); w = np.array([forn_peso[x] for x in opc]); fid = opc[int(rng.choice(len(opc), p=w / w.sum()))]; f = Fi.loc[fid]
    col = categorias[m.categoria][0]
    preco_usd = m.preco_base_usd_2024 * ppi.loc["2026-09", col] / ppi.loc["2024-01", col] * rng.normal(1, 0.03)
    qtd = int(1 + rng.poisson(1 if m.preco_base_usd_2024 > 20000 else 5))
    data_po = date(2026, 10, int(rng.integers(1, CUTOFF.day + 1)))
    prometida = data_po + timedelta(days=int(f.lead_time_contratual_dias))
    atraso = 0 if rng.random() < f.otd_base else int(rng.gamma(2, 9)) + 1
    recebida = prometida + timedelta(days=atraso - int(rng.integers(0, 6)) if atraso == 0 else atraso)
    taxa = {"USD": 1.0, "EUR": usd / eur, "BRL": usd}[f.moeda]; po += 1
    rows.append(dict(pedido=po, item=10, data_pedido=data_po.isoformat(), id_fornecedor=fid, part_number=m.part_number,
        categoria=m.categoria, quantidade=qtd, moeda=f.moeda, preco_unitario_moeda=round(preco_usd * taxa, 2),
        valor_total_moeda=round(preco_usd * taxa * qtd, 2), usd_brl_mes=usd, valor_total_usd=round(preco_usd * qtd, 2),
        incoterm=rng.choice(["FCA", "EXW", "DAP", "CIP"], p=[.5, .2, .2, .1]), data_prometida=prometida.isoformat(),
        data_recebimento=recebida.isoformat() if recebida <= CUTOFF else "",
        comprador=rng.choice(["Comprador A", "Comprador B", "Comprador C", "Comprador D"]), _receb_real=recebida.isoformat()))
P = pd.concat([P, pd.DataFrame(rows)], ignore_index=True)
tipos = [("Q2", "Certificação do fabricante ausente", 0.32), ("Q2", "Reprovação na inspeção de recebimento", 0.30),
         ("Q2", "Revisão de peça superada", 0.16), ("Q2", "Dano no transporte", 0.12), ("Q3", "Divergência de documentação (CoC/FAI)", 0.10)]
rec = P[(P.data_recebimento > "2026-09-30") & (P.data_recebimento <= CUTOFF.isoformat())]
nq = []; seq = int(Q.nota.str[2:].astype(int).max())
for _, r in rec.iterrows():
    f = Fi.loc[r.id_fornecedor]
    if rng.random() < min(0.10, f.ppm_base / 45000):
        t = tipos[int(rng.choice(len(tipos), p=[x[2] for x in tipos]))]
        ab = min(date.fromisoformat(r.data_recebimento) + timedelta(days=int(rng.integers(0, 4))), CUTOFF)
        fech = ab + timedelta(days=int(rng.gamma(2.2, 9))); seq += 1
        nq.append(dict(nota=f"QN{seq}", tipo_nota=t[0], data_abertura=ab.isoformat(),
            data_encerramento=fech.isoformat() if fech <= CUTOFF else "", status="Encerrada" if fech <= CUTOFF else "Aberta",
            pedido=r.pedido, id_fornecedor=r.id_fornecedor, part_number=r.part_number, motivo=t[1],
            qtd_rejeitada=int(max(1, round(r.quantidade * rng.uniform(.05, .4)))), qtd_recebida=r.quantidade,
            disposicao=rng.choice(["Devolução ao fornecedor", "Retrabalho pelo fornecedor", "Uso como está (concessão)", "Sucata"], p=[.5, .25, .15, .1]),
            causa_raiz=rng.choice(["Documentação", "Processo do fornecedor", "Embalagem", "Controle de revisão", "Subfornecedor"]), _fech_real=fech.isoformat()))
Q = pd.concat([Q, pd.DataFrame(nq)], ignore_index=True)

# 3. the replay must match the published tables exactly
pub_P = pd.read_csv(os.path.join(SYN, "pedidos_compra.csv"), dtype={"data_recebimento": str}, keep_default_na=False)
pub_Q = pd.read_csv(os.path.join(SYN, "notas_qualidade.csv"), keep_default_na=False)
for a, b, k in ((P, pub_P, "pedido"), (Q, pub_Q, "nota")):
    a2 = a.drop(columns=[c for c in a.columns if c.startswith("_")]).astype(str).reset_index(drop=True)
    b2 = b.astype(str).reset_index(drop=True)
    assert list(a2.columns) == list(b2.columns) and len(a2) == len(b2), k
    diff = (a2 != b2).any(axis=1).sum()
    assert diff == 0, f"{k}: {diff} rows differ"

# 4. save the truth (all tables, hidden dates included) and the state
os.makedirs(TRUTH, exist_ok=True)
P.rename(columns={"_receb_real": "receb_real"}).to_csv(os.path.join(TRUTH, "pedidos_compra.csv"), index=False)
Q.rename(columns={"_fech_real": "fech_real"}).to_csv(os.path.join(TRUTH, "notas_qualidade.csv"), index=False)
pd.read_csv(os.path.join(SYN, "rfqs_savings.csv"), keep_default_na=False).to_csv(os.path.join(TRUTH, "rfqs_savings.csv"), index=False)
F.to_csv(os.path.join(TRUTH, "fornecedores_params.csv"), index=False)            # includes otd_base and ppm_base
M[["part_number", "peso"]].to_csv(os.path.join(TRUTH, "materiais_peso.csv"), index=False)
pd.Series(forn_peso, name="peso").rename_axis("id_fornecedor").to_csv(os.path.join(TRUTH, "fornecedores_peso.csv"))
json.dump({"generated_through": CUTOFF.isoformat(), "notes_through": CUTOFF.isoformat()}, open(os.path.join(TRUTH, "state.json"), "w"), indent=2)
print("truth ok:", len(P), "POs,", len(Q), "notes; replay matches the published tables")
