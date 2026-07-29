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
MediaMarkt stoğundan çıkan bir ürünün elle girilmiş son alış bilgileri gizli
`Son Alış Arşivi` sayfasında saklanır ve ürün yeniden stoğa girerse geri yüklenir.

## Google Sheets sayfaları

1. Güncel Fiyatlar
2. Fiyat Geçmişi
3. Toptan Fiyat Listesi
4. Bosch Destekleri
5. Eldem Stok Raporu
6. Son Alış Arşivi (gizli, otomatik yönetilir)
7. Ayarlar ve Hatalar

Ana tabloda şu alanlar bulunacaktır:

- Ürün Modeli
- Kategori
- MediaMarkt Fiyatı
- Bosch Satış Fiyatı
- Eldem Stok
- Toptan Fiyatımız
- Son Alış Fiyatımız
- Son Alış Tarihi
- Bosch Fiyat Farkı Desteği
- Net Toptan Fiyat
- Net Toptana Göre Karlılık
- Net Son Alış Fiyatı
- Net Son Alışa Göre Karlılık
- Son Kontrol Tarihi
- MediaMarkt Linki
- Bosch Linki

Ürünler `Eldem Stok` miktarı en yüksekten en düşüğe doğru sıralanır. Stokların
eşit olması durumunda kategori ve model adı kullanılır.

Hesaplamalar:

- Net Toptan Fiyat = Toptan Fiyatımız - Bosch Fiyat Farkı Desteği
- Net Toptana Göre Karlılık = (MediaMarkt Fiyatı - Net Toptan Fiyat) / Net Toptan Fiyat
- Net Son Alış Fiyatı = Son Alış Fiyatımız - Bosch Fiyat Farkı Desteği
- Net Son Alışa Göre Karlılık = (MediaMarkt Fiyatı - Net Son Alış Fiyatı) / Net Son Alış Fiyatı

## Toptan listede bulunmayan ürünler

MediaMarkt'ta bulunan bir model güncel Bosch toptan fiyat listesinde yoksa ürün
takipten çıkarılmaz. Bu durum ürünün üretimden kalkmış olabileceğini, ancak bayi
stoklarında hâlâ bulunabileceğini gösterir.

- `Toptan Fiyatımız`: **Üretimden Kalktı**
- `Net Toptan Fiyat`: **Üretimden Kalktı**
- `Net Toptana Göre Karlılık`: Boş bırakılır.
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
- Eldem stok raporunu `girdiler/stok-raporlari/` klasörüne koyun.

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
- GitHub Actions her gün Türkiye saatiyle 09:17'de çalışır.

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

### 3. MediaMarkt proxy

MediaMarkt istekleri Türkiye konut tipi proxy üzerinden gönderilir. Proxy
yalnızca `mediamarkt.com.tr` alan adında kullanılır; Bosch, Google Sheets ve
Slack trafiği proxy kotasını tüketmez. Decodo'da kullanıcı adı/parola ile
Türkiye hedefli, 30 dakikalık sabit oturum oluşturun ve bağlantıyı şu biçimde
GitHub secret olarak kaydedin:

`http://KULLANICI_ADI:PAROLA@gate.decodo.com:7000`

Secret adı `MEDIAMARKT_PROXY_URL` olmalıdır.

### 4. GitHub Secrets

Repository ayarlarında `Settings > Secrets and variables > Actions` yoluna
giderek şu dört secret'ı oluşturun:

- `GOOGLE_SHEET_ID`
- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `SLACK_WEBHOOK_URL`
- `MEDIAMARKT_PROXY_URL`

### 5. Aylık liste güncellemesi

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
