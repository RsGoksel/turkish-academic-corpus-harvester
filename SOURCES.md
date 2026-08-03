# Kaynak defteri — hangi depodan ne aldık, neyi alamadık

Ölçüm: 171 üniversite alan adı × 9 URL kalıbı tarandı. **150 erişilebilir depo**,
62 DSpace, **46 tekil depo metin üretiyor**.

`TEXT örnek` = rastgele kayıtlardan kaçında ön-çıkarılmış tam metin var.

Son güncelleme: 2026-08-02 12:45 UTC


## ⚠ "TEXT paketi var" ≠ "dosya dolu" — kapsama oranları şişikti

DSpace bazı kayıtlarda TEXT paketi oluşturur ama dosyayı **boş bırakır**: 2 baytlık
yer tutucular. Tarama "paket var mı" diye baktığı için bu kayıtlar kapsama oranına
dahil oluyordu. PC-2 kendi shard'ında tespit etti; dört depoda doğruladım:

| depo | "TEXT paketi var" | **gerçek (>2 KB)** | boş dosya |
|---|---:|---:|---:|
| hacettepe | %98,7 | **%71,1** | 1.584 |
| bilkent | %96,1 | **%87,6** | 352 |
| selcuk | %62,3 | **%56,9** | 270 |
| dicle | %42,2 | **%35,2** | 239 |

PC-2'nin kendi shard'ında ölçtüğü %70,0 ile benim taramadan hesapladığım %71,1
bağımsız olarak birbirini doğruluyor.

**Düzeltildi:** `harvest.py` artık `--min-bytes 2048` uygular. Bayt bilgisi zaten
taramada vardı, kullanılmıyordu. Boş paketler **indirilmeden** elenir -- hem doğru
sayı hem daha az istek.

Aşağıdaki tabloda "TEXT kapsaması" sütunu taramadan gelen ham orandır. Gerçek
verim için yukarıdaki tabloya bakın; ölçülmemiş depolarda gerçek değer **daha
düşük** olacaktır.

## Shard atamasında boşluk

Bir depoya tek makine atandığında ve o makine `--num-shards 5` ile koştuğunda,
deponun **%80'i sahipsiz kalır**. Hacettepe'de tam bu oldu: PC-2 shard 2/5'te
6.506 kayıttan 4.553 belge çıkardı (%70), ama shard 0/1/3/4'teki 26.472 kayda
kimse atanmadı.

**Kural:** tek makineye verilen depo `--num-shards` almaz. Shard yalnızca aynı
depoya birden fazla makine koşturulduğunda kullanılır.

## Metin üreten depolar — verime göre

| depo | kayıt | TEXT kapsaması | tahmini belge | kaynak | atanan |
|---|---:|---|---:|---|---|
| [acikerisim.ege.edu.tr](https://acikerisim.ege.edu.tr) | 118,666 | ~%100 | ~118,666 | örneklem n=5 | PC-1, PC-2 |
| [dspace.itu.edu.tr](https://dspace.itu.edu.tr) | 72,553 | ~%20 | ~14,510 | örneklem n=5 | — |
| [acikerisim.uludag.edu.tr](https://acikerisim.uludag.edu.tr) | 55,945 | ~%60 | ~33,567 | örneklem n=5 | — |
| [acikerisim.selcuk.edu.tr](https://acikerisim.selcuk.edu.tr) | 54,829 | **%62.2** | ~34,102 | **ölçüldü** (n=21,925) | PC-1, PC-2 |
| [repository.bilkent.edu.tr](https://repository.bilkent.edu.tr) | 52,198 | ~%100 | ~52,198 | örneklem n=5 | — |
| [acikerisim.omu.edu.tr](https://acikerisim.omu.edu.tr) | 46,134 | ~%20 | ~9,226 | örneklem n=5 | — |
| [openaccess.hacettepe.edu.tr](https://openaccess.hacettepe.edu.tr) | 33,113 | **%98.7** | ~32,684 | **ölçüldü** (n=5,567) | — |
| [acikerisim.dicle.edu.tr](https://acikerisim.dicle.edu.tr) | 30,146 | ~%80 | ~24,116 | örneklem n=5 | — |
| [acikerisim.trakya.edu.tr](https://acikerisim.trakya.edu.tr)<br><sub>= dspace.trakya.edu.tr</sub> | 27,602 | ~%40 | ~11,040 | örneklem n=5 | — |
| [acikerisim.aku.edu.tr](https://acikerisim.aku.edu.tr) | 26,721 | ~%80 | ~21,376 | örneklem n=5 | — |
| [acikerisim.ibu.edu.tr](https://acikerisim.ibu.edu.tr) | 26,265 | ~%40 | ~10,506 | örneklem n=5 | — |
| [earsiv.gop.edu.tr](https://earsiv.gop.edu.tr) | 23,999 | ~%20 | ~4,799 | örneklem n=5 | — |
| [acikerisim.duzce.edu.tr](https://acikerisim.duzce.edu.tr) | 22,718 | ~%60 | ~13,630 | örneklem n=5 | — |
| [acikerisim.balikesir.edu.tr](https://acikerisim.balikesir.edu.tr)<br><sub>= dspace.balikesir.edu.tr</sub> | 20,538 | ~%100 | ~20,538 | örneklem n=5 | — |
| [acikerisim.nku.edu.tr](https://acikerisim.nku.edu.tr) | 18,093 | ~%80 | ~14,474 | örneklem n=5 | — |
| [dspace.adiyaman.edu.tr](https://dspace.adiyaman.edu.tr) | 16,094 | ~%100 | ~16,094 | örneklem n=5 | — |
| [openaccess.iyte.edu.tr](https://openaccess.iyte.edu.tr) | 15,166 | ~%100 | ~15,166 | örneklem n=5 | — |
| [acikerisim.bartin.edu.tr](https://acikerisim.bartin.edu.tr) | 14,410 | ~%60 | ~8,646 | örneklem n=5 | — |
| [acikerisim.maltepe.edu.tr](https://acikerisim.maltepe.edu.tr)<br><sub>= openaccess.maltepe.edu.tr</sub> | 14,050 | ~%20 | ~2,810 | örneklem n=5 | — |
| [acikerisim.aksaray.edu.tr](https://acikerisim.aksaray.edu.tr) | 13,016 | ~%100 | ~13,016 | örneklem n=5 | — |
| [acikerisim.baskent.edu.tr](https://acikerisim.baskent.edu.tr) | 12,451 | ~%20 | ~2,490 | örneklem n=5 | — |
| [acikerisim.gelisim.edu.tr](https://acikerisim.gelisim.edu.tr) | 11,520 | ~%100 | ~11,520 | örneklem n=5 | — |
| [acikerisim.medipol.edu.tr](https://acikerisim.medipol.edu.tr)<br><sub>= openaccess.medipol.edu.tr</sub> | 11,481 | ~%60 | ~6,888 | örneklem n=5 | — |
| [earsiv.kmu.edu.tr](https://earsiv.kmu.edu.tr) | 10,590 | ~%80 | ~8,472 | örneklem n=5 | — |
| [acikerisim.siirt.edu.tr](https://acikerisim.siirt.edu.tr) | 9,331 | ~%100 | ~9,331 | örneklem n=5 | — |
| [openaccess.nevsehir.edu.tr](https://openaccess.nevsehir.edu.tr) | 8,977 | ~%100 | ~8,977 | örneklem n=5 | — |
| [openaccess.uskudar.edu.tr](https://openaccess.uskudar.edu.tr) | 8,919 | ~%40 | ~3,567 | örneklem n=5 | — |
| [openaccess.iku.edu.tr](https://openaccess.iku.edu.tr) | 8,766 | ~%80 | ~7,012 | örneklem n=5 | — |
| [openaccess.izu.edu.tr](https://openaccess.izu.edu.tr) | 8,561 | ~%100 | ~8,561 | örneklem n=5 | — |
| [openaccess.ahievran.edu.tr](https://openaccess.ahievran.edu.tr) | 7,928 | ~%100 | ~7,928 | örneklem n=5 | — |
| [acikerisim.istinye.edu.tr](https://acikerisim.istinye.edu.tr) | 7,067 | ~%80 | ~5,653 | örneklem n=5 | — |
| [openaccess.bayburt.edu.tr](https://openaccess.bayburt.edu.tr) | 7,007 | ~%20 | ~1,401 | örneklem n=5 | — |
| [earsiv.hitit.edu.tr](https://earsiv.hitit.edu.tr) | 6,718 | ~%80 | ~5,374 | örneklem n=5 | — |
| [openaccess.altinbas.edu.tr](https://openaccess.altinbas.edu.tr) | 6,074 | ~%40 | ~2,429 | örneklem n=5 | — |
| [acikerisim.fsm.edu.tr](https://acikerisim.fsm.edu.tr) | 5,941 | ~%100 | ~5,941 | örneklem n=5 | — |
| [openaccess.osmaniye.edu.tr](https://openaccess.osmaniye.edu.tr) | 5,726 | ~%100 | ~5,726 | örneklem n=5 | — |
| [acikerisim.alanya.edu.tr](https://acikerisim.alanya.edu.tr) | 5,626 | ~%100 | ~5,626 | örneklem n=5 | — |
| [openaccess.artvin.edu.tr](https://openaccess.artvin.edu.tr) | 5,214 | ~%100 | ~5,214 | örneklem n=5 | — |
| [acikerisim.bakircay.edu.tr](https://acikerisim.bakircay.edu.tr) | 4,049 | ~%100 | ~4,049 | örneklem n=5 | — |
| [openaccess.29mayis.edu.tr](https://openaccess.29mayis.edu.tr) | 3,968 | ~%60 | ~2,380 | örneklem n=5 | — |
| [openaccess.ihu.edu.tr](https://openaccess.ihu.edu.tr) | 3,532 | ~%40 | ~1,412 | örneklem n=5 | — |
| [earsiv.batman.edu.tr](https://earsiv.batman.edu.tr) | 3,345 | ~%60 | ~2,007 | örneklem n=5 | — |
| [openaccess.sirnak.edu.tr](https://openaccess.sirnak.edu.tr) | 2,885 | ~%100 | ~2,885 | örneklem n=5 | — |
| [acikerisim.mehmetakif.edu.tr](https://acikerisim.mehmetakif.edu.tr) | 2,778 | ~%20 | ~555 | örneklem n=5 | — |
| [acikerisim.esenyurt.edu.tr](https://acikerisim.esenyurt.edu.tr) | 1,227 | ~%100 | ~1,227 | örneklem n=5 | — |
| [acikerisim.ksu.edu.tr](https://acikerisim.ksu.edu.tr)<br><sub>= dspace.ksu.edu.tr</sub> | 68 | ~%100 | ~68 | örneklem n=5 | — |

### ⚠ Küçük örneklem sistematik olarak YÜKSEK tahmin ediyor

Selçuk üç kez ölçüldü ve üçü uyuşmadı:

| yöntem | sonuç |
|---|---|
| PC-4 probe, n=50 | %78 |
| PC-0 örneklem, n=25 | %88 |
| **filo `scan`, n=21.925** | **%62,3** |

İki bağımsız shard (PC-1 %62,3 · PC-2 %62,1) birbirini doğruluyor, yani ölçüm
sağlam; yanlış olan küçük örneklemler. Sebebi muhtemelen sıralama: `discover`
ucu varsayılan sırada döner ve ilk sayfalardaki kayıtlar daha yeni, daha tam.
İlk 25 kayıt temsili değildir.

**Sonuç: `örneklem n=5` ya da `n=25` yazan her satır iyimserdir.** Gerçek değer
`scan` tamamlanmadan bilinmez. Hacettepe (%98,7, n=5.567) bir istisna --
orada örneklem de yüksek çıkmıştı ve tuttu.

**Toplam ~597,857 belge** 46 depoda (ölçülmemiş satırlar iyimser -- yukarıdaki uyarıya bakın).

## DergiPark — ölçülen en büyük kaynak

OAI-PMH: `https://dergipark.org.tr/api/public/oai/` (oai_dc, oai_etdms, oai_marc, oai_mods)

- Kayıt id aralığı **10 – 1.270.838**
- Test edilen 6 güncel makalenin **5'inde PDF metin katmanı var** (12k–90k karakter)
- Eski makaleler taranmış görüntü — metin yok, tarihe göre filtrelenmeli
- Makale başına ~30.000 karakter ≈ **7.500 token**
- Kaba tahmin: 1,27 M kayıt × %50 × 7.500 ≈ **4,7 milyar token**

İndirme kalıbı (3 istek/makale):

```
1. OAI GetRecord     -> <dc:identifier> makale sayfası
2. makale sayfası    -> href=/xx/download/article-file/{fileId}
3. article-file      -> PDF (application/pdf)
```

Metin çıkarma: PyMuPDF (`fitz`). Karakter sayısı <2000 ise taranmış görüntüdür, atılır.

## Alınmayacak

| kaynak | neden |
|---|---|
| İTÜ Nadir Eserler (ContentDM) | Kayıtlar sayfa taraması (`"Page 1"`), **OCR metni yok**. En uzun açıklama 6 karakter. Kullanmak için OCR hattı gerekir. |
| YÖK Ulusal Tez Merkezi | e-Devlet kimlik girişi gerektiriyor |
| Elsevier / Springer / IEEE | Sözleşme toplu indirmeyi yasaklıyor; tetiklenirse İTÜ'nün tüm IP aralığı kapanır |

## Düzeltme — OMÜ

PC-4'ün probe'u OMÜ'yü **%0 TEXT** diye işaretlemiş ve listeden çıkarmıştık.
Ulusal tarama `acikerisim.omu.edu.tr`'de **46.134 kayıt, 1/5 TEXT** buldu.
İki ölçüm de küçük örneklem. **Geçici olarak yeniden listede**, `scan` ile kesin ölçülecek.
