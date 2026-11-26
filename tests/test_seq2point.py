import numpy as np
import pytest
import torch

from nilm.models.seq2point import Seq2Point, Seq2PointNet


def test_center_makes_net_invariant_to_constant_offset():
    torch.manual_seed(0)
    net = Seq2PointNet(window=31, hidden=16, center=True).eval()
    x = torch.randn(8, 31)
    torch.testing.assert_close(net(x), net(x + 5.0), atol=1e-5, rtol=1e-5)


def test_without_center_offset_changes_output():
    torch.manual_seed(0)
    net = Seq2PointNet(window=31, hidden=16, center=False).eval()
    x = torch.randn(8, 31)
    assert not torch.allclose(net(x), net(x + 5.0), atol=1e-3)


@pytest.mark.parametrize("center", [False, True])
def test_fit_predict_contract(center):
    from scripts import synthetic
    df = synthetic.make(houses=(1, 2, 5), n=3000)
    k = df[df["appliance"] == "kettle"]
    m = Seq2Point(window=31, stride=5, hidden=16, center=center, epochs=1, verbose=False)
    m.fit(k[k.house == 1], k[k.house == 5])
    agg = k[k.house == 2]["aggregate_w"].to_numpy()
    p = m.predict(agg)
    assert p.shape == agg.shape and (p >= 0).all() and (p <= agg + 1e-6).all()


def test_fit_without_validation_house_uses_block_holdout():
    from scripts import synthetic
    df = synthetic.make(houses=(1, 2), n=40000)
    k = df[df["appliance"] == "kettle"]
    m = Seq2Point(window=31, stride=5, hidden=16, epochs=2, verbose=False).fit(k[k.house == 1])
    assert len(m.history) >= 1 and np.isfinite(m.history[-1]["val_loss"])
    p = m.predict(k[k.house == 2]["aggregate_w"].to_numpy())
    assert len(p) == (k.house == 2).sum()


def test_on_frac_none_still_trains():
    from scripts import synthetic
    df = synthetic.make(houses=(1, 5), n=8000)
    k = df[df["appliance"] == "fridge"]
    m = Seq2Point(window=31, stride=5, hidden=16, on_frac=None, epochs=1, verbose=False)
    m.fit(k[k.house == 1], k[k.house == 5])
    assert len(m.history) == 1


def test_validation_house_without_on_events_falls_back_to_block_holdout(capsys):
    from scripts import synthetic
    df = synthetic.make(houses=(1, 5), n=40000)
    k = df[df["appliance"] == "kettle"].copy()
    val = k[k.house == 5].copy()
    val["appliance_w"] = 0.0  # doğrulama evinde cihaz hiç açılmadı
    m = Seq2Point(window=31, stride=5, hidden=16, epochs=1, verbose=True).fit(k[k.house == 1], val)
    assert "blok ayırılıyor" in capsys.readouterr().out
    assert np.isfinite(m.history[-1]["val_loss"])
