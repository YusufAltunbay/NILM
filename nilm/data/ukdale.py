"""UK-DALE (NILMTK HDF5 biçimi) okuyucu -> ortak veri biçimi.

Dosya yapısı: /building{n}/elec/meter{m}; cihaz-sayaç eşlemesi her
binanın 'metadata' özniteliğinde tutulur. Ana sayaç (toplam) meter1'dir.
"""
from pathlib import Path

import pandas as pd
import tables

from nilm import config
from nilm.data.schema import validate

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "raw" / "ukdale.h5"


def appliance_meters(path=DEFAULT_PATH) -> dict:
    """{ev: {cihaz_tipi: [sayaç numaraları]}}"""
    out = {}
    with tables.open_file(str(path), "r") as h5:
        for node in h5.root._v_children.values():
            if not node._v_name.startswith("building"):
                continue
            house = int(node._v_name.removeprefix("building"))
            meta = node._v_attrs["metadata"]
            m = {}
            for app in meta.get("appliances", []):
                m.setdefault(app["type"], []).extend(app["meters"])
            out[house] = m
    return out


def _read_power(store, house, meter) -> pd.Series:
    df = store[f"/building{house}/elec/meter{meter}"]
    for col in [("power", "active"), ("power", "apparent")]:
        if col in df.columns:
            return df[col].astype("float32")
    raise KeyError(f"ev {house} sayaç {meter}: güç sütunu yok ({list(df.columns)})")


def load(house, appliance, path=DEFAULT_PATH, start=None, end=None,
         period_s=config.SAMPLE_PERIOD_S) -> pd.DataFrame:
    """Bir ev ve cihaz için toplam + cihaz gücünü ortak biçimde döndürür."""
    meters = appliance_meters(path)[house].get(appliance)
    if not meters:
        raise ValueError(f"ev {house} içinde '{appliance}' yok")
    with pd.HDFStore(str(path), "r") as store:
        agg = _read_power(store, house, 1)
        app = sum(_read_power(store, house, m) for m in meters)
    rule = f"{period_s}s"
    agg = agg[start:end].resample(rule).mean()
    app = app[start:end].resample(rule).mean()
    df = pd.concat({"aggregate_w": agg, "appliance_w": app}, axis=1)
    df = df.rename_axis("timestamp").reset_index()
    df["house"], df["appliance"] = house, appliance
    return df  # boşluklar NaN olarak kalır; prep.clean doldurur/atar
