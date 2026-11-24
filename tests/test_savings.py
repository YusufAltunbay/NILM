import pandas as pd
import pytest

from panel import savings


def _m():
    return pd.DataFrame({"kWh": [10.0, 20.0, 5.0], "TL": [30.0, 60.0, 10.0]}, index=["a", "b", "c"])


def test_monthly_scales_to_30_days():
    bill = pd.DataFrame({"Tahmin (kWh)": [1.0], "Tahmin (TL)": [3.0]}, index=["a"])
    m = savings.monthly(bill, days=15)
    assert m.loc["a", "TL"] == pytest.approx(6.0)
    assert m.loc["a", "kWh"] == pytest.approx(2.0)


def test_scenario_savings():
    s = savings.scenario(_m(), {"b": 50, "a": 10})
    assert s.loc["b", "Tasarruf TL"] == pytest.approx(30.0)
    assert s.loc["a", "Yeni TL"] == pytest.approx(27.0)
    assert s.loc["c", "Tasarruf TL"] == 0
    assert s["Tasarruf TL"].sum() == pytest.approx(33.0)


def test_plan_reaches_target_from_most_expensive():
    plan, ok = savings.plan_for_target(_m(), 20)   # 100 TL'nin %20'si = 20 TL
    assert ok and list(plan) == ["b"]              # en pahalı cihaz tek başına yeter
    saved = savings.scenario(_m(), plan)["Tasarruf TL"].sum()
    assert saved >= 20 - 1e-6


def test_plan_infeasible_when_target_too_high():
    plan, ok = savings.plan_for_target(_m(), 80)   # tavan %50 olduğu için en çok %50 düşer
    assert not ok
    assert all(v <= savings.MAX_CUT for v in plan.values())


def test_suggestions_rank_and_unknown_appliance():
    m = pd.DataFrame({"kWh": [1, 2], "TL": [10.0, 40.0]}, index=["tv", "kettle"])
    s = savings.suggestions(m)
    assert [x["appliance"] for x in s] == ["kettle", "tv"]
    assert s[1]["tip"] == savings.GENERIC[0]       # tanımsız cihaz için genel öneri
