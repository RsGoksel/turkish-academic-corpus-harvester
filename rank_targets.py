#!/usr/bin/env python3
"""Hedef sıralamasını ÖLÇÜLEN verime göre kur, kayıt sayısına göre değil.

SOURCES.md'nin ilk hâli depoları `kayıt × n=5 örneklem` ile sıralıyordu ve filoyu
listenin tepesindeki Ege'ye yönlendiriyordu -- bildiğimiz en düşük verimli
depolardan biri. n=5'te 5/5 gelmesi "%100" demek değildir; o örneklemde %95 aralığı
kabaca %48-100'dür.

Verim üç kapıdan geçer ve üçü de ayrı ayrı ölçülmelidir:

  1. TEXT paketi VAR mı            -- tarama söyler
  2. Paket DOLU mu                 -- 2 baytlık yer tutucular var (PC-2 buldu)
  3. Paket OKUNABİLİR mi           -- dolu ama 401 dönebilir (PC-4 buldu)

Bilkent bunun ders kitabı örneği: 52.198 kayıt, 50.143'ünde paket var (%96),
45.741'i dolu (%88), ama 40 örnekten 19'u 401 döndü -- okunabilir ~%52. Gerçek
beklenti 52.198 değil ~24.000. Tek kapıya bakan her tahmin şişer.

Bu betik ölçülmüş değerleri kullanır, ölçülmemişleri AYRI listeler ve tahmin
üretmez -- "bilmiyoruz" demek, dört kat şişik bir sayı vermekten iyidir.

    python3 rank_targets.py
"""
from __future__ import annotations

import json
from pathlib import Path

# Ölçülmüş değerler. Her satırın kaynağı ve örneklem boyu yazılı;
# n küçükse aralık geniştir ve bu tabloda görünür.
MEASURED = {
    # depo:        (kayıt,  paket_var, dolu,   okunabilir, kaynak)
    "bilkent":     (52198, 0.961, 0.876, 0.525, "PC-4 tam tarama + PC-0 n=40 erişim"),
    "hacettepe":   (32978, 0.987, 0.711, None,  "PC-2 tam shard sayımı"),
    "selcuk":      (54829, 0.623, 0.569, None,  "PC-1+PC-2 scan n=21.925"),
    "dicle":       (30146, 0.422, 0.352, None,  "PC-3 scan"),
    "aksaray":     (13016, 0.885, 0.885, 0.900, "PC-4 probe"),
    "adiyaman":    (16094, 0.250, 0.250, 1.000, "PC-4 probe — n=5 örneklem %100 demişti"),
    "ege":        (118666, 0.040, None,  None,  "PC-4 probe (n=5 örneklem %100 demişti)"),
    "omu":         (46134, 0.000, None,  None,  "tam probe 0/50"),
    "itu_polen":   (68911, 0.247, 0.247, 1.000, "TAMAMLANDI: 16.997 belge / 68.911"),
}


def expected(rec: int, have, full, readable) -> int | None:
    """Üç kapının çarpımı. Ölçülmemiş kapı 1.0 SAYILMAZ -- None döner."""
    if have is None:
        return None
    f = full if full is not None else have      # dolu ölçülmediyse paket oranı tavan
    r = readable if readable is not None else None
    if r is None:
        return None                              # erişim ölçülmeden sayı verilmez
    return int(rec * f * r)


def main():
    rows = []
    for depo, (rec, have, full, read, src) in MEASURED.items():
        exp = expected(rec, have, full, read)
        rows.append({"depo": depo, "kayit": rec, "paket": have, "dolu": full,
                     "okunabilir": read, "beklenti": exp, "kaynak": src})

    known = sorted((r for r in rows if r["beklenti"] is not None),
                   key=lambda r: -r["beklenti"])
    unknown = sorted((r for r in rows if r["beklenti"] is None),
                     key=lambda r: -(r["kayit"] * (r["paket"] or 0)))

    def pct(x):
        return "—" if x is None else f"%{100*x:.1f}"

    print("=== BEKLENTİSİ ÖLÇÜLMÜŞ (üç kapı da biliniyor) ===")
    print(f"{'depo':<12}{'kayıt':>8}{'paket':>8}{'dolu':>8}{'okunur':>8}{'BELGE':>9}  kaynak")
    for r in known:
        print(f"{r['depo']:<12}{r['kayit']:>8,}{pct(r['paket']):>8}{pct(r['dolu']):>8}"
              f"{pct(r['okunabilir']):>8}{r['beklenti']:>9,}  {r['kaynak'][:34]}")

    print("\n=== ERİŞİM ÖLÇÜLMEDİ — sayı verilmiyor ===")
    print(f"{'depo':<12}{'kayıt':>8}{'paket':>8}{'dolu':>8}  tavan (erişim %100 olsa)")
    for r in unknown:
        f = r["dolu"] if r["dolu"] is not None else r["paket"]
        cap = int(r["kayit"] * f) if f else 0
        print(f"{r['depo']:<12}{r['kayit']:>8,}{pct(r['paket']):>8}{pct(r['dolu']):>8}"
              f"  ≤{cap:,}  {r['kaynak'][:30]}")

    Path("data").mkdir(exist_ok=True)
    Path("data/target_ranking.json").write_text(
        json.dumps({"measured": known, "access_unmeasured": unknown},
                   indent=2, ensure_ascii=False))
    print("\nkaydedildi: data/target_ranking.json")


if __name__ == "__main__":
    main()
