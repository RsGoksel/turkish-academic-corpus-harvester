# Türk Üniversiteleri Açık Arşiv Hasatçısı

Türkiye'deki üniversitelerin **açık erişim** kurumsal arşivlerinden (DSpace) natif Türkçe akademik metin toplar. Toplanan korpus, Türkçe bir LLM'in **continued pre-training (CPT)** aşamasında kullanılır.

**Neden bu veri:** Türkçe LLM'lerin en büyük sorunu makine çevirisi verisiyle eğitilmeleri — model "çeviri kokan" Türkçe üretiyor. Tezler ve akademik yayınlar ise **insan eliyle yazılmış, natif, yüksek register** Türkçe. Bu korpus onu sağlıyor.

---

## ⚠️ Önce bunu oku — nezaket kuralları

Bu sunucular üniversitelerin kütüphane altyapısı, CDN değil. **Aşırı yükleme yaparsak IP'miz banlanır ve herkes için erişim kapanır.**

- `--delay 3` (varsayılan) altına inme
- `--workers 4` üstüne çıkma
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

**5 makine var. Kendi numaranı bul ve SADECE o bölümdeki komutları çalıştır.**

### PC-0 — dual5090 (ana makine, Göksel'in)
Bu makine İTÜ'yü zaten bitirdi (68.911 künye + 16.997 tam metin) ve koordinasyonu yapıyor.
```bash
python3 harvest.py text --repo itu --shard 0 --num-shards 5 --workers 4 --delay 1
```

### PC-1
```bash
# 1) Önce künyeleri çek (yoksa)
python3 harvest.py meta --repo ege --delay 3
# 2) Sonra tam metin — kendi payın
python3 harvest.py text --repo ege --shard 1 --num-shards 5 --workers 3 --delay 1
```

### PC-2
```bash
python3 harvest.py meta --repo marmara --delay 3
python3 harvest.py text --repo marmara --shard 2 --num-shards 5 --workers 3 --delay 1
```

### PC-3
```bash
python3 harvest.py meta --repo hacettepe --delay 5   # bu sunucu hassas, delay yüksek
python3 harvest.py text --repo hacettepe --shard 3 --num-shards 5 --workers 2 --delay 2
```

### PC-4 — keşif görevi
Yeni üniversite arşivi bul (aşağıdaki listeden test et), çalışanı `harvest.py` içindeki `REPOS` sözlüğüne ekle, sonra hasat et:
```bash
# Test:
curl -s "https://<adres>/server/oai/request?verb=Identify" | grep repositoryName
# Çalışıyorsa REPOS'a ekle, sonra:
python3 harvest.py meta --repo <yeni_kurum> --delay 3
python3 harvest.py text --repo <yeni_kurum> --shard 4 --num-shards 5 --workers 3 --delay 1
```

---

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
