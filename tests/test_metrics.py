import math
import numpy as np
import pytest
from nilm.eval import metrics


def test_mae_basic():
    assert metrics.mae([0, 100], [0, 50]) == 25.0


def test_mae_perfect():
    assert metrics.mae([1, 2, 3], [1, 2, 3]) == 0.0


def test_sae_basic():
    # gerçek toplam 100, tahmin toplam 110 -> %10
    assert metrics.sae([50, 50], [60, 50]) == pytest.approx(0.10)


def test_sae_cancelling_errors_is_zero():
    # SAE toplam enerjiye bakar: +10 ve -10 hata birbirini götürür
    assert metrics.sae([50, 50], [60, 40]) == 0.0


def test_sae_zero_truth_is_nan():
    assert math.isnan(metrics.sae([0, 0], [5, 5]))


def test_f1_perfect_and_worst():
    y = np.array([0, 100, 100, 0.0])
    assert metrics.f1_on_off(y, y) == 1.0
    assert metrics.f1_on_off(y, np.zeros(4)) == 0.0


def test_f1_known_value():
    y = np.array([100, 100, 0, 0.0])
    p = np.array([100, 0, 100, 0.0])   # tp=1, fp=1, fn=1 -> 2/4
    assert metrics.f1_on_off(y, p) == pytest.approx(0.5)


def test_f1_threshold_matters():
    y = np.array([30, 30, 0.0])
    assert metrics.f1_on_off(y, y, threshold_w=15) == 1.0
    assert metrics.f1_on_off(y, y, threshold_w=50) == 1.0  # hiç açık yok, tahmin de yok
    assert metrics.f1_on_off(y, np.array([30, 30, 60.0]), threshold_w=50) == 0.0


def test_f1_never_on_and_no_prediction():
    z = np.zeros(5)
    assert metrics.f1_on_off(z, z) == 1.0


def test_energy_and_bill():
    # 1000 W, 3600 örnek x 1 s = 1 kWh
    x = np.full(3600, 1000.0)
    assert metrics.energy_kwh(x, 1) == pytest.approx(1.0)
    assert metrics.bill_tl(x, 1, 3.0) == pytest.approx(3.0)


def test_tl_error():
    y = np.full(3600, 1000.0)
    p = np.full(3600, 1500.0)
    assert metrics.tl_error(y, p, 1, 3.0) == pytest.approx(1.5)


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        metrics.mae([1, 2, 3], [1, 2])


def test_nan_raises():
    with pytest.raises(ValueError):
        metrics.mae([1, float("nan")], [1, 2])


def test_empty_raises():
    with pytest.raises(ValueError):
        metrics.sae([], [])
