#!/usr/bin/env python3
"""Mevcut meta.jsonl dosyalarındaki bozuk handle'ları yerinde onarır.

Eski çıkarım dc.identifier içinde "hdl.handle.net" alt dizgisini arayıp bölüyordu.
Kaynakça bloğu yapıştırılmış kayıtlarda bu, handle yerine bibliyografya metni
üretti; bazılarında ise BAŞKA kurumun geçerli görünen handle'ını üretti (daha
kötüsü: sessizce yanlış belge indirilir). harvest.handle_from() artık yalnızca
tamamı handle URL'i olan identifier'ı kabul ediyor, olmazsa OAI kimliğinin
son parçasına düşüyor.

Kullanım:  python3 repair_handles.py [--apply]
Varsayılan kuru çalışma; --apply ile .bak yedeği alıp yazar.
"""
import glob
import json
import re
import shutil
import sys

from harvest import handle_from

VALID = re.compile(r"^[0-9][0-9.]*/[^/\s]+$")
apply_changes = "--apply" in sys.argv

for path in sorted(glob.glob("data/repos/*/meta.jsonl")):
    rows, changed = [], []
    for line in open(path):
        try:
            r = json.loads(line)
        except Exception:
            rows.append(line.rstrip("\n"))
            continue
        old = r.get("handle")
        new = handle_from(r.get("identifier", []), r.get("oai_id"))
        if new and new != old:
            r["handle"] = new
            changed.append((old, new))
        elif old is not None and not VALID.match(old) and not new:
            r.pop("handle", None)          # çözülemeyen bozuk handle'ı bırakma
            changed.append((old, None))
        rows.append(json.dumps(r, ensure_ascii=False))

    tag = "UYGULANDI" if apply_changes else "kuru"
    print(f"{path}: {len(changed)} değişiklik [{tag}]")
    for old, new in changed[:12]:
        print(f"   {str(old)[:44]!r} -> {new!r}")
    if apply_changes and changed:
        shutil.copy2(path, path + ".bak")
        with open(path, "w") as f:
            f.write("\n".join(rows) + "\n")
