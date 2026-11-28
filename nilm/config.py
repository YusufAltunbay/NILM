# Ekipçe kesinleştirilecek cihaz listesi (UK-DALE etiket adları)
APPLIANCES = ["fridge", "washing machine", "kettle", "dish washer", "microwave"]

# UK-DALE evlerde aynı cihazı farklı adlarla kaydediyor; bunlar tek cihaz sayılır.
APPLIANCE_ALIASES = {
    "fridge": ["fridge", "fridge freezer"],
    "washing machine": ["washing machine", "washer dryer"],
}

# Cihaz gücü üst sınırı (W). Buzdolabının kompresör kalkışında tek örneklik
# 1-2 kW tepeleri var; gerçek ama bilgi taşımıyor ve ölçeklemeyi bozuyor.
# Değerler seq2point (Zhang vd., 2018) UK-DALE ayarlarıyla uyumlu.
MAX_POWER_W = {
    "fridge": 300.0,
    "washing machine": 2500.0,
    "kettle": 3100.0,
    "dish washer": 2500.0,
    "microwave": 3000.0,
}

# Bu değerin altı 0 sayılır (bekleme/sayaç ofseti). Ev 5 mikrodalga sayacı
# Temmuz 2014'ten itibaren zamanın %90'ında sabit 50 W gösteriyor.
STANDBY_W = {
    "microwave": 100.0,
}

SAMPLE_PERIOD_S = 6          # UK-DALE yeniden örnekleme aralığı
TL_PER_KWH = 3.24            # Nisan 2026 mesken tarifesi: 100 kWh = 323,8 TL (ortalama)
TRAIN_HOUSES = [1, 3, 4]
VAL_HOUSES = [5]
UNSEEN_HOUSES = [2]          # hiç görülmeyen ev

# Cihaz bazlı AÇIK/KAPALI eşikleri (W). F1 hesabında kullanılır.
# Değerler NILM literatüründeki UK-DALE ayarlarına yakındır; ekipçe doğrulanacak.
ON_THRESHOLD_W = {
    "fridge": 50.0,
    "washing machine": 20.0,
    "kettle": 2000.0,
    "dish washer": 10.0,
    "microwave": 200.0,
}
DEFAULT_ON_THRESHOLD_W = 15.0
