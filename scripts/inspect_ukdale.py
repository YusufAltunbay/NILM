"""UK-DALE dosyasında hangi evde hangi cihaz var ve tarih aralıkları ne, listeler."""
import pandas as pd
from nilm import config
from nilm.data.ukdale import DEFAULT_PATH, appliance_meters

meters = appliance_meters(DEFAULT_PATH)
with pd.HDFStore(str(DEFAULT_PATH), "r") as store:
    for house, apps in sorted(meters.items()):
        idx = store.select(f"/building{house}/elec/meter1", columns=[]).index
        print(f"ev {house}: {idx.min():%Y-%m-%d} -> {idx.max():%Y-%m-%d}, {len(apps)} cihaz tipi")
        for a in config.APPLIANCES:
            print(f"   {a:16s} {'sayaç ' + str(apps[a]) if a in apps else '-'}")
