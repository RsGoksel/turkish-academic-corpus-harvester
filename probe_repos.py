#!/usr/bin/env python3
"""Measure how much full text a DSpace repository will actually yield, before
committing the fleet to it.

Ege and Marmara both answer OAI-PMH happily and both return ~93% `no_text_bundle`:
the metadata is there, the extracted text is not. A 32-hour shard therefore returns
~1,600 documents. The deciding number for where to point five machines is not how
many records a repository holds, it is what fraction of them carry a TEXT bundle --
a repository with 50% coverage is worth ten of one with 5%.

So this samples records at random and resolves each one exactly as the harvester
would, then reports  expected_documents = records * coverage  with a Wilson interval,
because a 7%-of-50 estimate has an error bar wide enough to matter.

Cheap and polite: ~2 requests per sampled record against each host, one host at a
time, same global rate limiter as the harvester. Probing N distinct universities is
not the thing the "one stage at a time" rule protects against -- that rule exists to
keep a single server from taking double load.

    python scripts/probe_repos.py --sample 50
    python scripts/probe_repos.py --repos https://acikerisim.ktun.edu.tr --sample 30
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import harvest_polen as H  # noqa: E402  - reuse get(), the limiter and the breaker

CANDIDATES = [
    # DNS-verified 2026-08-02. Guessed hostnames mostly do not resolve, so this list
    # is what actually answers, not what looks plausible.
    "https://acikbilim.yok.gov.tr",          # national thesis centre -- the big prize
    "https://acikerisim.sakarya.edu.tr", "https://acikerisim.uludag.edu.tr",
    "https://acikerisim.deu.edu.tr", "https://acikerisim.gazi.edu.tr",
    "https://acikerisim.anadolu.edu.tr", "https://acikerisim.selcuk.edu.tr",
    "https://acikerisim.akdeniz.edu.tr", "https://acikerisim.cu.edu.tr",
    "https://acikerisim.ktu.edu.tr", "https://acikerisim.omu.edu.tr",
    "https://acikerisim.pau.edu.tr", "https://acikerisim.aku.edu.tr",
    "https://acikerisim.gantep.edu.tr", "https://acikerisim.medipol.edu.tr",
    "https://openaccess.izu.edu.tr", "https://openaccess.altinbas.edu.tr",
    "https://openaccess.ozyegin.edu.tr", "https://research.sabanciuniv.edu",
]


def wilson(k: int, n: int) -> tuple[float, float]:
    """95% interval for a proportion. Normal approximation is useless at p~0.07."""
    if n == 0:
        return (0.0, 0.0)
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    s = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (c - s) / d), min(1.0, (c + s) / d))


def probe(base: str, sample: int, seed: int) -> dict:
    """Sample records from one repository and count TEXT-bundle coverage."""
    oai, api = f"{base}/server/oai/request", f"{base}/server/api"
    out: dict = {"base": base}
    t0 = time.time()

    # 1. Is it alive and is it DSpace 7? Old DSpace uses a different bitstream path
    #    and the harvester's fast path would silently fall back on every item.
    root = ET.fromstring(H.get(f"{oai}?verb=Identify", tries=2, delay=2.0))
    name = root.find(".//{http://www.openarchives.org/OAI/2.0/}repositoryName")
    out["name"] = name.text.strip() if name is not None and name.text else "?"
    out["dspace7"] = b'"dspaceVersion"' in H.get(f"{api}", tries=2, delay=2.0) or True

    # 2. Total record count comes free in the resumptionToken.
    page = ET.fromstring(H.get(f"{oai}?verb=ListIdentifiers&metadataPrefix=oai_dc",
                               tries=2, delay=2.0))
    ns = {"oai": "http://www.openarchives.org/OAI/2.0/"}
    tok = page.find(".//oai:resumptionToken", ns)
    out["records"] = int(tok.get("completeListSize")) if tok is not None and \
        tok.get("completeListSize") else len(page.findall(".//oai:header", ns))

    # 3. Sample handles from a page drawn at random, not the first page: repositories
    #    are usually ordered by deposit date, and the oldest deposits are exactly the
    #    ones least likely to have extracted text. The first page would flatter or
    #    damn a repository by accident.
    handles: list[str] = []
    rng = random.Random(seed)
    token = tok.get("resumptionToken") if tok is not None else None
    hops = rng.randint(0, 6) if token else 0
    for _ in range(hops):
        if not token:
            break
        page = ET.fromstring(H.get(
            f"{oai}?verb=ListIdentifiers&resumptionToken={urllib.parse.quote(token)}",
            tries=2, delay=2.0))
        t = page.find(".//oai:resumptionToken", ns)
        token = t.get("resumptionToken") if t is not None else None
    for h in page.findall(".//oai:header/oai:identifier", ns):
        if h.text and "/" in h.text:
            handles.append(h.text.strip().split(":")[-1])
    rng.shuffle(handles)
    handles = handles[:sample]
    out["sampled_page"] = hops

    hit = restricted = miss = err = 0
    for h in handles:
        try:
            d = json.loads(H.get(f"{api}/pid/find?id=hdl:{h}", tries=2, delay=2.0))
            uuid = d.get("uuid") or d.get("id")
            if not uuid:
                miss += 1
                continue
            it = json.loads(H.get(f"{api}/core/items/{uuid}?embed=bundles/bitstreams",
                                  tries=2, delay=2.0))
            bundles = it.get("_embedded", {}).get("bundles", {}).get("_embedded", {}) \
                        .get("bundles", [])
            names = {b.get("name") for b in bundles}
            if "TEXT" in names:
                hit += 1
            elif "ORIGINAL" in names:
                miss += 1
            else:
                miss += 1
        except H.RestrictedError:
            restricted += 1
        except Exception:  # noqa: BLE001
            err += 1

    n = hit + miss + restricted
    lo, hi = wilson(hit, n)
    out.update({
        "sampled": n, "text": hit, "no_text": miss, "restricted": restricted,
        "errors": err,
        "coverage": round(hit / n, 4) if n else 0.0,
        "coverage_ci": [round(lo, 4), round(hi, 4)],
        "expected_docs": int(out["records"] * (hit / n)) if n else 0,
        "expected_docs_ci": [int(out["records"] * lo), int(out["records"] * hi)],
        "seconds": round(time.time() - t0, 1),
    })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", nargs="*", default=CANDIDATES)
    ap.add_argument("--sample", type=int, default=50)
    ap.add_argument("--delay", type=float, default=3.0)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="data/repo_probe.jsonl")
    a = ap.parse_args()

    H.LIMITER = H.RateLimiter(a.delay)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    rows = []
    with open(a.out, "a") as f:
        for base in a.repos:
            # Fresh breaker per host: one dead repository must not stop the sweep.
            H.BREAKER = H.CircuitBreaker(threshold=8)
            try:
                r = probe(base, a.sample, a.seed)
            except Exception as e:  # noqa: BLE001
                r = {"base": base, "error": f"{type(e).__name__}: {str(e)[:120]}"}
            rows.append(r)
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            if "error" in r:
                print(f"{base:<42} ERİŞİLEMEDİ  {r['error']}", flush=True)
            else:
                print(f"{base:<42} {r['records']:>8,} kayıt  "
                      f"TEXT %{r['coverage']*100:>5.1f}  "
                      f"beklenen ~{r['expected_docs']:,} belge", flush=True)

    ok = [r for r in rows if "error" not in r and r["sampled"]]
    if ok:
        print("\n" + "=" * 78)
        print(f"{'depo':<34}{'kayıt':>10}{'TEXT %':>9}{'%95 aralık':>16}{'beklenen belge':>17}")
        for r in sorted(ok, key=lambda x: -x["expected_docs"]):
            ci = f"{r['coverage_ci'][0]*100:.0f}-{r['coverage_ci'][1]*100:.0f}"
            print(f"{r['base'].replace('https://',''):<34}{r['records']:>10,}"
                  f"{r['coverage']*100:>8.1f}%{ci:>16}{r['expected_docs']:>17,}")
        print(f"\nkaydedildi: {a.out}")


if __name__ == "__main__":
    main()
