"""Synthetic procurement dataset: extend it to a new cutoff date and export what a buyer would see.

Truth tables (data/synthetic/_truth/) hold every record with its real future dates: when a purchase
order will actually be received, when a quality notification will actually close. The visible tables
(data/synthetic/*.csv) are a view of that truth on a cutoff date. Extending never edits an existing
record, it only appends the days after the last generated date, with a seed derived from those dates.

Usage:
    python pipeline/synthetic.py 2026-11-30     # extend to 30 Nov 2026 and export the view
"""
import os, sys, json, calendar
import numpy as np, pandas as pd
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYN = os.path.join(ROOT, "data", "synthetic"); TRUTH = os.path.join(SYN, "_truth"); PUB = os.path.join(ROOT, "data", "public")

CATEGORIAS = {"Propulsão": "ppi_motores_aeronauticos_PCU336412", "Aviônica": "ppi_avionica_navegacao_PCU334511",
              "Estruturas e usinados": "ppi_pecas_aeronauticas_PCU336413", "Trem de pouso e hidráulica": "ppi_pecas_aeronauticas_PCU336413",
              "Elétrica e chicotes": "ppi_pecas_aeronauticas_PCU336413", "Matéria-prima metálica": "ppi_aco_laminados_WPU1017"}
TIPOS = [("Q2", "Certificação do fabricante ausente", 0.32), ("Q2", "Reprovação na inspeção de recebimento", 0.30),
         ("Q2", "Revisão de peça superada", 0.16), ("Q2", "Dano no transporte", 0.12), ("Q3", "Divergência de documentação (CoC/FAI)", 0.10)]
RFQ_PER_MONTH = 420 / 33  # same pace as the original generator


def load_truth():
    P = pd.read_csv(os.path.join(TRUTH, "pedidos_compra.csv"), dtype=str, keep_default_na=False)
    Q = pd.read_csv(os.path.join(TRUTH, "notas_qualidade.csv"), dtype=str, keep_default_na=False)
    R = pd.read_csv(os.path.join(TRUTH, "rfqs_savings.csv"), dtype=str, keep_default_na=False)
    st = json.load(open(os.path.join(TRUTH, "state.json")))
    return P, Q, R, st


def segments(start, end):
    """Split [start, end] into calendar-month pieces."""
    d = start
    while d <= end:
        last = date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])
        yield d, min(last, end); d = min(last, end) + timedelta(days=1)


def extend(cutoff):
    P, Q, R, st = load_truth()
    done = date.fromisoformat(st["generated_through"])
    if cutoff <= done:
        print(f"truth already generated through {done}; nothing to extend"); return
    F = pd.read_csv(os.path.join(TRUTH, "fornecedores_params.csv")).set_index("id_fornecedor")
    M = pd.read_csv(os.path.join(SYN, "materiais.csv")).merge(pd.read_csv(os.path.join(TRUTH, "materiais_peso.csv")), on="part_number")
    fpeso = pd.read_csv(os.path.join(TRUTH, "fornecedores_peso.csv")).set_index("id_fornecedor").peso.to_dict()
    ppi = pd.read_csv(os.path.join(PUB, "bls_ppi_aeroespacial_metais_mensal.csv")).set_index("mes").sort_index()
    fx = pd.read_csv(os.path.join(PUB, "bcb_cambio_ipca_mensal.csv")).set_index("mes").sort_index()
    po = int(P.pedido.astype(int).max()); nseq = int(Q.nota.str[2:].astype(int).max()); rseq = int(R.rfq.str[4:].astype(int).max())
    newP, newQ, newR = [], [], []
    for a, b in segments(done + timedelta(days=1), cutoff):
        rng = np.random.default_rng(int(a.strftime("%Y%m%d")) * 100 + b.day)
        mes = a.strftime("%Y-%m"); dim = calendar.monthrange(a.year, a.month)[1]; ndays = (b - a).days + 1
        ppi_m = ppi[ppi.index <= mes].dropna(how="all").index.max()          # latest PPI published for that month
        fx_m = fx[fx.index <= mes].usd_brl_ptax_media.dropna().index.max()
        usd, eur = fx.loc[fx_m, "usd_brl_ptax_media"], fx.loc[fx_m, "eur_brl_ptax_media"]
        saz = 1 + 0.12 * np.sin((a.month - 3) / 12 * 2 * np.pi)
        for _ in range(int(rng.poisson(330 * saz * 1.1 * ndays / dim))):
            m = M.iloc[int(rng.choice(len(M), p=M.peso / M.peso.sum()))]
            opc = m.fornecedores_aprovados.split(";"); w = np.array([fpeso[x] for x in opc]); fid = opc[int(rng.choice(len(opc), p=w / w.sum()))]; f = F.loc[fid]
            col = CATEGORIAS[m.categoria]
            preco_usd = m.preco_base_usd_2024 * ppi.loc[ppi_m, col] / ppi.loc["2024-01", col] * rng.normal(1, 0.03)
            qtd = int(1 + rng.poisson(1 if m.preco_base_usd_2024 > 20000 else 5))
            data_po = a + timedelta(days=int(rng.integers(0, ndays)))
            prometida = data_po + timedelta(days=int(f.lead_time_contratual_dias))
            atraso = 0 if rng.random() < f.otd_base else int(rng.gamma(2, 9)) + 1
            recebida = prometida + timedelta(days=atraso - int(rng.integers(0, 6)) if atraso == 0 else atraso)
            taxa = {"USD": 1.0, "EUR": usd / eur, "BRL": usd}[f.moeda]; po += 1
            newP.append(dict(pedido=po, item=10, data_pedido=data_po.isoformat(), id_fornecedor=fid, part_number=m.part_number,
                categoria=m.categoria, quantidade=qtd, moeda=f.moeda, preco_unitario_moeda=round(preco_usd * taxa, 2),
                valor_total_moeda=round(preco_usd * taxa * qtd, 2), usd_brl_mes=usd, valor_total_usd=round(preco_usd * qtd, 2),
                incoterm=rng.choice(["FCA", "EXW", "DAP", "CIP"], p=[.5, .2, .2, .1]), data_prometida=prometida.isoformat(),
                data_recebimento="", comprador=rng.choice(["Comprador A", "Comprador B", "Comprador C", "Comprador D"]),
                receb_real=recebida.isoformat()))
        for _ in range(int(rng.poisson(RFQ_PER_MONTH * ndays / dim))):
            m = M.iloc[int(rng.integers(len(M)))]
            fech = a + timedelta(days=int(rng.integers(0, ndays))); ab = fech - timedelta(days=int(rng.integers(5, 40)))
            hist = rng.random() > 0.22
            novos = int(rng.choice([0, 1, 2], p=[.55, .3, .15])) if m.fonte_unica == "Sim" else int(rng.choice([0, 1], p=[.8, .2]))
            base = m.preco_base_usd_2024 * rng.normal(1.04, 0.03)
            ini = base * rng.normal(1.04 + (0.02 if novos == 0 else 0), 0.035)
            fin = ini * (1 - max(0.0, rng.normal(0.05, 0.025) + 0.05 * novos))
            vol = int(1 + rng.poisson(12 if m.preco_base_usd_2024 < 20000 else 3))
            tipo, imp = (("Savings" if fin < base else "Aumento"), (base - fin) * vol) if hist else ("Cost avoidance", (ini - fin) * vol)
            rseq += 1
            newR.append(dict(rfq=f"RFQ-{rseq}", data_abertura=ab.isoformat(), data_fechamento=fech.isoformat(), part_number=m.part_number,
                categoria=m.categoria, fonte_unica_antes=m.fonte_unica, item_com_historico="Sim" if hist else "Não",
                fornecedores_convidados=int(rng.integers(2, 6)) + novos, novos_fabricantes_incluidos=novos,
                preco_referencia_usd=round(base, 2) if hist else "", cotacao_inicial_usd=round(ini, 2), preco_final_usd=round(fin, 2),
                volume_anual=vol, tipo_resultado=tipo, impacto_usd=round(imp, 2),
                validado_finance=rng.choice(["Sim", "Pendente"], p=[.8, .2]) if tipo != "Aumento" else "N/A"))
        # quality notifications for every receipt that really happens inside this segment
        allP = pd.concat([P, pd.DataFrame(newP).astype(str)], ignore_index=True) if newP else P
        rec = allP[(allP.receb_real >= a.isoformat()) & (allP.receb_real <= b.isoformat())]
        for _, r in rec.iterrows():
            f = F.loc[r.id_fornecedor]
            if rng.random() < min(0.10, f.ppm_base / 45000):
                t = TIPOS[int(rng.choice(len(TIPOS), p=[x[2] for x in TIPOS]))]
                ab = date.fromisoformat(r.receb_real) + timedelta(days=int(rng.integers(0, 4)))
                fech = ab + timedelta(days=int(rng.gamma(2.2, 9))); nseq += 1; qr = int(r.quantidade)
                newQ.append(dict(nota=f"QN{nseq}", tipo_nota=t[0], data_abertura=ab.isoformat(), data_encerramento="", status="Aberta",
                    pedido=r.pedido, id_fornecedor=r.id_fornecedor, part_number=r.part_number, motivo=t[1],
                    qtd_rejeitada=int(max(1, round(qr * rng.uniform(.05, .4)))), qtd_recebida=qr,
                    disposicao=rng.choice(["Devolução ao fornecedor", "Retrabalho pelo fornecedor", "Uso como está (concessão)", "Sucata"], p=[.5, .25, .15, .1]),
                    causa_raiz=rng.choice(["Documentação", "Processo do fornecedor", "Embalagem", "Controle de revisão", "Subfornecedor"]),
                    fech_real=fech.isoformat()))
    P = pd.concat([P, pd.DataFrame(newP).astype(str)], ignore_index=True)
    Q = pd.concat([Q, pd.DataFrame(newQ).astype(str)], ignore_index=True)
    R = pd.concat([R, pd.DataFrame(newR).astype(str)], ignore_index=True)
    P.to_csv(os.path.join(TRUTH, "pedidos_compra.csv"), index=False)
    Q.to_csv(os.path.join(TRUTH, "notas_qualidade.csv"), index=False)
    R.to_csv(os.path.join(TRUTH, "rfqs_savings.csv"), index=False)
    json.dump({"generated_through": cutoff.isoformat(), "notes_through": cutoff.isoformat()}, open(os.path.join(TRUTH, "state.json"), "w"), indent=2)
    print(f"extended {done} -> {cutoff}: {len(newP)} POs, {len(newR)} RFQs, {len(newQ)} quality notifications")


def view(cutoff):
    """Tables as a buyer would see them on the cutoff date."""
    P, Q, R, _ = load_truth(); c = cutoff.isoformat()
    P = P[P.data_pedido <= c].copy(); P["data_recebimento"] = np.where(P.receb_real <= c, P.receb_real, "")
    Q = Q[Q.data_abertura <= c].copy(); closed = Q.fech_real <= c
    Q["data_encerramento"] = np.where(closed, Q.fech_real, ""); Q["status"] = np.where(closed, "Encerrada", "Aberta")
    R = R[R.data_fechamento <= c].copy()
    return P.drop(columns="receb_real"), Q.drop(columns="fech_real"), R


def export(cutoff):
    P, Q, R = view(cutoff)
    P.to_csv(os.path.join(SYN, "pedidos_compra.csv"), index=False)
    Q.to_csv(os.path.join(SYN, "notas_qualidade.csv"), index=False)
    R.to_csv(os.path.join(SYN, "rfqs_savings.csv"), index=False)
    T = pd.read_csv(os.path.join(SYN, "metas_mensais.csv"))
    last = T.iloc[-1]; months = pd.period_range(T.mes.iloc[-1], cutoff.strftime("%Y-%m"), freq="M")[1:]
    if len(months):
        T = pd.concat([T, pd.DataFrame([last.to_dict() | {"mes": str(m)} for m in months])], ignore_index=True)
        T.to_csv(os.path.join(SYN, "metas_mensais.csv"), index=False)
    print(f"view exported for {cutoff}: {len(P)} POs, {len(Q)} notes, {len(R)} RFQs")


if __name__ == "__main__":
    c = date.fromisoformat(sys.argv[1]); extend(c); export(c)
