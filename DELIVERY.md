# Çıktıları gönderme — paket paket, beklemeden

**Sorun:** hasat 30-40 saat sürüyor ve makineler "bitince tar.gz atarım" diyor.
O zamana kadar veri tek bir VPS'te duruyor: kullanılamıyor, yedeklenmemiş, makine
düşerse gidiyor. **Her 2 saatte bir parça gönderin.**

Hedef: `RsGoksel/turkish-academic-corpus` (HuggingFace dataset, **private**)

Neden Drive değil: Drive'a yükleme oturum açmış bir tarayıcı ister; başsız
sunucuda OAuth akışı yok. HF dataset deposu GB ölçeği için tasarlanmış, sürümlü,
tek komut.

---

## Bir kereye mahsus kurulum

```bash
pip install -U "huggingface_hub[cli]"
hf auth login          # Göksel'in verdiği yazma yetkili token'ı yapıştırın
```

Token **yalnızca bu veri setine yazma yetkili** olmalı (fine-grained token,
`Write access to contents` yalnız `RsGoksel/turkish-academic-corpus` için).
Token'ı log'a, commit'e, ekran görüntüsüne koymayın.

## Her ~2 saatte bir: parçayı gönder

```bash
PC=1                      # kendi numaranız
REPO=selcuk               # hasat ettiğiniz depo
SHARD=1

STAMP=$(date -u +%Y%m%dT%H%M)
SRC=data/repos/$REPO/text.shard$SHARD.jsonl
PKG=pc${PC}_${REPO}_shard${SHARD}_${STAMP}.jsonl.gz

gzip -c "$SRC" > "/tmp/$PKG"
hf upload RsGoksel/turkish-academic-corpus "/tmp/$PKG" \
    "shards/$REPO/$PKG" --repo-type dataset
rm "/tmp/$PKG"
```

Adlandırma **tam olarak** böyle olsun — `pc<N>_<depo>_shard<K>_<zaman>.jsonl.gz`.
Zaman damgası UTC ve `YYYYMMDDTHHMM`. Böylece:

- kimin gönderdiği, hangi depo, hangi shard, ne zaman → dosya adından okunur
- aynı shard'ın ardışık paketleri sıralanır
- **üzerine yazma olmaz**; her paket ayrı dosya

Paketler **birikimli** olabilir (dosyanın o anki tam hali). Tekrarlanan satırlar
handle'a göre birleştirmede elenir — eksik göndermektense fazla gönderin.

## Tarama çıktısı da gönderilir

```bash
hf upload RsGoksel/turkish-academic-corpus \
    data/repos/$REPO/scan.shard$SHARD.jsonl \
    "scans/$REPO/pc${PC}_scan_shard${SHARD}.jsonl" --repo-type dataset
```

Tarama, sizin shard'ınız dışındaki makinelere de yarar: hangi kayıtta TEXT
olduğunu bir kez öğrenip herkesle paylaşıyoruz. **Bittiği anda gönderin**, 2 saat
beklemeyin.

## Otomatik hale getirin

```bash
cat > ~/upload_loop.sh <<'EOS'
#!/bin/bash
PC=1; REPO=selcuk; SHARD=1
cd /root/turkish-academic-corpus-harvester || exit 1
while true; do
  sleep 7200
  SRC=data/repos/$REPO/text.shard$SHARD.jsonl
  [ -s "$SRC" ] || continue
  STAMP=$(date -u +%Y%m%dT%H%M)
  PKG=pc${PC}_${REPO}_shard${SHARD}_${STAMP}.jsonl.gz
  gzip -c "$SRC" > "/tmp/$PKG"
  hf upload RsGoksel/turkish-academic-corpus "/tmp/$PKG" \
      "shards/$REPO/$PKG" --repo-type dataset && echo "$(date -u) gonderildi $PKG"
  rm -f "/tmp/$PKG"
done
EOS
chmod +x ~/upload_loop.sh
nohup ~/upload_loop.sh >> ~/upload_loop.log 2>&1 &
```

Yükleme hasadı yavaşlatmaz — ağ işi, hız sınırlayıcıdan geçmez ve hedef sunucu
üniversite değil HuggingFace.

## Rapor ederken

Paketi gönderdikten sonra Göksel'e tek satır yeter:

```
pc1 selcuk shard1 -> 3.412 belge / 41M token, son paket 20260802T1230
```
