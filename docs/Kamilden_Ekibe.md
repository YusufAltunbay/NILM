Yusuf, Ersin, panel Ersin'in gerçek tahminleriyle çalışıyor ve `kamil/degerlendirme` dalında güncel. Özet, nasıl açacağınız ve sizden ricalarım aşağıda.

NE VAR

* Panel 6 sayfa:
  * Nasıl çalışır: sayaç → model → cihazlar → fatura akışı ve bir günün sayaçtan cihazlara ayrılması (gerçek ya da model tahmini). Sunuma bununla başlayalım.
  * Fatura dağılımı: iki görünüm. "Benim faturam": giriş yapan kullanıcı aylık faturasını girer, panel bunu modelin örnek evdeki ayrımına göre cihazlara böler (tahmini). "Model doğruluğu": örnek evde gerçek ölçüm ile modelin tahmini, aylık ortalama; sayaç toplamı = 5 cihaz + "Diğer cihazlar".
  * Zaman serisi: gerçek güç ve 4 modelin tahmini aynı grafikte, pencere seçimli.
  * Model karşılaştırma: genel sıralama, ölçüt karnesi, cihaz cihaz ölçütler (results.csv'den).
  * Tasarruf: kullanıcı kendi faturasını girer, cihaz payları örnek evden ölçeklenir, senaryo ve hedef planı.
  * Görülmeyen ev: yalnızca ev 2. Bu sayfa model değerlendirmesi için; yalnızca misafir girişinde görünür.
* Model adları: Ortalama modeli, Eşik modeli, seq2point (CNN), BERT4NILM (Transformer).
* Ev 2 "görülmeyen", ev 5 "doğrulama" diye etiketli (Ersin'in notuna göre).
* Kullanıcı hesabı veri setindeki örnek bir sayaca (ev 2) bağlanır; gerçek kullanımda bunun yerine kullanıcının kendi sayacı bağlanır. Kullanıcı görünümünde sayfalar bu sayaç için, "Benim faturam" ise kullanıcının girdiği faturaya göre.
* Giriş: kullanıcı adı ve parola (yerel SQLite, `.panel/users.db`, Git'e gitmez). "Misafir olarak devam et" tüm evleri ve tüm sayfaları gösterir (sunum için). Oturum tarayıcı çerezinde 30 gün saklanır, sayfa yenilenince (F5) giriş korunur. Yeni hesap örnek evle (ev 2) açılır, panelde "Ali'nin evi" diye görünür. Kayıtta aylık fatura isteğe bağlı girilir; Fatura dağılımı ve Tasarruf sayfalarından da değiştirilebilir, hesaba kaydedilir.
* Kullanıcı verisi yüklenmiyor. Ersin'in gerekçesiyle aynı fikirdeyim: gerçek cihaz tüketimi olmadan doğruluk ölçülemez.
* Testler: `py -m pytest -q` → 120 test geçiyor.

ADIMLAR

1. Dalı alın:
   git fetch origin
   git checkout kamil/degerlendirme
   git pull
2. Tahmin dosyaları (Ersin'in Drive zip'i) `results\predictions\` içinde olmalı, 40 adet `.h5`. Kontrol:
   dir /b results\predictions\*.h5 | find /c ".h5"
3. Gerekli paketler: `py -m pip install -r requirements.txt` (torch için CPU sürümü yeter: `py -m pip install torch --index-url https://download.pytorch.org/whl/cpu`).
4. Paneli açın:
   py -m streamlit run panel/app.py
   İlk açılışta "Veri yükleniyor" 10-20 sn sürer: 76 milyon satırlık tahminler bir kez dakikalık ortalamaya indirilip `.panel/tahmin_dakikalik.parquet` dosyasına yazılır (~80 MB, Git'e gitmez). Sonraki açılışlar hızlıdır. Tahmin dosyaları değişirse önbellek kendiliğinden yenilenir.

GÖZDEN GEÇİRMENİZİ İSTEDİKLERİM

* PR #2 (`kamil/degerlendirme` → `main`): main'deki son değişiklikleri (Ersin'in PR #22, #23) dalıma birleştirdim, çakışma yok. Bakıp onaylarsanız main'e alalım. Yusuf, main korumalı olduğu için onay sende.
* Ersin: panel tahminleri yalnızca `nilm.eval.predictions.available()` / `path()` ile okuyor. Dosya adı ya da sütun biçimini değiştirirsen haber ver.
* Ersin: "Nasıl çalışır" sayfasındaki model açıklamaları (bir cümlelik) doğru mu, bak lütfen. Dosya: `panel/views/nasil_calisir.py`, `DESC` sözlüğü.
* Yusuf: "Nasıl çalışır" sayfasında UK-DALE ve evlerin rolleri anlatılıyor. Eksik ya da yanlış bir şey varsa söyle.

SIRADA OLANLAR (panel tarafı, ben yapıyorum)

* "Evimdeki diğer cihazlar": Ersin'in `panel/allocation.py` dosyasıyla, "tahmini dağılım" etiketiyle.
* Günlük / haftalık doğruluk: Ersin'in `nilm/eval/energy.py` dosyasıyla. Tüm dönemde Ortalama modeli, günlükte seq2point öne çıkıyor (PROJE.md §15.2); bunu grafikle göstereceğim.

SİZDEN RİCALAR

* Ersin: su ısıtıcısındaki seed turu bitince yeni results.csv ve tahminleri main'e koyarsan panel otomatik günceller; sadece haber ver.
* İkiniz de: sunum için her sayfadan 1-2 cümlelik anlatım çıkaralım. Ben "Nasıl çalışır" ve "Tasarruf" sayfalarını anlatırım; model ve veri kısmını sizin anlatmanız daha doğru olur.
* Rapor: sistem tasarımı ve panel bölümünü ben yazacağım, en sona bırakıyoruz.

NOTLAR

* Tutarlar aylık ortalama (her cihazın kayıtlı süresine göre 30 güne ölçeklenir; kayıt boşlukları sayılmaz).
* Grafiklerde 6 sn yerine dakikalık ortalama kullanılıyor; enerji ve fatura değişmez çünkü ortalama korunur. Ölçüt tabloları ise Ersin'in results.csv'sinden (6 sn'lik veriden) geliyor.
* `.panel/` klasörü (kullanıcılar ve önbellek) herkesin kendi bilgisayarında kalır.
