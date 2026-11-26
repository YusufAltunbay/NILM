import numpy as np
import pytest
import torch

from nilm.models.bert4nilm import Bert4Nilm, Bert4NilmNet


@pytest.mark.parametrize("window", [31, 32, 481])
def test_net_output_shape_matches_window(window):
    net = Bert4NilmNet(window=window, hidden=16, layers=1, heads=2).eval()
    assert net(torch.randn(3, window)).shape == (3, window)


def test_center_makes_net_invariant_to_constant_offset():
    torch.manual_seed(0)
    net = Bert4NilmNet(window=31, hidden=16, layers=1, heads=2, center=True).eval()
    x = torch.randn(4, 31)
    torch.testing.assert_close(net(x), net(x + 5.0), atol=1e-4, rtol=1e-4)


def _small(**kw):
    return Bert4Nilm(window=31, hidden=16, layers=1, heads=2, train_batch=16, epochs=2,
                     verbose=False, **kw)


def _kettle(houses, n):
    from scripts import synthetic
    df = synthetic.make(houses=houses, n=n)
    return df[df["appliance"] == "kettle"]


def test_fit_predict_contract():
    k = _kettle((1, 2, 5), 6000)
    m = _small().fit(k[k.house == 1], k[k.house == 5])
    agg = k[k.house == 2]["aggregate_w"].to_numpy()
    p = m.predict(agg)
    assert p.shape == agg.shape and (p >= 0).all() and (p <= agg.astype("float32")).all() and np.isfinite(p).all()
    assert len(m.history) >= 1


@pytest.mark.parametrize("n", [1, 10, 31, 32, 100])
def test_predict_handles_short_and_odd_lengths(n):
    k = _kettle((1, 5), 6000)
    m = _small().fit(k[k.house == 1], k[k.house == 5])
    agg = np.full(n, 500.0)
    assert m.predict(agg).shape == (n,)


def test_predict_empty():
    k = _kettle((1, 5), 6000)
    m = _small().fit(k[k.house == 1], k[k.house == 5])
    assert len(m.predict(np.array([]))) == 0


def test_fit_without_validation_house_uses_block_holdout():
    k = _kettle((1, 2), 40000)
    m = _small().fit(k[k.house == 1])
    assert np.isfinite(m.history[-1]["val_loss"])


def test_validation_house_without_on_events_falls_back_to_block_holdout(capsys):
    from scripts import synthetic
    df = synthetic.make(houses=(1, 5), n=40000)
    k = df[df["appliance"] == "kettle"].copy()
    val = k[k.house == 5].copy()
    val["appliance_w"] = 0.0
    m = Bert4Nilm(window=31, hidden=16, layers=1, heads=2, train_batch=16, epochs=1, verbose=True)
    m.fit(k[k.house == 1], val)
    assert "blok ayırılıyor" in capsys.readouterr().out


def test_predict_before_fit_raises():
    with pytest.raises(RuntimeError):
        Bert4Nilm(window=31).predict(np.ones(50))
