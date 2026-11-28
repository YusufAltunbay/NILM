import numpy as np
import pytest

from panel.allocation import UNDEFINED, allocate_other, other_energy_kwh


def test_other_energy_clips_negative_residual():
    agg = np.array([1000.0, 1000.0, 100.0])
    pred = [np.array([400.0, 400.0, 300.0]), np.array([100.0, 100.0, 0.0])]
    # artıklar: 500, 500, max(0, -200)=0 -> 1000 W·adım
    assert other_energy_kwh(agg, pred, 3600) == pytest.approx(1.0)


def test_other_energy_without_predictions_is_total():
    assert other_energy_kwh(np.full(10, 1000.0), [], 360) == pytest.approx(1.0)


def test_allocation_under_budget_keeps_expected_and_remainder():
    a = allocate_other(10.0, {"tv": (100, 4), "ütü": (1000, 0.5)}, days=10)
    assert not a.scaled
    assert a.kwh["tv"] == pytest.approx(4.0)       # 100 W * 4 sa * 10 gün
    assert a.kwh["ütü"] == pytest.approx(5.0)
    assert a.kwh[UNDEFINED] == pytest.approx(1.0)


def test_allocation_over_budget_scales_proportionally():
    a = allocate_other(3.0, {"tv": (100, 4), "ütü": (1000, 0.5)}, days=10)  # beklenen 4 ve 5
    assert a.scaled
    assert a.kwh["tv"] == pytest.approx(3.0 * 4 / 9)
    assert a.kwh["ütü"] == pytest.approx(3.0 * 5 / 9)
    assert a.kwh[UNDEFINED] == 0.0


@pytest.mark.parametrize("e", [0.0, 2.0, 50.0])
def test_total_is_conserved(e):
    a = allocate_other(e, {"a": (100, 3), "b": (500, 1)}, days=7)
    assert sum(a.kwh.values()) == pytest.approx(e)


def test_no_devices_everything_undefined():
    a = allocate_other(4.2, {}, days=3)
    assert a.kwh == {UNDEFINED: pytest.approx(4.2)}


def test_tl_conversion_and_validation():
    a = allocate_other(2.0, {}, days=1)
    assert a.tl(3.24)[UNDEFINED] == pytest.approx(6.48)
    with pytest.raises(ValueError):
        allocate_other(-1.0, {}, days=1)
