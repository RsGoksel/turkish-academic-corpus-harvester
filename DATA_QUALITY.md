# Veri kalitesi — PC-2 bulguları (2026-08-02)

Hacettepe hasadı sırasında çıkan üç sorun. İkisi bizim kodumuzdaydı, biri
depoların kendisinde. Üçü de sessizdi: hiçbiri hata olarak görünmüyordu, veri
sadece eksik geliyordu.

---

## 1. Tek bozuk OAI sayfası tüm künye hasadını öldürüyordu

Hacettepe'nin OAI beslemesinde **4400** ve **15700** ofsetleri kalıcı olarak
HTTP 500 veriyor. Komşuları sağlam:

```
ofset 4400  -> HTTP 500, kayıt=0      ofset 4600  -> HTTP 200, kayıt=100
ofset 4500  -> HTTP 200, kayıt=100    ofset 5000  -> HTTP 200, kayıt=100
```

Bu yüzden "sunucu hassas, `--delay` yükselt" tavsiyesi burada **asla** işe
yaramaz — her deneme aynı kaydı ister, geri çekilir ve koşu ölür. Sonuç:
33.178 kaydın 28.778'i hiç alınamıyordu.

**Yayınlanan `hacettepe_meta.jsonl.gz`'nin 4.400 satırda kalmasının sebebi
budur** ve kimse fark etmemişti, çünkü dosya "başarıyla" yayımlanmıştı.

Düzeltme: `harvest_meta` bir sayfa kalıcı hata verdiğinde resumption token'ın
sonundaki ofseti bir sayfa ileri taşıyıp devam ediyor (`_skip_page`). En fazla
100 künye kaybedilir; alternatifi deponun geri kalanını kaybetmek.
Künye 4.400 → **32.978**'e çıktı.

## 2. `dc.identifier` içindeki kaynakça, handle yerine geçiyordu

Bazı kayıtlarda tüm kaynakça `dc.identifier` alanına yapıştırılmış (23.395
karaktere kadar) ve içindeki bir atıfta `hdl.handle.net` geçiyor. Eski çıkarım
alt dizgi arayıp bölüyordu:

```python
handles = [v for v in row["identifier"] if "hdl.handle.net" in v]
row["handle"] = handles[0].split("hdl.handle.net/")[-1]
```

İki başarısızlık biçimi üretti:

- **handle yerine bibliyografya metni** — hiç çözülmez (7 kayıt)
- **geçerli görünen ama BAŞKA kurumun handle'ı** — `10871/…`, `1765/…`,
  `11424/417`. Bunlar sessizce yanlış belgeyi indirir; hata bile vermez (3 kayıt)

Düzeltme (`handle_from`): yalnızca **tamamı** handle URL'i olan identifier kabul
ediliyor, hiçbiri uymazsa OAI kimliğinin son parçasına düşülüyor.

363.053 handle üzerinde doğrulandı: **10 hatalı handle düzeldi, 0 bozuk kaldı**,
doğru olanlar değişmedi. Ayrıca OAI'ye düşme sayesinde daha önce **handle'ı hiç
olmayan 353 kayıt** kurtarıldı — onlar metin aşamasında tümden atlanıyordu.

| depo | kayıt | bozuk→düzeldi | handle yok→kurtuldu |
|---|---:|---:|---:|
| ege | 118.818 | 0 | 2 |
| hacettepe | 32.978 | 7 | 326 |
| itu | 68.911 | 0 | 10 |
| marmara | 87.506 | 2 | 0 |
| selcuk | 54.840 | 1 | 15 |
| **toplam** | **363.053** | **10** | **353** |

Mevcut künye dosyaları için: `python3 repair_handles.py --apply` (`.bak` yedeği
alır). **İTÜ ve Marmara künyeleri yayımlanmış durumda; onlar da yenilenmeli.**

## 3. TEXT paketi var ama dosyanın içi boş

Taramanın "TEXT var" sayısı **verimi olduğundan fazla gösteriyor**. Hacettepe
shard 2'de tarama %98,7 kapsama dedi, gerçek isabet **%69** çıktı. Sebep: depo
TEXT paketini oluşturmuş ama bitstream **2 bayt**.

```
metni BOŞ çıkanlar   n=296   min=2      medyan=2         maks=368
metni DOLU çıkanlar  n=854   min=2.185  medyan=106.480   maks=214.060
```

İki küme hiç örtüşmüyor, yani tarama boyutu meseleyi istek harcamadan çözüyor.
`min_chars` eşiğini düşürmek çare değil: 1.740 `too_short` kaydın 1.546'sı
**sıfır** karakter, eşik 500'e çekilse yalnız 10 tanesi kurtulur.

Düzeltme: metin aşaması, taramada `bytes < min_chars` olan kaydı hiç istemiyor.
UTF-8'de bayt ≥ karakter ve `clean()` yalnız siler, dolayısıyla bu filtre hiçbir
geçerli belgeyi eleyemez. Hacettepe'de belge başına ~1.500 gereksiz istek düşer.

---

## Kurumlara bildirilecek liste

`python3 inventory.py` her denenen kayıt için tek satırlık kalıcı defter üretir
— **başarılı olan da olmayan da**, sebebiyle ve indirme adresiyle:

```
data/reports/<depo>_inventory.jsonl    handle, sonuç, kategori, açıklama,
                                       karakter, bayt, metin adresi, başlık
data/reports/<depo>_bos_belgeler.csv   kuruma gönderilecek BOŞ dosyalar
```

Kategoriler: `BASARILI`, `BOS_DOSYA`, `COK_KISA`, `TEXT_PAKETI_YOK`,
`ERISIM_KAPALI`, `TEXT_INDIRILEMEDI`, `KAYIT_BULUNAMADI`, `GECICI_HATA`,
`DENENMEDI`.

`BOS_DOSYA` ile `TEXT_PAKETI_YOK` ayrımı önemli: birincisi kurumun düzeltebileceği
bir arıza (indirme adresi yayımlanmış, arkasında içerik yok), ikincisi normal
(DSpace o kayıttan metin çıkarmamış). Kuruma yalnız birincisi bildirilir.

Şu ana kadar tespit edilen boş dosyalar: **Hacettepe 1.578**, **Selçuk 40**,
**Ege 3**.

---

## Küçük not

`harvest_meta` OAI yanıtlarını `xml.etree.ElementTree` ile ayrıştırıyor; bu
ayrıştırıcı XXE ve "billion laughs" saldırılarına açıktır. Kaynaklarımız bilinen
üniversite sunucuları olduğu için risk düşük, ama depo listesi yabancı adreslere
açıldıkça `defusedxml` düşünülmeli. (Depo "bağımlılık yok" diyor, o yüzden
değiştirmedim.)
