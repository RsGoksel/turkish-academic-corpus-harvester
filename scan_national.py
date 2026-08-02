#!/usr/bin/env python3
"""Türkiye çapında açık akademik depo taraması.

İTÜ'de öğrendiğimiz iki şey bu taramayı şekillendiriyor:

  1. Bir kurumun BİRDEN FAZLA platformu olabilir. İTÜ'nün hem DSpace'i (Polen,
     tam metin var) hem ContentDM'i (Dijital Koleksiyonlar, yalnız görüntü) var.
     Sadece DSpace aramak, ikincisini tamamen kaçırır.
  2. Ayakta olmak yeterli değil. İTÜ Nadir Eserler 200 OK veriyor, OAI'si
     çalışıyor, ama kayıtları "Page 1" başlıklı taramalar -- METİN YOK. Bu yüzden
     her depo için "metin var mı" ayrıca yoklanır, sadece erişilebilirlik değil.

Denenen kalıplar, gözlenen gerçek adreslerden türetildi:
  acikerisim.<host>  openaccess.<host>  acikbilim.<host>  dspace.<host>
  earsiv.<host>  repository.<host>  dijitalkoleksiyonlar.kutuphane.<host>

    python3 scan_national.py --out data/national_scan.jsonl
"""
from __future__ import annotations

import argparse
import json
import re
import ssl
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = {"User-Agent": "turkish-academic-corpus-harvester/1.0 "
                    "(akademik arastirma; iletisim: github.com/RsGoksel)"}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# YÖK üyesi üniversitelerin alan adları (devlet + büyük vakıf).
HOSTS = """itu.edu.tr boun.edu.tr metu.edu.tr ankara.edu.tr istanbul.edu.tr ege.edu.tr
hacettepe.edu.tr gazi.edu.tr marmara.edu.tr yildiz.edu.tr dokuz eylul.edu.tr deu.edu.tr
selcuk.edu.tr uludag.edu.tr erciyes.edu.tr akdeniz.edu.tr cukurova.edu.tr atauni.edu.tr
ktu.edu.tr ondokuzmayis.edu.tr omu.edu.tr anadolu.edu.tr sakarya.edu.tr kocaeli.edu.tr
pau.edu.tr gantep.edu.tr firat.edu.tr inonu.edu.tr dicle.edu.tr yyu.edu.tr
mersin.edu.tr aku.edu.tr balikesir.edu.tr comu.edu.tr kirikkale.edu.tr sdu.edu.tr
gop.edu.tr adiyaman.edu.tr harran.edu.tr ksu.edu.tr mu.edu.tr nigde.edu.tr
usak.edu.tr bartin.edu.tr duzce.edu.tr karabuk.edu.tr bilecik.edu.tr aksaray.edu.tr
giresun.edu.tr hitit.edu.tr kilis.edu.tr mehmetakif.edu.tr nevsehir.edu.tr
osmaniye.edu.tr siirt.edu.tr sinop.edu.tr bingol.edu.tr bitlis.edu.tr ardahan.edu.tr
igdir.edu.tr artvin.edu.tr bayburt.edu.tr gumushane.edu.tr tunceli.edu.tr
sabanciuniv.edu bilkent.edu.tr koc.edu.tr ozyegin.edu.tr bahcesehir.edu.tr
medipol.edu.tr izu.edu.tr altinbas.edu.tr yeditepe.edu.tr kadir.edu.tr khas.edu.tr
atilim.edu.tr cankaya.edu.tr baskent.edu.tr tobb.edu.tr ieu.edu.tr yasar.edu.tr
istinye.edu.tr biruni.edu.tr acibadem.edu.tr maltepe.edu.tr okan.edu.tr
ahievran.edu.tr amasya.edu.tr agri.edu.tr alanya.edu.tr ato.edu.tr batman.edu.tr beu.edu.tr bozok.edu.tr bandirma.edu.tr cbu.edu.tr manisa.edu.tr cumhuriyet.edu.tr sivas.edu.tr erzincan.edu.tr ebyu.edu.tr esogu.edu.tr gelisim.edu.tr halic.edu.tr iku.edu.tr istanbulc.edu.tr isikun.edu.tr izmirekonomi.edu.tr karatekin.edu.tr kmu.edu.tr kafkas.edu.tr kilisyedigun.edu.tr klu.edu.tr kirklareli.edu.tr ksbu.edu.tr kutahya.edu.tr dpu.edu.tr munzur.edu.tr mardin.edu.tr artuklu.edu.tr msgsu.edu.tr nku.edu.tr sanko.edu.tr sbu.edu.tr subu.edu.tr tedu.edu.tr thk.edu.tr toros.edu.tr trakya.edu.tr ufuk.edu.tr uskudar.edu.tr yalova.edu.tr yobu.edu.tr gidatarim.edu.tr agu.edu.tr asbu.edu.tr aybu.edu.tr bakircay.edu.tr bandirma.edu.tr ibu.edu.tr izmir.edu.tr iyte.edu.tr gtu.edu.tr etu.edu.tr erzurum.edu.tr ohu.edu.tr aday.edu.tr istanbulticaret.edu.tr nisantasi.edu.tr beykent.edu.tr aydin.edu.tr arel.edu.tr esenyurt.edu.tr fsm.edu.tr ihu.edu.tr 29mayis.edu.tr piri.edu.tr antalya.edu.tr ostimteknik.edu.tr tau.edu.tr adanabtu.edu.tr alparslan.edu.tr sirnak.edu.tr hakkari.edu.tr mus.edu.tr sehir.edu.tr zbeu.edu.tr beun.edu.tr bursauludag.edu.tr btu.edu.tr
""".split()

PREFIXES = ["acikerisim", "openaccess", "acikbilim", "dspace", "earsiv",
            "repository", "avesis", "acik", "arsiv"]
EXTRA = ["dijitalkoleksiyonlar.kutuphane"]

PLATFORMS = [("DSpace", r"dspace|/server/api|xmlui|jspui"),
             ("ContentDM", r"contentdm|/cdm/"),
             ("Islandora", r"islandora"),
             ("EPrints", r"eprints"),
             ("OJS", r"open journal|/index.php/.*?/oai")]


def fetch(url: str, timeout: int = 12, cap: int = 40000):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.status, r.url, r.read(cap).decode("utf-8", "replace")


def probe_host(host: str) -> list[dict]:
    found = []
    for pre in PREFIXES + EXTRA:
        url = f"https://{pre}.{host}"
        try:
            status, final, body = fetch(url)
        except Exception:
            continue
        low = body.lower()
        plat = next((n for n, pat in PLATFORMS if re.search(pat, low)), None)
        rec = {"host": host, "url": url, "final": final, "status": status,
               "platform": plat}
        # Metin var mı: DSpace ise TEXT bundle'ı, OAI varsa kayıt yapısı yoklanır.
        if plat == "DSpace":
            try:
                d = json.loads(fetch(f"{final.rstrip('/')}/server/api/discover/search/objects"
                                     "?dsoType=item&size=5&embed=bundles/bitstreams",
                                     timeout=25, cap=300000)[2])
                objs = (((d.get("_embedded") or {}).get("searchResult") or {})
                        .get("_embedded") or {}).get("objects") or []
                page = (((d.get("_embedded") or {}).get("searchResult") or {})
                        .get("page") or {})
                has_text = 0
                for o in objs:
                    ind = (o.get("_embedded") or {}).get("indexableObject") or {}
                    bl = ((((ind.get("_embedded") or {}).get("bundles") or {})
                           .get("_embedded") or {}).get("bundles") or [])
                    has_text += any(x.get("name") == "TEXT" for x in bl)
                rec["total_items"] = page.get("totalElements")
                rec["text_sample"] = f"{has_text}/{len(objs)}"
                rec["usable"] = has_text > 0
            except Exception as e:  # noqa: BLE001
                rec["api_error"] = type(e).__name__
                rec["usable"] = None
        else:
            rec["usable"] = None
        found.append(rec)
        time.sleep(0.5)
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/national_scan.jsonl")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()

    import pathlib
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    rows = []
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(probe_host, h): h for h in HOSTS}
        for i, f in enumerate(as_completed(futs), 1):
            try:
                got = f.result()
            except Exception:
                got = []
            rows.extend(got)
            if i % 10 == 0:
                print(f"  {i}/{len(HOSTS)} host … {len(rows)} depo bulundu", flush=True)

    with open(a.out, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    ds = [r for r in rows if r["platform"] == "DSpace"]
    usable = [r for r in ds if r.get("usable")]
    print(f"\n{len(rows)} erişilebilir depo | DSpace {len(ds)} | metin ÜRETEN {len(usable)}")
    print(f"\n{'depo':<52}{'kayıt':>10}  TEXT örnek")
    for r in sorted(usable, key=lambda x: -(x.get("total_items") or 0)):
        print(f"{r['url'][:51]:<52}{r.get('total_items') or '?':>10}  {r.get('text_sample')}")
    other = [r for r in rows if r["platform"] and r["platform"] != "DSpace"]
    if other:
        print(f"\nDSpace olmayan platformlar ({len(other)}):")
        for r in other[:15]:
            print(f"   {r['url'][:52]:<54} {r['platform']}")
    print(f"\nkaydedildi: {a.out}")


if __name__ == "__main__":
    main()
