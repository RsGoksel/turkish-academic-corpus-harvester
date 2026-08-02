# Kaynak defteri — hangi depodan ne aldık, neyi alamadık

Bu dosya **tek doğruluk kaynağıdır**. Bir depoya dokunan her makine sonucu buraya
işler. "Denedik mi?" ve "ne çıktı?" sorularının cevabı burada olmalı; log dosyaları
makinelerde kalır, bu dosya ortakta durur.

Ölçümler `probe_repos.py` ile alındı: her depodan 50 kayıtlık rastgele örnek çekilip
TEXT paketi olan oranı sayıldı. **Kayıt sayısı yanıltıcıdır** — asıl ölçü
`kayıt × TEXT kapsaması`. Anadolu'nun 25.953 kaydı var ve tek belge vermiyor.

Son güncelleme: 2026-08-02 10:50 UTC

---

## A. Tamamlananlar

| depo | adres | künye | belge | durum |
|---|---|---|---|---|
| İTÜ | https://polen.itu.edu.tr | 68.911 | **16.997** | ✅ tam metin bitti |

## B. Sürmekte

| depo | adres | künye | TEXT % | beklenen | atanan | not |
|---|---|---|---|---|---|---|
| Selçuk | https://acikerisim.selcuk.edu.tr | 54.840 | %78 | ~42.775 | PC-1 (shard 1/5) | filonun en verimli hedefi |
| Marmara | https://acikerisim.marmara.edu.tr | 87.506 | ~%10 | ~8.750 | PC-3 (shard 3/5) | düşük verim, bkz. §D |
| Ege | https://acikerisim.ege.edu.tr | 118.818 | ~%10 | ~11.800 | PC-2 (shard 2/5) | düşük verim, bkz. §D |
| Uludağ | https://acikerisim.uludag.edu.tr | 51.951 | %48 | ~24.936 | — | sırada |

## C. Ölçüldü, sırada bekliyor

| depo | adres | künye | TEXT % | %95 aralık | beklenen belge |
|---|---|---|---|---|---|
| Medipol | https://acikerisim.medipol.edu.tr | 11.481 | %80 | 67–89 | ~9.184 |
| AKÜ | https://acikerisim.aku.edu.tr | 26.766 | %34 | 22–48 | ~9.100 |
| İZÜ | https://openaccess.izu.edu.tr | 8.071 | **%92** | 81–97 | ~7.425 |
| Altınbaş | https://openaccess.altinbas.edu.tr | 6.075 | %24 | 14–37 | ~1.458 |

**İZÜ en verimli depo** — küçük ama neredeyse hiç israf yok.

## D. Ölçüldü, ALINMAYACAK

| depo | künye | TEXT % | neden |
|---|---|---|---|
| Anadolu | https://earsiv.anadolu.edu.tr | 25.953 | **%0** — TEXT paketi hiç üretilmemiş |
| OMÜ | https://acikerisim.omu.edu.tr | 47.775 | **%0** — aynı |

Bu ikisi künye olarak listenin en büyüklerinden ama tek belge vermiyor. Kayıt
sayısına göre hedef seçmenin neden yanlış olduğunun kanıtı.

Marmara ve Ege %10 civarında; PC-4'ün ölçümünden sonra öncelik Selçuk/Uludağ/İZÜ'ye
kaydırıldı. Devam eden shard'lar bitirilir, yeni makine bunlara atanmaz.

## E. Erişilemedi — sınıflandırma sürüyor

11 host cevap vermedi. Beşi HTTP 404 (Sakarya elle doğrulandı: **DSpace 6**, ayakta —
bu araç DSpace 7 REST API'si kullanıyor, DSpace 6 farklı uç noktalara sahip), altısı
bağlantı hatası. **TEXT kapsaması ölçülmedi**, sıfır olduğu anlamına gelmez.

| depo | belirti | not |
|---|---|---|
| Sakarya | 404 | DSpace 6 doğrulandı |
| (10 host) | 404 / bağlantı | PC-4 sınıflandırması sürüyor |

## F. Erişim reddedilenler — bilinçli olarak alınmayacak

| kaynak | neden |
|---|---|
| YÖK Ulusal Tez Merkezi | e-Devlet (T.C. kimlik) girişi gerektiriyor — kullanılmadı |
| Elsevier / Springer / IEEE (İTÜ aboneliği) | Sözleşmeler toplu indirme ve TDM'i yasaklıyor; tetiklenirse İTÜ'nün tüm IP aralığı kapanır. Meşru yol: kurumsal TDM izin başvurusu |

---

## Ölçüm yöntemi

`python3 probe_repos.py` — her depodan `discover/search/objects` ile 50 kayıtlık
örnek, `embed=bundles/bitstreams` ile TEXT paketi kontrolü. %95 aralık normal
yaklaşımla; n=50 olduğu için aralıklar geniş, nokta tahmine tek başına güvenme.
