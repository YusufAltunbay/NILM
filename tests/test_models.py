import numpy as np
import pytest

from scripts import synthetic
from nilm.models.base import MeanModel
from nilm.models.baseline import ThresholdModel

MODELS = [MeanModel, ThresholdModel]


@pytest.fixture(scope="module")
def data():
    df = synthetic.make(houses=(1, 2), n=5000)
    sub = df[df["appliance"] == "kettle"]
    return sub[sub.house == 1], sub[sub.house == 2]


@pytest.mark.parametrize("cls", MODELS)
def test_output_contract(cls, data):
    train, test = data
    agg = test["aggregate_w"].to_numpy()
    p = cls().fit(train).predict(agg)
    assert p.shape == agg.shape
    assert (p >= 0).all()
    assert (p <= agg + 1e-9).all()
    assert np.isfinite(p).all()


def test_threshold_beats_mean_on_f1(data):
    from nilm import config
    from nilm.eval import metrics
    train, test = data
    agg, y = test["aggregate_w"].to_numpy(), test["appliance_w"].to_numpy()
    thr = config.ON_THRESHOLD_W["kettle"]
    f_mean = metrics.f1_on_off(y, MeanModel().fit(train).predict(agg), thr)
    f_thr = metrics.f1_on_off(y, ThresholdModel().fit(train).predict(agg), thr)
    assert f_thr > f_mean


def test_threshold_handles_edge_cases(data):
    train, _ = data
    m = ThresholdModel().fit(train)
    assert m.predict(np.array([100.0])).shape == (1,)
    assert (m.predict(np.full(50, 100.0)) == 0).all()
