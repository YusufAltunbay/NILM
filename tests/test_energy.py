import numpy as np
import pandas as pd
import pytest

from nilm.eval import energy

DT = 6
PER_DAY = 86400 // DT


def _frame(days, y_w, p_w, start="2024-01-01", pred_col="predicted_w", drop=None):
    ts = pd.date_range(start, periods=days * PER_DAY, freq=f"{DT}s", tz="UTC")
    df = pd.DataFrame({"timestamp": ts, "appliance_w": float(y_w), pred_col: float(p_w)})
    if drop is not None:
        df = df.drop(index=df.index[drop])
    return df.reset_index(drop=True)


def test_daily_energy_values():
    out = energy.daily_energy(_frame(3, 1000, 900), price=3.0)
    assert len(out) == 3
    assert out["true_kwh"].tolist() == pytest.approx([24.0] * 3)      # 1 kW x 24 sa
    assert out["pred_kwh"].tolist() == pytest.approx([21.6] * 3)
    assert out["err_kwh"].tolist() == pytest.approx([-2.4] * 3)       # eksik tahmin: negatif
    assert out["abs_err_tl"].tolist() == pytest.approx([7.2] * 3)     # 2.4 kWh x 3 TL
    assert (out["coverage"] == 1.0).all()


def test_pred_w_alias_is_accepted():
    out = energy.daily_energy(_frame(2, 500, 500, pred_col="pred_w"))
    assert len(out) == 2 and out["abs_err_kwh"].max() == pytest.approx(0.0)


def test_missing_prediction_column_raises():
    df = _frame(1, 1, 1).drop(columns="predicted_w")
    with pytest.raises(KeyError):
        energy.daily_energy(df)


def test_incomplete_day_is_dropped_by_default_and_kept_when_asked():
    df = _frame(2, 1000, 1000, drop=slice(0, PER_DAY // 2))  # ilk günün yarısı yok
    assert len(energy.daily_energy(df)) == 1
    kept = energy.daily_energy(df, min_coverage=0.0)
    assert len(kept) == 2 and kept["coverage"].min() == pytest.approx(0.5)


def test_weekly_blocks_start_at_first_day():
    out = energy.weekly_energy(_frame(15, 100, 100))
    assert len(out) == 2                      # 15 gün = 2 tam hafta + 1 gün (atılır)
    assert out["true_kwh"].tolist() == pytest.approx([100 * 7 * 24 / 1000] * 2)
    assert out["period_start"].iloc[1] - out["period_start"].iloc[0] == pd.Timedelta(days=7)


def test_timezone_naive_timestamps_work():
    df = _frame(2, 1000, 1000)
    df["timestamp"] = df["timestamp"].dt.tz_localize(None)
    assert len(energy.daily_energy(df)) == 2


def test_empty_frame_and_summary():
    empty = pd.DataFrame({"timestamp": pd.to_datetime([]), "appliance_w": [], "predicted_w": []})
    out = energy.daily_energy(empty)
    assert out.empty and list(out.columns) == energy.OUT_COLUMNS
    s = energy.summarize(out)
    assert s["n_periods"] == 0 and np.isnan(s["mae_tl"])


def test_summarize_relative_error():
    out = energy.daily_energy(_frame(4, 1000, 900), price=1.0)
    s = energy.summarize(out)
    assert s["n_periods"] == 4
    assert s["mae_kwh"] == pytest.approx(2.4) and s["true_kwh_mean"] == pytest.approx(24.0)
    assert s["rel_err"] == pytest.approx(0.1)
    assert np.isnan(energy.summarize(energy.daily_energy(_frame(1, 0, 0)))["rel_err"])  # gerçek enerji 0


def test_invalid_arguments():
    with pytest.raises(ValueError):
        energy.period_energy(_frame(1, 1, 1), days=0)
    with pytest.raises(ValueError):
        energy.period_energy(_frame(1, 1, 1), min_coverage=1.5)
