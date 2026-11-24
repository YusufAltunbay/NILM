import pandas as pd
import pytest
from panel import charts


@pytest.fixture
def bill():
    return pd.DataFrame({"Gerçek (TL)": [45.0, 42.0, 21.0], "Tahmin (TL)": [44.0, 55.0, 34.0],
                         "Gerçek (kWh)": [13.0, 12.0, 6.0], "Tahmin (kWh)": [13.0, 16.0, 10.0], "Hata (TL)": [1.0, 13.0, 13.0]},
                        index=["fridge", "washing machine", "kettle"])


@pytest.mark.parametrize("fn", [charts.ribbon, charts.stacked, charts.donut, charts.bars])
def test_bill_charts_build_valid_specs(fn, bill):
    assert fn(bill).to_dict()  # geçersiz Vega-Lite şeması hata verir


def test_series_and_residual(bill):
    ts = pd.date_range("2024-01-01", periods=50, freq="6s", tz="UTC")
    df = pd.DataFrame({"timestamp": ts, "Gerçek": range(50), "Tahmin": range(50), "Toplam": range(50)})
    bands = pd.DataFrame({"start": [ts[3]], "end": [ts[9]]})
    assert charts.series(df, "fridge", True, bands).to_dict()
    assert charts.residual(df).to_dict()


def test_rank_and_heatmap_single_and_multi_model():
    r = pd.DataFrame({"appliance": ["fridge", "kettle"] * 2, "model": ["a", "a", "b", "b"], "mae": [10.0, 5.0, 8.0, 9.0]})
    ozet = r.groupby("model")[["mae"]].mean().reset_index().rename(columns={"model": "Model"})
    assert charts.rank_bars(ozet, "mae", "MAE", True).to_dict()
    assert charts.heatmap(r, "mae", "MAE", True).to_dict()
    assert charts.heatmap(r[r["model"] == "a"], "mae", "MAE", True).to_dict()   # tek model
    assert charts.model_bars(r, "mae", "MAE").to_dict()
