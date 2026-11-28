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


def _devices():
    return pd.DataFrame({"kWh": [10.0, 20.0, 5.0], "TL": [100.0, 60.0, 40.0]}, index=["fridge", "kettle", "dish washer"])


def test_presets_differ_per_appliance_and_grow():
    apps = ["fridge", "kettle", "tv"]
    lo, mid, hi = (savings.preset_cuts(apps, p) for p in savings.PRESETS)
    assert len({lo["fridge"], lo["kettle"]}) == 2            # her cihaz kendi aralığında
    for a in apps:
        assert lo[a] <= mid[a] <= hi[a] <= savings.MAX_CUT


def test_plan_respects_per_device_cap():
    plan, ok, potential = savings.plan_for_target(_devices(), 8)
    caps = {a: savings.tip_range(a)[1] for a in plan}
    assert ok and all(plan[a] <= caps[a] for a in plan)
    assert savings.scenario(_devices(), plan)["Tasarruf TL"].sum() >= 8 - 1e-6


def test_plan_infeasible_beyond_realistic_potential():
    plan, ok, potential = savings.plan_for_target(_devices(), 40)
    assert not ok and potential < 0.4 * 200


def test_suggestions_rank_and_unknown_appliance():
    m = pd.DataFrame({"kWh": [1, 2], "TL": [10.0, 40.0]}, index=["tv", "kettle"])
    s = savings.suggestions(m)
    assert [x["appliance"] for x in s] == ["kettle", "tv"]
    assert s[1]["tip"] == savings.GENERIC[0]       # tanımsız cihaz için genel öneri


def test_suggestions_rank_by_potential_not_bill_share():
    m = pd.DataFrame({"kWh": [1, 1], "TL": [100.0, 60.0]}, index=["fridge", "kettle"])
    assert savings.suggestions(m)[0]["appliance"] == "kettle"   # buzdolabı daha pahalı ama kısılacak yer az


def test_monthly_uses_per_device_days():
    bill = pd.DataFrame({"Tahmin (kWh)": [10.0, 10.0], "Tahmin (TL)": [30.0, 30.0], "Gün": [15.0, 60.0]}, index=["a", "b"])
    m = savings.monthly(bill)
    assert m.loc["a", "TL"] == 60.0 and m.loc["b", "TL"] == 15.0


def test_fit_to_bill_scales_shares_and_leaves_other():
    m = pd.DataFrame({"kWh": [10.0, 20.0], "TL": [30.0, 60.0]}, index=["a", "b"])
    out, other = savings.fit_to_bill(m, house_tl=300.0, user_bill=1300.0, price=3.0)
    assert abs(out.loc["a", "TL"] - 130.0) < 1e-9 and abs(out.loc["b", "TL"] - 260.0) < 1e-9
    assert abs(other - 910.0) < 1e-9 and abs(out.loc["a", "kWh"] - 130.0 / 3) < 1e-9


def test_fit_to_bill_caps_when_devices_exceed_meter():
    m = pd.DataFrame({"kWh": [1.0], "TL": [500.0]}, index=["a"])
    out, other = savings.fit_to_bill(m, house_tl=300.0, user_bill=1000.0, price=3.0)
    assert abs(out["TL"].sum() - 950.0) < 1e-9 and abs(other - 50.0) < 1e-9


def test_target_is_share_of_whole_bill():
    m = pd.DataFrame({"kWh": [100.0], "TL": [100.0]}, index=["kettle"])
    plan, ok, _ = savings.plan_for_target(m, 10, other=900.0)   # 1000 TL'nin %10'u = 100 TL, kettle tavanı %25
    assert not ok
