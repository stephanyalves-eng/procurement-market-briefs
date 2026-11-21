"""Data vintage in the manifest: a run that is not fully fresh must say so."""
import json, shutil
from datetime import date
import pandas as pd
import pytest

from briefs import vintage
from conftest import ROOT

EDITION = date(2026, 11, 16)          # every series in the repository covers what is expected on this date


@pytest.fixture
def pub(tmp_path):
    d = tmp_path / "public"; shutil.copytree(f"{ROOT}/data/public", d)
    (d / "sources_status.json").write_text(json.dumps({s: {"fetched_at": "2026-11-16T11:30:00Z", "published_at": None}
                                                       for s in ("bcb", "bls", "comex")}))
    return d


def _drop_month(pub, file, month):
    p = pub / file; df = pd.read_csv(p); df[df.mes != month].to_csv(p, index=False)


def test_fresh_run_is_current_and_silent(pub):
    s = vintage.collect(EDITION, pub=str(pub))
    assert {v["status"] for v in s.values()} == {"current"}
    assert vintage.warnings(s) == []
    for v in s.values():
        assert set(v) >= {"source_period", "expected_period", "fetched_at", "published_at", "status"}


def test_expected_periods_follow_release_days():
    assert vintage.expected_period("comex_aero", date(2026, 11, 9)) == "2026-09"
    assert vintage.expected_period("comex_aero", date(2026, 11, 10)) == "2026-10"
    assert vintage.expected_period("bls_ppi", date(2026, 11, 15)) == "2026-09"
    assert vintage.expected_period("bls_ppi", date(2026, 11, 16)) == "2026-10"
    assert vintage.expected_period("bcb_ptax_daily", date(2026, 11, 16)) == "2026-11-13"   # Monday -> Friday


@pytest.mark.parametrize("fetched,failed,status", [(False, (), "skipped"), (True, ("bls",), "fetch_failed")])
def test_skipped_or_failed_fetch_always_warns(pub, fetched, failed, status):
    s = vintage.collect(EDITION, fetched=fetched, failed=failed, pub=str(pub))
    assert s["bls_ppi"]["status"] == status
    assert any(w.startswith(status.replace("_", " ")) and "bls_ppi" in w for w in vintage.warnings(s))


def test_series_that_did_not_move_is_carried_forward_and_partial(pub):
    """The fetch worked but BLS has not released October yet: the October value must not pass as current."""
    _drop_month(pub, "bls_ppi_aeroespacial_metais_mensal.csv", "2026-10")
    s = vintage.collect(EDITION, pub=str(pub))
    v = s["bls_ppi"]
    assert (v["status"], v["behind"], v["source_period"], v["expected_period"]) == ("carried_forward", True, "2026-09", "2026-10")
    assert any(w.startswith("partial coverage: bls_ppi") for w in vintage.warnings(s))
    assert vintage.coverage_note("aerospace", EDITION, "en", pub=str(pub)) == \
        "Partial coverage: BLS PPI through Sep 2026 (Oct 2026 not yet available)."
    assert "PPI do BLS até set/2026" in vintage.coverage_note("procurement", EDITION, "pt", pub=str(pub))
    assert vintage.coverage_note("ev", EDITION, "en", pub=str(pub)) == ""


def test_one_late_column_makes_a_table_late(pub):
    p = pub / "bls_ppi_aeroespacial_metais_mensal.csv"; df = pd.read_csv(p)
    df.loc[df.mes == "2026-10", "ppi_aco_laminados_WPU1017"] = None; df.to_csv(p, index=False)
    assert vintage.source_period("bls_ppi", EDITION, str(pub)) == "2026-09"


def test_rebuilding_an_old_edition_flags_possible_hindsight(pub):
    """Files downloaded on 16 Nov hold October data that was not public on 3 Nov."""
    s = vintage.collect(date(2026, 11, 3), fetched=False, pub=str(pub))
    assert s["comex_aero"]["ahead"] and s["bls_ppi"]["ahead"]
    assert any(w.startswith("possible hindsight: comex_aero") for w in vintage.warnings(s))
