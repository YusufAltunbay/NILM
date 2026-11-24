"""UK-DALE dosyasında hangi evde hangi cihaz var ve tarih aralıkları ne, listeler."""
from nilm import config
from nilm.data.ukdale import DEFAULT_PATH, appliance_meters, time_range

meters = appliance_meters(DEFAULT_PATH)
for house, apps in sorted(meters.items()):
    a, b = time_range(house)
    print(f"ev {house}: {a:%Y-%m-%d} -> {b:%Y-%m-%d} ({(b - a).days} gün), {len(apps)} cihaz tipi")
    for name in config.APPLIANCES:
        print(f"   {name:16s} {'sayaç ' + str(apps[name]) if name in apps else '-'}")
