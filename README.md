# Türk Üniversiteleri Açık Arşiv Hasatçısı

## ⚡ ÖNEMLİ — iki yeni şey (2026-08-02)

**1. `scan` aşaması: hasadı 15 kata kadar hızlandırır.**

Eski yol belge başına 3 istek, TEXT'i olmayan kayıt başına 2 istek harcıyordu.
Marmara ve Ege'de kayıtların yalnızca ~%10'unda TEXT var — yani istek bütçesinin
onda dokuzu boşa gidiyordu. `scan` tek istekte 25 kaydın hangisinde TEXT olduğunu
**ve indirme adresini** öğrenir. Sonrasında metin aşaması belge başına 1 istek
harcar, TEXT'i olmayana hiç dokunmaz.

Ölçüldü (Selçuk, canlı sunucu): 5 kayıtlık testte eski yol 13 istek, yeni yol 3.
Marmara shard'ı için 36.240 istek → 2.417. **~30 saat → ~2 saat.**

```bash
# ÖNCE tarama (kendi shard'ınız), SONRA metin
python3 harvest.py scan --repo selcuk --shard 1 --num-shards 5 --delay 2
python3 harvest.py text --repo selcuk --shard 1 --num-shards 5 --workers 1 --delay 3
```

`scan` sayfa numarasına göre bölünür, `text` handle hash'ine göre — ikisi farklı
bölmelerdir, bu normaldir. Tarama çıktısını **herkesle paylaşın** (bkz. DELIVERY.md):
bir kez öğrenilen "kimde TEXT var" bilgisi tüm filoya yarar.

**2. Çıktıları bitince değil, her 2 saatte bir gönderin** → [DELIVERY.md](DELIVERY.md)

Ayrıca: hangi depodan ne aldığımızın tek kaydı → [SOURCES.md](SOURCES.md)

**Düzeltildi:** `--repo https://...` biçimi artık doğru dizine yazıyor
(önceden `data/repos/https:/host/` altına düşüp "run meta stage first" hatası
veriyordu — PC-1 ve PC-4 bildirdi).


Türkiye'deki üniversitelerin **açık erişim** kurumsal arşivlerinden (DSpace) natif Türkçe akademik metin toplar. Toplanan korpus, Türkçe bir LLM'in **continued pre-training (CPT)** aşamasında kullanılır.

**Neden bu veri:** Türkçe LLM'lerin en büyük sorunu makine çevirisi verisiyle eğitilmeleri — model "çeviri kokan" Türkçe üretiyor. Tezler ve akademik yayınlar ise **insan eliyle yazılmış, natif, yüksek register** Türkçe. Bu korpus onu sağlıyor.

---


## ⚡ HEDEF DEĞİŞTİ (2026-08-02 09:10 UTC) — önce burayı okuyun

PC-4'ün ölçümü depo seçimini kökten değiştirdi. Depoyu **kayıt sayısına göre seçmek
yanlıştı**; belirleyici sayı `kayıt × TEXT kapsaması`:

| depo | kayıt | TEXT | beklenen belge | durum |
|---|---|---|---|---|
| **Selçuk** | 54.840 | **%78** | **~42.775** | ✅ künye yayında, hasat edilecek |
| **Uludağ** | 51.951 | **%48** | **~24.936** | künye hasadı sürüyor |
| İTÜ | 68.911 | %44 | ~30.320 | ✅ tamamlandı |
| Marmara | 87.506 | %16,5 | ~14.469 | ⛔ **durdurun** |
| Ege | 118.818 | %4 | ~4.752 | ⛔ **durdurun** |
| Anadolu | 25.953 | %0 | 0 | ⛔ hiç başlamayın |

Ege 118.818 kayıtla listenin en büyüğü ve en az belgeyi veriyor. Marmara kampanyası
5 makine × ~32 saat karşılığında ~14.500 belge getirecek; **Selçuk tek başına onun
3 katı.** Devam eden marmara/ege koşularını durdurun — durdurmak bedava, `resume`
kaldığı yerden alır, tek satır kaybolmaz.

### Yeni komutunuz

```bash
git pull
python3 harvest.py text --repo selcuk --shard <PC-NUMARANIZ> --num-shards 5 --workers 1 --delay 3
```

`--repo` artık **tam adres de kabul ediyor**, yani yeni bir depo bulduğunuzda kodun
güncellenmesini beklemenize gerek yok:

```bash
python3 harvest.py text --repo https://acikerisim.uludag.edu.tr --shard 0 --num-shards 5
```

### Yeni depo önermeden önce ölçün

```bash
python3 probe_repos.py --sample 50 --delay 3
```

`kayıt × TEXT kapsaması` verir, Wilson aralığıyla. Kapsamı ölçülmemiş bir depoyu
filoya önermeyin — bugün 160 makine-saati bu yüzden kaybedildi.

## ⚠️ Önce bunu oku — nezaket kuralları

Bu sunucular üniversitelerin kütüphane altyapısı, CDN değil. **Aşırı yükleme yaparsak IP'miz banlanır ve herkes için erişim kapanır.**

- `--delay 3` (varsayılan) altına inme
- `--workers 2` üstüne çıkma — istek hızı artık GLOBAL sınırlı (tüm işçiler toplamı)
- Aynı üniversiteye **aynı anda iki makine** koşturma — shard sistemi bunu zaten engelliyor
- HTTP 429 / 500 görürsen **dur**, birkaç saat bekle, sonra tekrar dene

Sadece **açık erişim** içerik indiriliyor. Abonelik gerektiren yayıncı içeriğine (Elsevier, Springer, IEEE...) **dokunulmuyor** — o sözleşmeler toplu indirmeyi yasaklıyor.

---

## Kurulum (her makinede bir kez)

```bash
git clone https://github.com/RsGoksel/turkish-academic-corpus-harvester.git
cd turkish-academic-corpus-harvester
python3 -m venv .venv && . .venv/bin/activate
pip install -U pip
# Bağımlılık YOK — sadece Python 3.9+ standart kütüphanesi kullanılıyor.
python3 -c "import urllib.request, xml.etree.ElementTree; print('hazır')"
```

---

## Nasıl çalışıyor

İki aşama:

| aşama | ne yapar | süre | çıktı |
|---|---|---|---|
| **`meta`** | OAI-PMH ile tüm kayıtların künyesini çeker (başlık, yazar, özet, anahtar kelime) | ~1-2 saat | `data/repos/<kurum>/meta.jsonl` |
| **`text`** | Her kayıt için DSpace'in **önceden çıkardığı tam metni** indirir | uzun (shard'lanır) | `data/repos/<kurum>/text.shardN.jsonl` |

**Önemli:** DSpace, PDF'lerin metnini zaten çıkarmış durumda (`TEXT` bundle). Yani PDF indirip OCR yapmıyoruz — hazır metni çekiyoruz. Hem hızlı hem sunucuya nazik.

`meta` aşaması shard'lanmaz (tek makine yeter, hızlı). `text` aşaması shard'lanır.

---

## 🖥️ HANGİ MAKİNE NE YAPACAK

### ⚠️ ÖNCE BUNU YAP — künyeyi İNDİR, hasat ETME

Künye hasadı **bir kez yapıldı ve yayınlandı** (279.635 kayıt). Kendin çekme: hem
sunucuyu boşuna yorar, hem de shard hesabı için herkesin **aynı handle kümesini**
görmesi gerekir.

```bash
mkdir -p data/repos/itu data/repos/ege data/repos/marmara data/repos/hacettepe
BASE=https://github.com/RsGoksel/turkish-academic-corpus-harvester/releases/download/meta-v1
for r in itu ege marmara hacettepe; do
  curl -sL "$BASE/${r}_meta.jsonl.gz" | gunzip > data/repos/$r/meta.jsonl
done
wc -l data/repos/*/meta.jsonl
# beklenen: itu 68911 | ege 118818 | marmara 87506 | hacettepe 4400
```

### Sonra: kendi shard'ını çalıştır

Shard ataması `handle`'ın **hash**'ine göre yapılır — dosya sırasından bağımsızdır,
yani künyeyi nereden aldığın önemli değil, her makine aynı bölümlemeyi hesaplar.

| makine | komut |
|---|---|
| **PC-0** (dual5090) | `python3 harvest.py text --repo ege --shard 0 --num-shards 5 --workers 2 --delay 1.5` |
| **PC-1** | `python3 harvest.py text --repo ege --shard 1 --num-shards 5 --workers 1 --delay 3` |
| **PC-2** | `python3 harvest.py text --repo ege --shard 2 --num-shards 5 --workers 1 --delay 3` |
| **PC-3** | `python3 harvest.py text --repo marmara --shard 3 --num-shards 5 --workers 1 --delay 3` |
| **PC-4** | `python3 harvest.py text --repo marmara --shard 4 --num-shards 5 --workers 1 --delay 3` |

Ege bitince Marmara'ya, sonra Hacettepe'ye geçilir — sırayı Göksel duyurur.

**İTÜ tam metni bitti** (16.997 belge) — tekrar çekmeyin.

**Aynı anda iki aşama çalıştırmayın:** her process kendi hız sınırlayıcısını tutar;
ikisi aynı sunucuya giderse istek hızı ikiye katlanır ve nezaket sınırı delinir.
(Bu tespit PC-1'den geldi.)

**Geçici hatalar tekrar denenir:** `no_text_bundle` gibi kalıcı sonuçlar atlanır ama
HTTP hatası / zaman aşımı yiyen kayıtlar bir sonraki koşuda yeniden denenir. Yani
aynı komutu tekrar çalıştırmak güvenlidir ve eksik kalanı toplar.

## Doğrulanmış arşivler

| kurum | adres | kayıt | durum |
|---|---|---|---|
| İTÜ | `polen.itu.edu.tr` | 68.911 | ✅ künye + tam metin tamam |
| Ege | `acikerisim.ege.edu.tr` | 118.818 | 🔄 künye %61 |
| Marmara | `openaccess.marmara.edu.tr` | 87.506 | ✅ künye tamam |
| Hacettepe | `openaccess.hacettepe.edu.tr` | 33.178 | ⚠️ sunucu HTTP 500 veriyor, yavaş dene |

## Denenecek adresler (PC-4 için)

DSpace kalıbı genelde `https://<adres>/server/oai/request` (DSpace 7+) veya `https://<adres>/oai/request` (DSpace 6).

```
acikerisim.ktun.edu.tr        acikerisim.sakarya.edu.tr     acikerisim.erciyes.edu.tr
openaccess.ankara.edu.tr      acikerisim.atauni.edu.tr      acikerisim.pau.edu.tr
openaccess.yildiz.edu.tr      acikerisim.selcuk.edu.tr      acikerisim.gantep.edu.tr
acikerisim.akdeniz.edu.tr     openaccess.dogus.edu.tr       acikerisim.cu.edu.tr
acikerisim.ondokuzmayis.edu.tr  openaccess.iyte.edu.tr      acikerisim.kocaeli.edu.tr
```

---

## Çıktı formatı

**`meta.jsonl`** — her satır bir kayıt:
```json
{"oai_id":"oai:...","source":"itu","title":["Başlık","Title"],"creator":["Soyad, Ad"],
 "subject":["anahtar1","keyword1"],"description":["Türkçe özet...","English abstract..."],
 "date":["2024-06-28"],"type":["Master Thesis"],"language":["tr"],"handle":"11527/26309"}
```

**`text.shardN.jsonl`** — her satır bir tam metin:
```json
{"handle":"11527/26309","text":"İSTANBUL TEKNİK ÜNİVERSİTESİ...","title":"...",
 "type":"Master Thesis","date":"2024-06-28","language":"tr","source":"itu"}
```

---

## Bittiğinde — veriyi geri gönder

```bash
tar czf hasat_pc<N>_$(date +%F).tar.gz data/repos/
# Göksel'e ilet (scp / rsync / bulut yükleme — sana söylenecek yol)
```

İlerlemeyi paylaşmak için:
```bash
wc -l data/repos/*/meta.jsonl data/repos/*/text*.jsonl
```

---

## Sorun giderme

| belirti | ne yap |
|---|---|
| `HTTP 500` | Sunucu hatası, senin sorunun değil. `--delay 10` ile tekrar dene, olmazsa saatler sonra. |
| `Connection refused` | Hız limitine takıldık. **Dur.** `--delay 5 --workers 1` ile yeniden başla. |
| `no_text_bundle` çok fazla | Normal — makalelerin tam metni yok, sadece tezlerde var. İTÜ'de %75 bu şekilde. |
| İşlem yarıda kesildi | Sorun değil, **kaldığı yerden devam eder**. Aynı komutu tekrar çalıştır. |

## Lisans / etik

Toplanan içerik ilgili kurumların açık erişim politikaları altında yayımlanmıştır. Her kaydın künyesinde kaynak ve handle saklanır, böylece atıf zinciri korunur. Abonelik gerektiren içerik toplanmaz.
