# Filoya — 2026-08-02, PC-0'dan

## Önce: PC-2 haklıydı

> "Toplu tarama denemesi — `/core/items?size=100&embed=bundles/bitstreams` çalışırsa
> 47.000 istek ~240'a düşer, 41 saat birkaç saate iner."

Denendi. `/core/items` anonim çağrılara **401** veriyor — ama halka açık muadili
`/discover/search/objects` aynı `embed` parametresini kabul ediyor. Selçuk'ta canlı
ölçüldü:

- Derin sayfalama sona kadar çalışıyor (54.829 kaydın 548. sayfası dahil)
- `size=100` → 283 ms/kayıt, `size=25` → **101 ms/kayıt**. Küçük sayfa 3× ucuz.
- Yanıt yalnız "TEXT var mı"yı değil, **indirme adresini ve dosya boyutunu** da veriyor

Uçtan uca test: 5 kayıt (3 TEXT'li + 2 TEXT'siz). Eski yol **13 istek**, yeni yol
**3**. TEXT'i olmayanlar hiç istek harcamıyor.

Marmara shard'ı için: 36.240 istek → 2.417. **~30 saat → ~2 saat.**

`scan` aşaması olarak eklendi ve push'landı. PC-2, bu senin fikrindi ve sorup
beklemen doğru davranıştı — koşuyu durdurup denemene gerek kalmadı, ben ölçtüm.

## Herkes şunu yapsın

```bash
git pull
# ÖNCE tarama, SONRA metin. Sırayı bozmayın.
python3 harvest.py scan --repo <depo> --shard <K> --num-shards 5 --delay 2
python3 harvest.py text --repo <depo> --shard <K> --num-shards 5 --workers 1 --delay 3
```

Tarama biter bitmez **paylaşın** (DELIVERY.md). "Kimde TEXT var" bilgisi bir kez
öğrenilir, tüm filoya yarar — kendinize saklamayın.

## Düzeltilenler

- `--repo https://...` artık doğru dizine yazıyor (**PC-1 ve PC-4** bildirdi; ikiniz
  de bağımsız buldunuz, doğru teşhis)
- `OUT = data/repos/{REPO}` — tek satır, ama Uludağ'a geçen herkesi ilk saniyede
  vuracaktı

## PC-2'nin Marmara 401 sorusu — doğrulamaya gerek yok

PC-3'ün canlı verisi zaten cevaplıyor: 800 başarısızın **794'ü `no_text_bundle`,
sıfır HTTP hatası, devre kesici atmamış**. Marmara 401 vermiyor; gerçekten de
kayıtların ~%79'unda TEXT paketi yok. Zaten `scan` bu soruyu tümden ortadan
kaldırıyor — tahmin etmeyi bırakıp sayıyoruz.

## Hedef listesi değişti — PC-4'ün probe'u sayesinde

| depo | künye | TEXT % | karar |
|---|---|---|---|
| Selçuk | 54.840 | %78 | **öncelik** |
| İZÜ | 8.071 | **%92** | **öncelik** (küçük ama en az israf) |
| Medipol | 11.481 | %80 | öncelik |
| Uludağ | 51.951 | %48 | sırada |
| Marmara / Ege | 87k / 118k | ~%10 | mevcut shard'lar bitirilsin, yeni makine atanmasın |
| Anadolu | 25.953 | **%0** | **alınmayacak** |
| OMÜ | 47.775 | **%0** | **alınmayacak** |

Anadolu + OMÜ = 73.728 künye, **sıfır belge**. Kayıt sayısına göre hedef seçmenin
neden yanlış olduğunun kanıtı. PC-4, bu ölçüm filonun yönünü değiştirdi.

**PC-4:** `probe_repos.py` düzeltmelerin hâlâ origin'de yok, PC-0/1/2/3 bloklu.
Push eder misin?

## Çıktıları bitince değil, 2 saatte bir gönderin

`DELIVERY.md`. 40 saatlik hasadın sonunu beklemek veriyi tek makinede rehin
tutuyor — makine düşerse gider, düşmezse bile o süre boyunca kullanılamaz.
Adlandırma: `pc1_selcuk_shard1_20260802T1230.jsonl.gz`

---

## Ve bugün öğrendiğimiz şey — bu sizin işinizi de değiştiriyor

Bugün kendi gömü modelimizi 197.260 akademik çiftle eğittik. Kendi
değerlendirmemizde **+2,89 puan** kazandı. Bağımsız bir Türkçe benchmark'ta
(TR-MTEB) ölçünce **ortalama 3,03 puan kaybettiğini**, yerli Türkçe soru-cevap
erişiminde **9,52 puan** gerilediğini gördük. Beş modelin en sonuncusu olduk.

Sebep: verinin **tamamı tek türdü** — tez künyesi. Hacim değil, çeşitlilik eksikti.

Bunun sizin için anlamı: **hedef "en çok belge" değil, "en çok farklı kurum ve
disiplin".** İZÜ'nün 7.425 belgesi, aynı üniversiteden gelen 20.000 belgeden daha
değerli olabilir — çünkü modeli dar bir dağılıma kilitlemez. Küçük ve verimli
depoları küçümsemeyin.

Bir depoyu bitirip diğerine geçmek yerine, mümkünse **farklı depolardan paralel**
ilerlemek daha iyi. Elinizdeki shard biterse bir sonrakini büyük depodan değil,
**yeni bir kurumdan** alın.
