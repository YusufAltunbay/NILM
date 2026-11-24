import numpy as np
import pandas as pd
import pytest
from nilm.eval import predictions
from scripts import run_eval, synthetic


def _test_frame(n=5):
    return pd.DataFrame({"timestamp": pd.date_range("2024-01-01", periods=n, freq="6s", tz="UTC"),
                         "house": 2, "appliance": "fridge",
                         "aggregate_w": np.arange(n) + 100.0, "appliance_w": np.arange(n) * 1.0})


def test_roundtrip(tmp_path):
    f = predictions.to_frame(_test_frame(), np.arange(5) * 2.0)
    predictions.save("mean", f, tmp_path)
    back = predictions.load_all(tmp_path)
    assert list(back["model"].unique()) == ["mean"]
    assert back["predicted_w"].tolist() == [0.0, 2.0, 4.0, 6.0, 8.0]
    assert set(predictions.COLUMNS) <= set(back.columns)


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        predictions.to_frame(_test_frame(5), np.zeros(4))


def test_load_all_empty(tmp_path):
    assert predictions.load_all(tmp_path / "yok").empty


def test_run_eval_writes_predictions(tmp_path, monkeypatch):
    monkeypatch.setattr(predictions, "PRED_DIR", tmp_path)
    df = synthetic.make(n=500)
    out = run_eval.run(df, "synthetic", ["mean"], log=False)
    pred = predictions.load_all(tmp_path)
    assert len(out) == 5                       # 5 cihaz x test evi 2
    assert set(pred["house"]) == {2}           # yalnızca test evi yazılır
    assert len(pred) == 5 * 500
