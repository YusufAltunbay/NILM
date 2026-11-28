import pandas as pd
from panel import theme


def _bill(real, pred):
    idx = ["fridge", "kettle"]
    return pd.DataFrame({"Gerçek (TL)": real, "Tahmin (TL)": pred}, index=idx)


def test_summary_over_prediction():
    s = theme.summary_sentence(_bill([100.0, 50.0], [110.0, 70.0]))
    assert "%" in s and "fazla" in s
    assert "Su ısıtıcısı" in s          # en büyük sapma (+20 TL)
    assert "Buzdolabı" in s             # en yakın tahmin (%10 sapma)


def test_summary_under_prediction():
    s = theme.summary_sentence(_bill([100.0, 50.0], [90.0, 40.0]))
    assert "eksik" in s


def test_summary_exact():
    s = theme.summary_sentence(_bill([100.0, 50.0], [100.0, 50.0]))
    assert "neredeyse tam" in s


def test_tr_and_color_known_and_unknown():
    assert theme.tr("fridge") == "Buzdolabı"
    assert theme.tr("toaster") == "Toaster"
    assert theme.color("toaster").startswith("#")


def test_ordered_keeps_unknown_appliances():
    from panel import theme
    assert theme.ordered(["tv", "kettle", "fridge"]) == ["fridge", "kettle", "tv"]
    assert theme.color("tv") == theme.color("tv")  # çalıştırmalar arasında kararlı


def test_build_cache_downsamples_and_keeps_energy(tmp_path):
    import numpy as np
    from nilm.eval import predictions
    from panel import data
    n = 3000
    ts = pd.Series(pd.date_range("2013-05-01", periods=n, freq="6s", tz="UTC"))
    test = pd.DataFrame({"timestamp": ts, "aggregate_w": np.full(n, 500.0), "appliance_w": np.r_[np.zeros(1000), np.full(n - 1000, 120.0)]})
    for model in ("mean", "seq2point"):
        for h in (2, 5):
            predictions.save(model, "washing machine", h, test, test["appliance_w"].to_numpy() * 0.9, root=tmp_path)
    cache = tmp_path / "c.parquet"
    pred = data.build_cache(tmp_path, cache=cache)
    assert set(pred["model"]) == {"mean", "seq2point"} and set(pred["house"]) == {2, 5}
    g = pred[(pred["model"] == "mean") & (pred["house"] == 2)]
    assert len(g) == n * 6 // 60
    # enerji korunur
    assert abs(g["appliance_w"].sum() * 60 - test["appliance_w"].sum() * 6) < 1e-3 * test["appliance_w"].sum() * 6
    # ikinci çağrı diskteki önbellekten okur
    mt = cache.stat().st_mtime_ns
    data.build_cache(tmp_path, cache=cache)
    assert cache.stat().st_mtime_ns == mt


def test_house_names_and_model_order():
    from panel import data
    assert "görülmeyen" in data.house_name(2) and "doğrulama" in data.house_name(5)
    assert data.model_order(["BERT4NILM (Transformer)", "Ortalama modeli", "x"]) == ["Ortalama modeli", "BERT4NILM (Transformer)", "x"]


def test_bill_with_other_adds_up_to_meter():
    import numpy as np
    from panel import data
    ts = pd.date_range("2013-05-01", periods=100, freq="60s", tz="UTC")
    rows = []
    for a, w in (("kettle", 100.0), ("fridge", 50.0)):
        rows.append(pd.DataFrame({"timestamp": ts, "appliance": a, "aggregate_w": 400.0, "appliance_w": w, "predicted_w": w * 1.2}))
    sub = pd.concat(rows, ignore_index=True)
    b = data.bill_from(sub, 60, 3.0, other=True)
    assert list(b.index) == ["fridge", "kettle", "other"]
    meter = 400.0 * 100 * 60 / 3600 / 1000 * 3.0
    assert abs(b["Gerçek (TL)"].sum() - meter) < 1e-9 and abs(b["Tahmin (TL)"].sum() - meter) < 1e-9
    m = data.to_month(b)
    assert np.allclose(m["Gün"], 30.0)
