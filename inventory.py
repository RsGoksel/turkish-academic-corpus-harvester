#!/usr/bin/env python3
"""Her denenen kayıt için tek satırlık kalıcı defter üretir — olan da olmayan da.

Hasat sırasında sonuç üç ayrı dosyaya dağılıyor (text / failed / restricted) ve
"neden" bilgisi eksik kalıyor: hangi adresten çekildi, kaç bayttı, hangi kurumun
kaydıydı. Bu betik meta + scan + text + failed + restricted dosyalarını
birleştirip depo başına tek bir envanter üretir.

İki çıktı:
  data/reports/<depo>_inventory.jsonl   her handle bir satır, sonuç + sebep + adres
  data/reports/<depo>_bos_belgeler.csv  kuruma bildirilecek BOŞ dosyalar

Kullanım:  python3 inventory.py [depo ...]     (boş bırakılırsa hepsi)
"""
import csv
import glob
import json
import sys
from pathlib import Path

REPORTS = Path("data/reports")


def load_jsonl(path, key="handle"):
    out = {}
    if not Path(path).exists():
        return out
    with open(path) as f:
        for line in f:
            try:
                r = json.loads(line)
            except Exception:
                continue
            h = r.get(key)
            if h:
                out[h] = r          # sonraki satır öncekini ezer: en güncel sonuç
    return out


def classify(err, n_bytes, has_urls):
    """Hata dizgisini kuruma bildirilebilir bir kategoriye indirger.

    BOS_DOSYA ile TEXT_PAKETI_YOK ayrımı `has_urls`'e dayanır, bayta değil:
    TEXT paketi hiç olmayan kayıtta tarama zaten bayt=0 yazar, bu "dosya boş"
    demek değildir. Kuruma bildirilecek olan yalnız birincisi -- indirme adresi
    yayımlanmış ama arkasında içerik yok.
    """
    e = str(err or "")
    if e.startswith("too_short_0"):
        return "BOS_DOSYA", "TEXT dosyası indirildi, içi boş"
    if e.startswith("too_short"):
        return "COK_KISA", f"metin {e.split('_')[-1]} karakter (eşiğin altında)"
    if e.startswith("restricted_"):
        return "ERISIM_KAPALI", f"bitstream {e.replace('restricted_', '')}"
    if e == "no_text_bundle":
        if has_urls:
            if isinstance(n_bytes, int) and n_bytes < 2000:
                return "BOS_DOSYA", f"TEXT dosyası {n_bytes} bayt (yer tutucu)"
            return "TEXT_INDIRILEMEDI", "adres var ama içerik alınamadı"
        return "TEXT_PAKETI_YOK", "DSpace metni çıkarmamış"
    if e == "no_uuid":
        return "KAYIT_BULUNAMADI", "handle REST API'de çözülmedi"
    if e:
        return "GECICI_HATA", e
    return "BILINMIYOR", ""


def build(repo):
    base = Path("data/repos") / repo
    meta = {}
    if (base / "meta.jsonl").exists():
        with open(base / "meta.jsonl") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if r.get("handle"):
                    meta[r["handle"]] = r

    scan = {}
    for p in sorted(base.glob("scan*.jsonl")):
        scan.update(load_jsonl(p))

    ok, failed, restricted = {}, {}, {}
    for p in sorted(base.glob("text*.jsonl")):
        if ".failed." in p.name:
            failed.update(load_jsonl(p))
        else:
            ok.update(load_jsonl(p))
    for p in sorted(base.glob("restricted*.jsonl")):
        restricted.update(load_jsonl(p))

    REPORTS.mkdir(parents=True, exist_ok=True)
    inv_path = REPORTS / f"{repo}_inventory.jsonl"
    csv_path = REPORTS / f"{repo}_bos_belgeler.csv"

    counts = {}
    empties = []
    with open(inv_path, "w") as f:
        for h in sorted(set(meta) | set(ok) | set(failed) | set(restricted)):
            m = meta.get(h, {})
            s = scan.get(h, {})
            n_bytes = s.get("bytes")
            urls = s.get("text_urls") or []
            if h in ok:
                sonuc, kategori, aciklama = "BASARILI", "BASARILI", ""
                karakter = len(ok[h].get("text") or "")
            else:
                rec = restricted.get(h) or failed.get(h) or {}
                err = rec.get("error")
                if not rec and h in meta:
                    sonuc, kategori, aciklama = "DENENMEDI", "DENENMEDI", "bu shard'a düşmedi"
                else:
                    sonuc = "BASARISIZ"
                    kategori, aciklama = classify(err, n_bytes, bool(urls))
                karakter = 0

            counts[kategori] = counts.get(kategori, 0) + 1
            row = {
                "handle": h,
                "kurum": repo,
                "sonuc": sonuc,
                "kategori": kategori,
                "aciklama": aciklama,
                "karakter": karakter,
                "bayt": n_bytes,
                "metin_adresi": urls[0] if urls else None,
                "kayit_adresi": f"https://hdl.handle.net/{h}",
                "baslik": (m.get("title") or [None])[0],
                "tur": (m.get("type") or [None])[0],
                "tarih": (m.get("date") or [None])[-1] if m.get("date") else None,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            if kategori == "BOS_DOSYA":
                empties.append(row)

    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["handle", "kayit_adresi", "metin_adresi", "bayt", "baslik", "tur", "tarih"])
        for r in empties:
            w.writerow([r["handle"], r["kayit_adresi"], r["metin_adresi"],
                        r["bayt"], r["baslik"], r["tur"], r["tarih"]])

    print(f"\n{repo}: {inv_path}")
    for k, v in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"   {k:20s} {v:7,}")
    if empties:
        print(f"   -> kuruma bildirilecek BOŞ dosya: {len(empties):,}  ({csv_path})")
    return counts


if __name__ == "__main__":
    repos = sys.argv[1:] or [Path(p).parent.name
                             for p in sorted(glob.glob("data/repos/*/meta.jsonl"))]
    for r in repos:
        build(r)
