import numpy as np
import pandas as pd
import pytest

from nilm.eval import predictions
from nilm.eval.evaluate import evaluate
from nilm.models.base import MeanModel


def _test_df(n=50, house=2):
    return pd.DataFrame({"timestamp": pd.date_range("2024-01-01", periods=n, freq="6s", tz="UTC"),
                         "house": house, "appliance": "fridge",
                         "aggregate_w": np.full(n, 300.0), "appliance_w": np.full(n, 100.0)})


def test_save_load_roundtrip(tmp_path):
    df = _test_df()
    pred = np.linspace(0, 99, len(df))
    p = predictions.save("m", "washing machine", 2, df, pred, root=tmp_path)
    assert p.name == "m__washing_machine__house2.h5"
    out = predictions.load("m", "washing machine", 2, root=tmp_path)
    assert list(out.columns) == ["timestamp", "aggregate_w", "appliance_w", "pred_w"]
    np.testing.assert_allclose(out["pred_w"], pred, rtol=1e-6)


def test_length_mismatch_rejected(tmp_path):
    with pytest.raises(ValueError):
        predictions.save("m", "fridge", 2, _test_df(), np.zeros(3), root=tmp_path)


def test_evaluate_saves_predictions(tmp_path, monkeypatch):
    monkeypatch.setattr(predictions, "DIR", tmp_path)
    df = _test_df()
    evaluate(MeanModel().fit(df), df, "t", "fridge", log=False, save_preds=True)
    assert (tmp_path / "mean__fridge__house2.h5").exists()
