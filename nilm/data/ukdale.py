"""UK-DALE (NILMTK HDF5 biçimi) okuyucu -> ortak veri biçimi.

Dosya yapısı: /building{n}/elec/meter{m}; cihaz-sayaç eşlemesi her
binanın 'metadata' özniteliğinde tutulur. Ana sayaç (toplam) meter1'dir.
"""
from pathlib import Path

import pandas as pd
import tables

from nilm import config

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "raw" / "ukdale.h5"


def appliance_meters(path=DEFAULT_PATH) -> dict:
    """{ev: {cihaz: [sayaç numaraları]}}

    config.APPLIANCE_ALIASES'taki adlar tek cihaz altında toplanır. Birden fazla
    seçili cihazı birlikte ölçen sayaçlar (örn. ev 4'te çamaşır makinesi +
    mikrodalga tek sayaçta) belirsiz olduğu için o cihazlardan çıkarılır.
    """
    canon = {alias: name for name, aliases in config.APPLIANCE_ALIASES.items()
             for alias in aliases}
    out = {}
    with tables.open_file(str(path), "r") as h5:
        for node in h5.root._v_children.values():
            if not node._v_name.startswith("building"):
                continue
            house = int(node._v_name.removeprefix("building"))
            m = {}
            for app in node._v_attrs["metadata"].get("appliances", []):
                name = canon.get(app["type"], app["type"])
                m.setdefault(name, set()).update(app["meters"])
            selected = [a for a in config.APPLIANCES if a in m]
            shared = {mt for a in selected for b in selected if a < b for mt in m[a] & m[b]}
            out[house] = {a: sorted(ms - shared) for a, ms in m.items() if ms - shared}
    return out


def _read_power(h5, house, meter, start=None, end=None) -> pd.Series:
    """Sayaç tablosunu doğrudan PyTables ile okur.

    Dosya pandas 0.15 ile yazıldığından güncel pandas.HDFStore açamıyor;
    tablo yapısı: index (UTC ns) + values_block_0 (sütunlar non_index_axes'te).
    """
    node = h5.get_node(f"/building{house}/elec/meter{meter}")
    cols = [tuple(c) for c in node._v_attrs["non_index_axes"][0][1]]
    for want in [("power", "active"), ("power", "apparent")]:
        if want in cols:
            j = cols.index(want)
            break
    else:
        raise KeyError(f"ev {house} sayaç {meter}: güç sütunu yok ({cols})")
    t = node.table
    cond = []
    if start is not None:
        cond.append(f"(index >= {pd.Timestamp(start, tz='UTC').value})")
    if end is not None:
        cond.append(f"(index < {pd.Timestamp(end, tz='UTC').value})")
    rows = t.read_where(" & ".join(cond)) if cond else t.read()
    idx = pd.to_datetime(rows["index"], utc=True)
    return pd.Series(rows["values_block_0"][:, j], index=idx, dtype="float32")


def time_range(house, path=DEFAULT_PATH):
    """Ana sayacın ilk ve son zaman damgası."""
    with tables.open_file(str(path), "r") as h5:
        t = h5.get_node(f"/building{house}/elec/meter1").table
        return (pd.Timestamp(t.cols.index[0], tz="UTC"),
                pd.Timestamp(t.cols.index[t.nrows - 1], tz="UTC"))


def load(house, appliance, path=DEFAULT_PATH, start=None, end=None,
         period_s=config.SAMPLE_PERIOD_S) -> pd.DataFrame:
    """Bir ev ve cihaz için toplam + cihaz gücünü ortak biçimde döndürür."""
    meters = appliance_meters(path)[house].get(appliance)
    if not meters:
        raise ValueError(f"ev {house} içinde '{appliance}' yok")
    rule = f"{period_s}s"
    with tables.open_file(str(path), "r") as h5:
        agg = _read_power(h5, house, 1, start, end).resample(rule).mean()
        app = sum(_read_power(h5, house, m, start, end).resample(rule).mean()
                  for m in meters)
    df = pd.concat({"aggregate_w": agg, "appliance_w": app}, axis=1)
    df = df.rename_axis("timestamp").reset_index()
    df["house"], df["appliance"] = house, appliance
    return df  # boşluklar NaN olarak kalır; prep.clean doldurur/atar
