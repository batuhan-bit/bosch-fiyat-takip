# Bosch Fiyat Takip Botu

Bu proje, MediaMarkt Türkiye'de satıcısı **MediaMarkt** olan Bosch beyaz eşya
ürünlerini her gün kontrol eder, aynı modelleri Bosch Türkiye resmi sitesinde
eşleştirir ve sonuçları Google Sheets'e aktarır.

## İzlenecek ürün grupları

- Buzdolabı
- Çamaşır makinesi
- Kurutma makinesi
- Bulaşık makinesi

## Veri kaynakları

Yalnızca aşağıdaki resmi siteler kullanılacaktır:

- MediaMarkt Türkiye
- Bosch Türkiye

Pazaryeri satıcıları, kuponlar, sepette indirimler ve takas kampanyaları
hesaplamaya dahil edilmez.

Güncel Fiyatlar ve Fiyat Geçmişi sayfalarına yalnızca MediaMarkt'ın doğrudan
satıcısı olduğu ve o gün satın alınabilir stoğu bulunan ürünler yazılır. Stoktan
çıkan ürün Güncel Fiyatlar'dan kaldırılır; yeniden stoğa girerse tekrar eklenir.
Son alış fiyatı ve tarihi, geri dönen ürün için geçmiş kayıttan korunur.

## Google Sheets sayfaları

1. Güncel Fiyatlar
2. Fiyat Geçmişi
3. Toptan Fiyat Listesi
4. Bosch Destekleri
5. Ayarlar ve Hatalar

Ana tabloda şu alanlar bulunacaktır:

- Ürün Modeli
- Kategori
- MediaMarkt Fiyatı
- Bosch Satış Fiyatı
- Toptan Fiyatımız
- Son Alış Fiyatımız
- Son Alış Tarihi
- Bosch Fiyat Farkı Desteği
- Net Toptan Fiyat
- Net Son Alış Fiyatı
- Ürün Durumu
- Son Kontrol Tarihi
- MediaMarkt Linki
- Bosch Linki

Hesaplamalar:

- Net Toptan Fiyat = Toptan Fiyatımız - Bosch Fiyat Farkı Desteği
- Net Son Alış Fiyatı = Son Alış Fiyatımız - Bosch Fiyat Farkı Desteği

## Toptan listede bulunmayan ürünler

MediaMarkt'ta bulunan bir model güncel Bosch toptan fiyat listesinde yoksa ürün
takipten çıkarılmaz. Bu durum ürünün üretimden kalkmış olabileceğini, ancak bayi
stoklarında hâlâ bulunabileceğini gösterir.

- `Toptan Fiyatımız`: **YOK**
- `Net Toptan Fiyat`: **YOK**
- `Ürün Durumu`: **Toptan listede yok**
- `Son Alış Fiyatımız`: Kullanıcı tarafından elle girilmeye devam eder.
- `Son Alış Tarihi`: Kullanıcı tarafından elle girilir ve günlük güncellemede korunur.
- `Net Son Alış Fiyatı`: Son alış fiyatı ve geçerli Bosch desteği varsa hesaplanır.

Toptan listede bulunmamak, modelin Bosch fiyat farkı dosyasındaki phase-out
listesinde olduğu anlamına gelmez. Phase-out desteği yalnızca model kodu ilgili
phase-out sayfasında birebir bulunursa kullanılır.

## Bosch fiyat farkı desteği kuralları

- Dosyadaki destek tutarı **KDV hariç** haliyle kullanılır; KDV eklenmez.
- Normal BSP sayfasında model kodu varsa o satırdaki destek kullanılır.
- Phase-out/fırsat ürünleri sayfasında model kodu varsa o satırdaki destek
  kullanılır.
- Aile Bakanlığı kampanyası hiçbir hesaplamada veya raporda kullanılmaz.
- Eşleştirme yalnızca normalize edilmiş tam model koduyla yapılır.
- Model BSP ve phase-out sayfalarının hiçbirinde yoksa destek tutarı `YOK`
  olarak gösterilir ve maliyetten herhangi bir destek düşülmez. Bu durumda net
  fiyat, mevcut toptan veya son alış fiyatına eşittir.

## Aylık dosyaların yüklenmesi

- Toptan fiyat listesini `girdiler/toptan-fiyat-listeleri/` klasörüne koyun.
- Bosch fiyat farkı listesini `girdiler/fiyat-farki-listeleri/` klasörüne koyun.

Bu klasörlerdeki ticari dosyalar güvenlik amacıyla GitHub'a gönderilmez.

## Planlanan çevrimiçi çalışma

Bot GitHub Actions üzerinde günde bir kez çalışacak. Google erişim bilgileri ve
Slack webhook adresi GitHub Secrets içinde saklanacak. Günlük kontrol sonunda
özet tablo ve Google Sheets bağlantısı Slack kanalına gönderilecek.

## Güncel teknik durum

- Dört MediaMarkt Bosch kategorisi yapılandırılmış ürün verilerinden taranır.
- Ürün sayfasında marka `BOSCH`, satıcı `MediaMarkt` ve satın alınabilir stok
  durumu doğrulanır.
- Model, Bosch Türkiye resmi sitesinde tam kodla aranır.
- Google Sheets'teki Son Alış Fiyatımız ve Son Alış Tarihi sütunları günlük
  güncellemede korunur.
- GitHub Actions her gün Türkiye saatiyle 09:00'da çalışır.

## Kurulum özeti

### 1. Google hizmet hesabı

1. Google Cloud Console'da bir proje oluşturun.
2. Google Sheets API'yi etkinleştirin.
3. Bir hizmet hesabı oluşturup JSON anahtarı indirin.
4. `Bosch Fiyat Takip` Google Sheets dosyasını hizmet hesabının e-posta
   adresiyle Düzenleyici olarak paylaşın.
5. JSON dosyasının içeriğini GitHub'da `GOOGLE_SERVICE_ACCOUNT_JSON` isimli
   repository secret olarak kaydedin.

### 2. Slack

1. Slack API sayfasında yeni bir uygulama oluşturun.
2. Incoming Webhooks özelliğini açın.
3. Raporun gideceği kanal için webhook oluşturun.
4. Adresi GitHub'da `SLACK_WEBHOOK_URL` isimli repository secret olarak
   kaydedin.

### 3. GitHub Secrets

Repository ayarlarında `Settings > Secrets and variables > Actions` yoluna
giderek şu üç secret'ı oluşturun:

- `GOOGLE_SHEET_ID`
- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `SLACK_WEBHOOK_URL`

### 4. Aylık liste güncellemesi

Yeni dosyaları ilgili `girdiler` klasörlerine koyduktan sonra aşağıdaki komut,
aktif toptan ve destek kayıtlarını Google Sheets'e aktarır. Aile Bakanlığı
kampanyası otomatik olarak yok sayılır.

```powershell
$env:PYTHONPATH="src"
python -m bosch_tracker.import_lists --wholesale "toptan.xlsx" --support "fiyat-farki.xlsx"
```

## Yerel kontrol

Google Sheets ve Slack'e yazmadan canlı kaynakları sınamak için:

```powershell
$env:PYTHONPATH="src"
python -m bosch_tracker.main --dry-run --output-json "kontrol.json"
```
