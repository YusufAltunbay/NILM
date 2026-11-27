import numpy as np
import pandas as pd
import pytest

from scripts import seed_ozeti


def _run(model, app, seed, ev2_mae, kaynak="deney"):
    r = dict(model=model, appliance=app, seed=seed, kaynak=kaynak)
    for tag in ("ev2", "val5"):
        r[f"{tag}_mae"], r[f"{tag}_f1"], r[f"{tag}_tl"] = ev2_mae, 0.5, 10.0
    return r


def test_summarize_mean_and_std_across_seeds():
    runs = pd.DataFrame([_run("seq2point", "kettle", s, v) for s, v in enumerate([6.0, 8.0, 10.0])])
    s = seed_ozeti.summarize_runs(runs).iloc[0]
    assert s["n_seed"] == 3
    assert s["ev2_mae_ort"] == pytest.approx(8.0)
    assert s["ev2_mae_std"] == pytest.approx(2.0)  # ddof=1


def test_single_seed_has_nan_std_and_dash_in_markdown():
    runs = pd.DataFrame([_run("bert4nilm", "fridge", 0, 5.0, kaynak="resmi")])
    summ = seed_ozeti.summarize_runs(runs)
    assert np.isnan(summ.iloc[0]["ev2_mae_std"])
    assert "5.0" in seed_ozeti.markdown(summ) and "±" not in seed_ozeti.markdown(summ).split("\n")[2]


def test_missing_tl_shows_dash():
    r = _run("seq2point", "fridge", 1, 5.0)
    r["ev2_tl"] = np.nan
    summ = seed_ozeti.summarize_runs(pd.DataFrame([r]))
    line = seed_ozeti.markdown(summ).split("\n")[2]
    assert " - " in line


def test_collect_merges_official_seed0_with_experiment_seeds(tmp_path):
    res = pd.DataFrame([dict(model="seq2point", dataset=f"processed:house{h}({k})", appliance="kettle",
                             mae=1.0, sae=0.1, f1=0.9, tl_error=2.0, predict_ms=3.0)
                        for h, k in ((2, "unseen"), (5, "val"))])
    exp = pd.DataFrame([dict(model="seq2point", cihaz="kettle", seed=1, notlar="seed-turu",
                             ev2_mae=2.0, ev2_f1=0.8, ev2_tl=4.0, val5_mae=3.0, val5_f1=0.7, val5_tl=6.0),
                        dict(model=np.nan, cihaz="fridge", seed=1, notlar="center-lr3e-4-seed1",
                             ev2_mae=9.0, ev2_f1=0.8, ev2_tl=np.nan, val5_mae=9.0, val5_f1=0.7, val5_tl=np.nan),
                        dict(model="seq2point", cihaz="kettle", seed=0, notlar="baska-deney",
                             ev2_mae=99.0, ev2_f1=0.0, ev2_tl=0.0, val5_mae=99.0, val5_f1=0.0, val5_tl=0.0)])
    res.to_csv(tmp_path / "r.csv", index=False)
    exp.to_csv(tmp_path / "e.csv", index=False)
    runs = seed_ozeti.collect(tmp_path / "r.csv", tmp_path / "e.csv")
    kettle = runs[runs.appliance == "kettle"]
    assert sorted(kettle.seed) == [0, 1]                       # seed 0 resmi, seed 1 deney; 'baska-deney' alınmadı
    assert kettle[kettle.seed == 0].iloc[0]["ev2_mae"] == 1.0  # resmi tablo kazanır
    fridge = runs[runs.appliance == "fridge"].iloc[0]
    assert fridge["model"] == "seq2point" and fridge["kaynak"] == "eski örnekleme"
