import pandas as pd

from nilm.models.params import PARAMS, params
from scripts import run_eval


def test_params_returns_copy_and_default_empty():
    assert params("seq2point", "microwave") == {"hidden": 256}
    p = params("seq2point", "microwave")
    p["hidden"] = 1
    assert PARAMS[("seq2point", "microwave")] == {"hidden": 256}  # tablo bozulmaz
    assert params("seq2point", "kettle") == {}
    assert params("mean", "fridge") == {}


def _table(path):
    rows = [dict(model=m, dataset="processed:house2(unseen)", appliance=a, mae=1.0, sae=0.1, f1=0.5,
                 tl_error=2.0, predict_ms=3.0)
            for m in ("mean", "seq2point") for a in ("fridge", "microwave", "kettle")]
    pd.DataFrame(rows).to_csv(path, index=False)


def test_replace_rows_removes_only_selected_model_and_appliance(tmp_path):
    f = tmp_path / "results.csv"
    _table(f)
    bak = run_eval.replace_rows(["seq2point"], ["microwave", "kettle"], f)
    left = pd.read_csv(f)
    assert len(left) == 4
    assert not ((left.model == "seq2point") & left.appliance.isin(["microwave", "kettle"])).any()
    assert ((left.model == "mean") & (left.appliance == "microwave")).any()  # başka model dokunulmadı
    assert ((left.model == "seq2point") & (left.appliance == "fridge")).any()  # başka cihaz dokunulmadı
    assert len(pd.read_csv(bak)) == 6  # yedek özgün tablo


def test_replace_rows_without_file_is_noop(tmp_path):
    assert run_eval.replace_rows(["mean"], ["fridge"], tmp_path / "yok.csv") is None


def test_run_filters_appliances(tmp_path):
    from scripts import synthetic
    df = synthetic.make(houses=(1, 2, 5), n=3000)
    out = run_eval.run(df, "synthetic", ["mean"], log=False, appliances=["kettle"])
    assert set(out["appliance"]) == {"kettle"}
    assert len(out) == 2  # ev 2 ve ev 5
