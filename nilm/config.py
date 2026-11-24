# Ekipçe kesinleştirilecek cihaz listesi (UK-DALE etiket adları)
APPLIANCES = ["fridge", "washing machine", "kettle", "dish washer", "microwave"]

SAMPLE_PERIOD_S = 6          # UK-DALE yeniden örnekleme aralığı
TL_PER_KWH = 3.0             # birim fiyat (güncellenecek)
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
