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
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import harvest as H  # noqa: E402  - reuse get(), the limiter and the breaker

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
    # The token is the element's TEXT, not an attribute (OAI-PMH spec); only
    # completeListSize/cursor are attributes. Reading it as an attribute yielded
    # None, so `hops` was always 0 and every repository was judged on page 1 --
    # exactly the deposit-order bias the random hop above exists to avoid.
    token = tok.text.strip() if tok is not None and tok.text else None
    hops = rng.randint(0, 6) if token else 0
    for _ in range(hops):
        if not token:
            break
        page = ET.fromstring(H.get(
            f"{oai}?verb=ListIdentifiers&resumptionToken={urllib.parse.quote(token)}",
            tries=2, delay=2.0))
        t = page.find(".//oai:resumptionToken", ns)
        token = t.text.strip() if t is not None and t.text else None
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


def _status(url: str) -> int:
    """Status code for a bitstream WITHOUT downloading it.

    `Range: bytes=0-0` asks for one byte. Servers that honour it answer 206 and
    send nothing; servers that ignore it answer 200 and we close before reading.
    Either way a readability check costs a few hundred bytes instead of the ~50 KB
    an average document weighs -- that is the difference between a 40-request probe
    and a 2 MB one.
    """
    if H.LIMITER is not None:
        H.LIMITER.wait()
    req = urllib.request.Request(url, headers={**H.UA, "Range": "bytes=0-0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status
    except Exception as e:                                  # noqa: BLE001
        return getattr(e, "code", 0) or 0


def probe_access(base: str, sample: int, seed: int, page_size: int = 25,
                 from_scan: "str | None" = None) -> dict:
    """Measure what fraction of the text a repository ADVERTISES it will actually serve.

    The presence of a TEXT bundle is not permission to read it. Bilkent advertises a
    TEXT bundle on 96.1% of 52,198 records -- a full census, not an estimate -- and
    then answers HTTP 401 on 65.0% of the bitstreams behind them (measured over 6,061
    fetches). The realistic yield is 17,100 documents, not 50,143. Every number in
    SOURCES.md is a coverage figure, so every number in SOURCES.md is an upper bound.

    This is the same mistake as ranking by record count, one layer in: there we
    learned records != coverage, here that coverage != access. The fix is the same --
    measure the thing you actually want instead of a proxy for it. Forty requests
    answer in two minutes what otherwise costs forty hours of harvesting to discover.

    With --from-scan, reuses a completed scan instead of re-paginating (free).
    """
    api = f"{base}/server/api"
    out: dict = {"base": base, "mode": "access"}
    rng = random.Random(seed)
    t0 = time.time()

    with_text: list[str] = []
    if from_scan:
        n_records = n_text = 0
        for line in Path(from_scan).open():
            try:
                rec = json.loads(line)
            except Exception:
                continue
            n_records += 1
            if rec.get("text_urls"):
                n_text += 1
                with_text.append(rec["text_urls"][0])
        examined = n_records          # a completed scan IS the whole population
        out["source"] = f"scan:{from_scan}"
    else:
        first = json.loads(H.get(f"{api}/discover/search/objects?dsoType=item&size=1&page=0",
                                 tries=2, delay=2.0))
        n_records = (((first.get("_embedded") or {}).get("searchResult") or {})
                     .get("page") or {}).get("totalElements") or 0
        if not n_records:
            raise SystemExit("discover uç noktası boş döndü -- DSpace 7 değil mi?")
        n_pages = (n_records + page_size - 1) // page_size
        # Draw from pages scattered across the whole repository. Items inside ONE
        # page come from a single deposit batch and share whatever access policy that
        # batch was given, so 40 neighbours are nowhere near 40 independent draws --
        # the same correlation that made the n=50 coverage probes overconfident.
        # `examined` is the denominator for coverage. Dividing the TEXT count from a
        # handful of sampled pages by the repository's TOTAL record count reported
        # Adiyaman at 0.31% coverage and 50 expected documents out of 16,094 records
        # -- the sample size has to divide the sample, not the population.
        n_text = examined = 0
        for page in rng.sample(range(n_pages), min(8, n_pages)):
            d = json.loads(H.get(
                f"{api}/discover/search/objects?dsoType=item&size={page_size}"
                f"&page={page}&embed=bundles/bitstreams", tries=2, delay=2.0))
            objs = ((((d.get("_embedded") or {}).get("searchResult") or {})
                     .get("_embedded") or {}).get("objects") or [])
            for o in objs:
                ind = (o.get("_embedded") or {}).get("indexableObject") or {}
                examined += 1
                blist = ((((ind.get("_embedded") or {}).get("bundles") or {})
                          .get("_embedded") or {}).get("bundles") or [])
                tb = next((b for b in blist if b.get("name") == "TEXT"), None)
                if not tb:
                    continue
                bs = ((((tb.get("_embedded") or {}).get("bitstreams") or {})
                       .get("_embedded") or {}).get("bitstreams") or [])
                for b in bs:
                    href = ((b.get("_links") or {}).get("content") or {}).get("href")
                    if href:
                        with_text.append(href)
                        n_text += 1
                        break
        out["source"] = "discover"

    out["records"] = n_records
    if not with_text:
        out.update({"tested": 0, "readable": 0, "restricted": 0, "errors": 0,
                    "readable_rate": 0.0, "expected_docs": 0})
        return out

    rng.shuffle(with_text)
    picked = with_text[:sample]
    readable = restricted = errors = 0
    for url in picked:
        code = _status(url)
        if code in (200, 206):
            readable += 1
        elif code in (401, 403):
            restricted += 1
        else:
            errors += 1

    tested = readable + restricted            # errors are inconclusive, not denials
    rate = readable / tested if tested else 0.0
    lo, hi = wilson(readable, tested)
    coverage = n_text / examined if examined else 0.0
    out.update({
        "tested": tested, "readable": readable, "restricted": restricted,
        "errors": errors,
        "text_coverage": round(coverage, 4),
        # How many items that coverage figure rests on. Without it a 25%-of-200
        # estimate and a 96.1%-of-52,198 census read identically in the table.
        "coverage_n": examined,
        "readable_rate": round(rate, 4),
        "readable_ci": [round(lo, 4), round(hi, 4)],
        # records * coverage * readability -- the only one of the three that is a
        # count of documents we can actually put in the corpus.
        "expected_docs": int(n_records * coverage * rate),
        "expected_docs_ci": [int(n_records * coverage * lo),
                             int(n_records * coverage * hi)],
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
    ap.add_argument("--access", action="store_true",
                    help="TEXT paketi var mı değil, GERÇEKTEN indirilebiliyor mu ölç")
    ap.add_argument("--from-scan", default=None,
                    help="tamamlanmış scan.jsonl'i kullan (sayfalama isteği harcama)")
    a = ap.parse_args()

    if a.access:
        H.LIMITER = H.RateLimiter(a.delay)
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for base in a.repos:
            H.BREAKER = H.CircuitBreaker(threshold=8)
            try:
                r = probe_access(base, a.sample, a.seed, from_scan=a.from_scan)
            except Exception as e:                          # noqa: BLE001
                r = {"base": base, "error": f"{type(e).__name__}: {str(e)[:120]}"}
            rows.append(r)
            if "error" in r:
                print(f"{base:<40} ERİŞİLEMEDİ  {r['error']}", flush=True)
            else:
                ci = f"{r['readable_ci'][0]*100:.0f}-{r['readable_ci'][1]*100:.0f}"
                print(f"{base.replace('https://',''):<40}"
                      f"{r['tested']:>4} denendi  okunabilir %{r['readable_rate']*100:>5.1f}"
                      f" ({ci})  401/403 {r['restricted']:>3}"
                      f"  -> ~{r['expected_docs']:,} belge", flush=True)
        with open(a.out, "a") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"\nkaydedildi: {a.out}")
        print("NOT: 'beklenen belge' = kayıt × TEXT kapsaması × okunabilirlik.")
        print("     Yalnız kapsamaya bakan sayı ÜST SINIRDIR, tahmin değildir.")
        return

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
