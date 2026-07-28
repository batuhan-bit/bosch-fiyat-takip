# Kurulum notları

## Günlük akış

1. MediaMarkt Türkiye'deki Bosch beyaz eşya ürünlerini kontrol et.
2. Yalnızca satıcısı MediaMarkt olan ürünleri kabul et.
3. Tam model kodunu çıkar ve Bosch Türkiye resmi sitesinde eşleştir.
4. Güncel fiyatları Google Sheets'e yaz.
5. Son alış fiyatı ve son alış tarihi hücrelerine dokunma; bu alanlar kullanıcı
   tarafından girilir.
6. Model güncel toptan listede yoksa Toptan Fiyatımız ve Net Toptan Fiyat
   alanlarına `YOK` yaz; ürünü silme ve kendiliğinden phase-out kabul etme.
7. Son alış fiyatı girilmişse, toptan fiyat bulunmasa bile geçerli Bosch
   desteğini düşerek Net Son Alış Fiyatını hesapla.
8. Günlük fiyat kaydını Fiyat Geçmişi sayfasına ekle.
9. Bulunamayan veya eşleşmeyen ürünleri Ayarlar ve Hatalar sayfasına yaz.
10. Günlük özeti Slack'e gönder.

## Temmuz 2026 kaynak dosyalarının yapısı

- Toptan listesi: `Solo Toptan` sayfasında model kodu B sütununda, toptan fiyat
  C sütununda.
- Fiyat farkı listesi: model kodu C sütununda, destek tutarı D sütununda.
- Fiyat farkı dosyasında standart BSP, phase-out/fırsat ürünleri ve Aile
  Bakanlığı kampanyası için ayrı sayfalar bulunuyor.
- Aile Bakanlığı kampanyası hiçbir şekilde kullanılmaz.
- Model kodu BSP sayfasında bulunursa BSP desteği, phase-out/fırsat ürünleri
  sayfasında bulunursa phase-out desteği kullanılır. Toptan listede bulunmamak
  tek başına phase-out desteği kullanma nedeni değildir.
- Dosyadaki destek tutarı KDV hariç haliyle kullanılır; KDV eklenmez.
- Destekler toplanmaz ve model kodu birebir eşleşmeden destek atanmaz.
- Model BSP ve phase-out listelerinin ikisinde de bulunmazsa destek `YOK`
  gösterilir; net maliyet hesabında indirim uygulanmaz.

## Slack özeti

Mesajda en az şu bilgiler bulunacaktır:

- Kontrol tarihi ve saati
- Kontrol edilen ürün sayısı
- Fiyatı değişen ürün sayısı
- Yeni bulunan ürünler
- MediaMarkt'ta artık bulunamayan ürünler
- Bosch sitesinde eşleşmeyen ürünler
- Google Sheets bağlantısı

## Beklenen bilgiler

- Örnek Bosch toptan fiyat listesi
- Örnek Bosch fiyat farkı listesi
- Raporun gönderileceği yaklaşık saat
- Google Sheets dosyası veya yeni dosya oluşturma tercihi
- Slack kanalına ait Incoming Webhook bilgisi (daha sonra GitHub Secret olarak girilecek)
