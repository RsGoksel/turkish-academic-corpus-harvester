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

## Hedef sıralaması — ÖLÇÜLEN verime göre

Bu tablonun ilk hâli depoları `kayıt × n=5 örneklem` ile sıralıyordu ve filoyu
listenin tepesindeki **Ege'ye** yönlendiriyordu — bildiğimiz en düşük verimli
depolardan biri. n=5'te 5/5 gelmesi "%100" demek değildir; o örneklemde %95
aralığı kabaca **%48-100**'dür. PC-4 tespit etti.

Verim **üç kapıdan** geçer ve üçü ayrı ayrı ölçülmelidir:

1. **Paket var mı** — tarama söyler
2. **Paket dolu mu** — 2 baytlık yer tutucular var *(PC-2 buldu)*
3. **Okunabilir mi** — dolu ama 401 dönebilir *(PC-4 buldu)*

Bilkent bunun ders kitabı örneği: 52.198 kayıt → paket %96,1 → dolu %87,6 →
**okunabilir %52,5**. Gerçek beklenti 52.198 değil **~24.000**. Tek kapıya bakan
her tahmin şişer.

**Model doğrulandı:** İTÜ Polen için 17.021 belge öngörüyor, gerçekte **16.997**
aldık — %0,14 hata.

### Beklentisi ölçülmüş (üç kapı da biliniyor)

| depo | kayıt | paket | dolu | okunabilir | **BELGE** | kaynak |
|---|---:|---:|---:|---:|---:|---|
| itu_polen | 68,911 | %24.7 | %24.7 | %100.0 | **17,021** | TAMAMLANDI: 16.997 belge / 68.911 |
| bilkent | 52,198 | %96.1 | %87.6 | %34.5 | **15,775** | PC-4 fiili indirme n=6.706 |
| aksaray | 13,016 | %90.7 | %90.7 | %72.5 | **8,558** | PC-4 n=1000, 40 sayfa × 1 |
| adiyaman | 16,094 | %49.2 | %49.2 | %100.0 | **7,918** | PC-4 n=1000, 40 sayfa × 1 |

#### Dördüncü yanlılık: sayfa-kümeli örnekleme

PC-4, kendi aracındaki bir yanlılığı buldu ve düzeltti: kapsama 8 sayfadan
**bitişik** 25 kayıt çekerek ölçülüyordu. Bitişik kayıtlar aynı yatırma
partisinden gelir ve korelelidir; efektif örneklem nominalinin çok altındadır.
Yeni yöntem: **40 sayfa × 1 kayıt**.

Düzeltince iki hedef de kaydı, üstelik **ters yönlerde**:

| | eski (8×25) | yeni (40×1) |
|---|---|---|
| Aksaray kapsama | %88,5 | %90,7 |
| Aksaray okunabilir | %90,0 | **%72,5** |
| Aksaray beklenti | ~10.367 | **~8.558** |
| Adıyaman kapsama | %25,0 | **%49,2** |
| Adıyaman beklenti | ~4.023 | **~7.918** |

**"Aksaray 2,5 kat daha iyi" bir ölçüm artefaktıydı.** İkisi artık birbirinin
güven aralığında; hacimce anlamlı fark yok.

Kümelenmenin sertliği: Adıyaman'da örneklenen 40 sayfanın yalnızca 20'sinde tek
bir uygun kayıt vardı. Yani %49,2 "her sayfanın yarısı dolu" değil, **"sayfaların
yarısı tamamen dolu, yarısı tamamen boş"** demek.

**Aksaray seçildi ama gerekçesi değişti:** hacim değil, bölgesel çeşitlilik.

#### Bilkent: fiili sayım, probe değil

PC-0'ın n=40 probe'u erişimi %52,5 ölçtü; PC-4'ün **6.706 fiili indirmesi %34,5
[33,4-35,6]** ölçtü — probe'un %95 aralığının ([37,0-68,0]) **altında**.
Kontrol edildi: probe'un 40 örneği 40 **farklı** sayfadan geliyordu, yani
kümelenme değil. Sapmanın sebebi **açıklanamadı**. Tabloya fiili sayım girdi;
6.706 örnek 40'ı yener, mekanizma bilinmese de.

#### Uyarı: eski yöntemle ölçülen her depo aynı yanlılığı taşıyor

Üç-kapı modelinin İTÜ'de %0,14 tutması **modeli** doğrular, **girdileri** değil —
İTÜ'de üçüncü kapı zaten dardı, yanlı bir okunabilirlik ölçümü sonucu bozmamış
olabilir. Erişimi eski yöntemle ölçülmüş depolar yeni örneklemeyle **tekrar
koşulmalı**. (PC-4 tespit etti ve öneriyor.)

### Erişim ölçülmedi — sayı VERİLMİYOR

Bunlar için tahmin üretmiyoruz. "Bilmiyoruz" demek, dört kat şişik bir sayı
vermekten iyidir. Tavan = erişim %100 olsaydı çıkacak değer.

| depo | kayıt | paket | dolu | tavan | kaynak |
|---|---:|---:|---:|---:|---|
| selcuk | 54,829 | %62.3 | %56.9 | ≤31,197 | PC-1+PC-2 scan n=21.925 |
| hacettepe | 32,978 | %98.7 | %71.1 | ≤23,447 | PC-2 tam shard sayımı |
| dicle | 30,146 | %42.2 | %35.2 | ≤10,611 | PC-3 scan |
| ege | 118,666 | %4.0 | — | ≤4,746 | PC-4 probe (n=5 örneklem %100 demişti) |
| omu | 46,134 | %0.0 | — | ≤0 | tam probe 0/50 |

### Düzeltilen çelişkiler

| depo | eski tablo | **ölçülen** | kat |
|---|---:|---:|---:|
| Ege | ~118.666 | **≤4.746** | 25× şişik |
| Bilkent | ~52.198 | **24.005** | 2,2× |
| Adıyaman | ~16.094 | **4.023** | 4× |
| OMÜ | ~9.226 | **0** | tam probe 0/50 |

Ege tablonun tepesindeydi ve PC-1 ile PC-2 oraya atanmıştı. Sıralama artık
kayıt sayısına değil ölçülen belgeye göre.

Araç: `rank_targets.py`

---
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
