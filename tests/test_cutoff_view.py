"""Fixed-cutoff tests: nothing dated after the cutoff may reach what a buyer or quality engineer sees.

The truth tables hold real future dates (when an order will arrive, when a notification will close). A leak would
show a future receipt, closure, decision or measurement in a report that claims to describe the cutoff date.
"""
from datetime import date
import pandas as pd
import pytest

import synthetic, sqe_synthetic, sixsigma_synthetic

# mid-month and mid-week on purpose: month ends hide leaks that only show up in a partial period
CUTOFFS = [date(2026, 10, 15), date(2026, 7, 8), date(2025, 12, 31)]


def _not_after(series, cutoff, what):
    s = pd.to_datetime(series.replace("", None), errors="raise").dropna()
    late = s[s > pd.Timestamp(cutoff) + pd.Timedelta(hours=23, minutes=59)]
    assert late.empty, f"{what}: {len(late)} value(s) after the cutoff {cutoff}, first {late.min()}"


@pytest.mark.parametrize("cutoff", CUTOFFS)
def test_procurement_view_has_no_future_dates(cutoff):
    P, Q, R = synthetic.view(cutoff)
    assert "receb_real" not in P.columns and "fech_real" not in Q.columns, "truth columns exported"
    _not_after(P.data_pedido, cutoff, "PO dates")
    _not_after(P.data_recebimento, cutoff, "PO receipt dates")
    _not_after(Q.data_abertura, cutoff, "quality notification opening dates")
    _not_after(Q.data_encerramento, cutoff, "quality notification closing dates")
    _not_after(R.data_abertura, cutoff, "RFQ opening dates")
    _not_after(R.data_fechamento, cutoff, "RFQ closing dates")
    # an item closed after the cutoff must still show as open
    assert set(Q.loc[Q.data_encerramento == "", "status"]) <= {"Aberta"}
    assert set(Q.loc[Q.data_encerramento != "", "status"]) <= {"Encerrada"}


@pytest.mark.parametrize("cutoff", CUTOFFS)
def test_supplier_quality_view_has_no_future_events(cutoff):
    _, R, I, P, A = sqe_synthetic.view(cutoff)
    _not_after(R.data_recebimento, cutoff, "receipts")
    for c in ("data_abertura", "data_contencao", "data_encerramento_8d"):
        _not_after(I[c], cutoff, f"quality issues {c}")
    assert (I.status == "Closed").sum() == I.data_encerramento_8d.notna().sum()
    assert I.loc[I.data_contencao.isna(), "contencao_horas"].isna().all(), "containment time shown before containment"
    # data_prevista is the localization plan and may be in the future; what happened to a part may not
    for c in ("data_submissao", "data_decisao", "aprovacao_final"):
        _not_after(P[c], cutoff, f"PPAP {c}")
    assert P.loc[P.data_decisao.isna(), "decisao_1"].isna().all(), "PPAP decision shown before its date"
    _not_after(A.data_auditoria, cutoff, "audits")


@pytest.mark.parametrize("cutoff", CUTOFFS)
def test_six_sigma_layer_has_no_future_measurements(cutoff):
    _not_after(sixsigma_synthetic.measurements(cutoff).data, cutoff, "capability measurements")
    ps = sixsigma_synthetic.project_status(cutoff)
    if len(ps): _not_after(ps.start.astype(str), cutoff, "DMAIC project starts")


def test_procurement_view_drops_receipts_after_cutoff():
    """Guard for the test itself: the truth does contain later receipts, so the view really filters something."""
    P, _, _, _ = synthetic.load_truth(); c = "2026-10-15"
    pending = P[(P.data_pedido <= c) & (P.receb_real > c)]
    assert len(pending), "fixture has no PO received after the cutoff; pick another cutoff"
    V = synthetic.view(date.fromisoformat(c))[0].set_index(["pedido", "item"])
    assert (V.loc[pending.set_index(["pedido", "item"]).index, "data_recebimento"] == "").all()
