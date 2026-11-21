"""Extending the data to a new month must not change any earlier report.

Each month is appended with its own seed and past records are never rewritten. These tests rebuild October's
inputs after the truth has been extended to November and check they are identical.
"""
from datetime import date
import pandas as pd
from pandas.testing import assert_frame_equal

import synthetic, sqe_synthetic, sixsigma_synthetic

OCT, NOV = date(2026, 10, 31), date(2026, 11, 30)


def _headline(P, Q, R, month):
    """The procurement report's headline numbers for one month, from the tables the brief loads."""
    r = P[P.mr == month]; q = Q[Q.m == month]; rr = R[(R.m >= month[:4] + "-01") & (R.m <= month)]
    return dict(otd=(r.data_recebimento <= r.data_prometida).mean() * 100,
                ppm=q.qtd_rejeitada.sum() / max(r.quantidade.sum(), 1) * 1e6,
                savings_ytd=rr[rr.tipo_resultado == "Savings"].impacto_usd.sum())


def test_extending_november_leaves_october_unchanged(truth_copy, monkeypatch):
    from briefs import procurement
    monkeypatch.setattr(procurement, "SYN", synthetic.SYN)
    before = procurement.load(OCT)
    assert synthetic.load_truth()[3]["generated_through"] == OCT.isoformat(), "fixture should start at the October cutoff"

    synthetic.extend(NOV)
    assert synthetic.load_truth()[3]["generated_through"] == NOV.isoformat()
    assert len(synthetic.load_truth()[0]) > len(before[0]), "extension added no purchase order"

    after = procurement.load(OCT)
    for name, b, a in zip(("purchase orders", "quality notifications", "RFQs", "targets"), before, after):
        assert_frame_equal(b.reset_index(drop=True), a.reset_index(drop=True), obj=f"October {name}")
    assert _headline(*after[:3], "2026-10") == _headline(*before[:3], "2026-10")


def test_extending_is_append_only(truth_copy):
    P0, Q0, R0, _ = synthetic.load_truth()
    synthetic.extend(NOV)
    P1, Q1, R1, _ = synthetic.load_truth()
    for name, old, new in (("purchase orders", P0, P1), ("quality notifications", Q0, Q1), ("RFQs", R0, R1)):
        assert_frame_equal(old, new.iloc[:len(old)], obj=f"existing {name}")


def test_supplier_quality_history_does_not_depend_on_cutoff():
    """Records dated up to October are the same whether the view is taken at the end of October or November."""
    _, R_oct, I_oct, _, A_oct = sqe_synthetic.view(OCT)
    _, R_nov, I_nov, _, A_nov = sqe_synthetic.view(NOV)
    end = pd.Timestamp(OCT) + pd.Timedelta(hours=23, minutes=59)
    assert_frame_equal(R_oct.reset_index(drop=True), R_nov[R_nov.data_recebimento <= end].reset_index(drop=True))
    assert_frame_equal(A_oct.reset_index(drop=True), A_nov[A_nov.data_auditoria <= end].reset_index(drop=True))
    fixed = ["id_problema", "data_abertura", "id_fornecedor", "origem", "defeito", "deteccao", "qtd_rejeitada", "copq_usd"]
    assert_frame_equal(I_oct[fixed].reset_index(drop=True), I_nov.loc[I_nov.data_abertura <= end, fixed].reset_index(drop=True))


def test_six_sigma_measurements_do_not_depend_on_cutoff():
    m_oct, m_nov = sixsigma_synthetic.measurements(OCT), sixsigma_synthetic.measurements(NOV)
    assert_frame_equal(m_oct, m_nov[m_nov.data <= pd.Timestamp(OCT)].reset_index(drop=True))
