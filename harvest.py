#!/usr/bin/env python3
"""Harvest the ITU Polen open archive (polen.itu.edu.tr) into training-ready JSONL.

The archive exposes OAI-PMH for metadata and a DSpace 7 REST API for content, and
crucially it already ships a TEXT bundle per item: DSpace has pre-extracted the
full text of every PDF. That means the 21 GB of theses can be pulled as text
directly instead of downloading and parsing PDFs -- and Ottoman/rare works avoid an
OCR pass entirely.

Two stages, both resumable:

  1. `meta`  OAI-PMH sweep -> data/itu/polen_meta.jsonl (one line per record,
             68,911 records at ~100/page). Cheap, gives titles/abstracts/subjects.
  2. `text`  For each record: item lookup -> TEXT bundle -> .txt bitstream ->
             cleaned document -> data/itu/polen_text.jsonl

Politeness: single worker per stage by default with a delay between requests; this
is a university server, not a CDN. Raise --workers only if the admin agrees.

    python scripts/harvest_polen.py meta
    python scripts/harvest_polen.py text --workers 4
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

# Every Turkish university running DSpace exposes the same OAI-PMH + REST pair, and
# DSpace pre-extracts PDF text into a TEXT bundle. The technique that worked for ITU
# therefore generalizes to the whole national repository network -- all open access,
# no credentials, no publisher licences involved.
REPOS = {
    "itu":       "https://polen.itu.edu.tr",
    "ege":       "https://acikerisim.ege.edu.tr",
    "marmara":   "https://openaccess.marmara.edu.tr",
    "hacettepe": "https://openaccess.hacettepe.edu.tr",
}
REPO = "itu"
OAI = ""
API = ""
OUT = Path("data/itu")
NS = {"oai": "http://www.openarchives.org/OAI/2.0/",
      "dc": "http://purl.org/dc/elements/1.1/"}
UA = {"User-Agent": "ITU-LLM-corpus-builder/1.0 (academic use; contact via ITU)"}


class RateLimiter:
    """Bounds the TOTAL request rate across every worker thread.

    The first version accepted --delay but never used it in the text stage: a
    ThreadPoolExecutor hammered the server with `workers` continuous streams, and
    each document costs four requests. Across five machines that is twenty
    unthrottled streams -- a reliable way to get an entire university's IP range
    to block us. The limiter serialises request starts so `min_interval` is
    honoured globally, not per thread.
    """

    def __init__(self, min_interval: float):
        import threading
        self.min_interval = min_interval
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            gap = self.min_interval - (now - self._last)
            if gap > 0:
                time.sleep(gap)
            self._last = time.monotonic()


class CircuitBreaker:
    """Stops the run after repeated server errors instead of grinding on."""

    def __init__(self, threshold: int = 12):
        import threading
        self.threshold = threshold
        self._lock = threading.Lock()
        self.consecutive = 0
        self.tripped = False

    def record(self, ok: bool) -> None:
        with self._lock:
            if ok:
                self.consecutive = 0
            else:
                self.consecutive += 1
                if self.consecutive >= self.threshold:
                    self.tripped = True


LIMITER: "RateLimiter | None" = None
BREAKER: "CircuitBreaker | None" = None


def get(url: str, tries: int = 4, delay: float = 2.0) -> bytes:
    last = None
    for i in range(tries):
        if BREAKER is not None and BREAKER.tripped:
            raise RuntimeError("circuit breaker tripped: too many server errors")
        if LIMITER is not None:
            LIMITER.wait()
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=90) as r:
                data = r.read()
            if BREAKER is not None:
                BREAKER.record(True)
            return data
        except Exception as e:  # noqa: BLE001 - university server, transient errors expected
            last = e
            code = getattr(e, "code", None)
            if BREAKER is not None:
                BREAKER.record(code in (429, 500, 502, 503, 504) or code is None)
            # 429/5xx mean "slow down", so back off much harder than on a hiccup.
            backoff = delay * (4 ** i) if code in (429, 500, 502, 503, 504) else delay * (i + 1)
            time.sleep(min(backoff, 120))
    raise last  # type: ignore[misc]


# --------------------------------------------------------------- stage 1: metadata

def harvest_meta(delay: float) -> None:
    global LIMITER, BREAKER
    LIMITER = RateLimiter(delay)
    BREAKER = CircuitBreaker()
    OUT.mkdir(parents=True, exist_ok=True)
    out_path = OUT / "meta.jsonl"
    token_path = OUT / ".meta_token"

    seen = set()
    if out_path.exists():
        for line in out_path.open():
            try:
                seen.add(json.loads(line)["oai_id"])
            except Exception:
                pass
        print(f"resuming: {len(seen)} records already harvested")

    token = token_path.read_text().strip() if token_path.exists() else None
    total = None
    n = 0
    with out_path.open("a") as f:
        while True:
            url = (f"{OAI}?verb=ListRecords&resumptionToken={urllib.parse.quote(token)}"
                   if token else f"{OAI}?verb=ListRecords&metadataPrefix=oai_dc")
            root = ET.fromstring(get(url))
            for rec in root.findall(".//oai:record", NS):
                oid_el = rec.find(".//oai:identifier", NS)
                oid = oid_el.text if oid_el is not None else None
                if not oid or oid in seen:
                    continue
                row = {"oai_id": oid, "source": REPO}
                for field in ("title", "creator", "subject", "description", "date",
                              "type", "identifier", "language", "publisher", "rights"):
                    vals = [e.text.strip() for e in rec.findall(f".//dc:{field}", NS)
                            if e.text and e.text.strip()]
                    if vals:
                        row[field] = vals
                handles = [v for v in row.get("identifier", []) if "hdl.handle.net" in v]
                if handles:
                    row["handle"] = handles[0].split("hdl.handle.net/")[-1]
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                seen.add(oid)
                n += 1

            rt = root.find(".//oai:resumptionToken", NS)
            if total is None and rt is not None and rt.get("completeListSize"):
                total = int(rt.get("completeListSize"))
            print(f"  {len(seen)}/{total or '?'} kayıt", flush=True)
            if rt is None or not (rt.text or "").strip():
                token_path.unlink(missing_ok=True)
                break
            token = rt.text.strip()
            token_path.write_text(token)
            time.sleep(delay)
    print(f"done: {len(seen)} records -> {out_path}")


# --------------------------------------------------------------- stage 2: full text

_WS = re.compile(r"[ \t]{2,}")
_NL = re.compile(r"\n{3,}")


def clean(text: str) -> str:
    """DSpace's extractor leaves the PDF's layout whitespace in place."""
    text = text.replace("\r", "")
    text = _WS.sub(" ", text)
    text = "\n".join(ln.strip() for ln in text.split("\n"))
    return _NL.sub("\n\n", text).strip()


def item_uuid(handle: str) -> str | None:
    """Resolve handle -> item UUID.

    `/pid/find` answers directly instead of going through the search index, which
    is both cheaper for the server and less fragile than a Solr query.
    """
    d = json.loads(get(f"{API}/pid/find?id=hdl:{handle}"))
    return d.get("uuid")


def text_for_item(uuid: str) -> str | None:
    """Fetch the pre-extracted text, using `embed` to collapse two calls into one.

    Politeness caps the request RATE, so the way to finish sooner is to need fewer
    requests per document -- not to raise the rate. `?embed=bundles/bitstreams`
    returns the bundle list with its bitstreams inlined, taking a document from
    four requests (search -> bundles -> bitstreams -> content) down to three
    (pid -> item+embed -> content). Documents with no TEXT bundle -- about 75% at
    ITU -- now cost two requests instead of three.
    """
    d = json.loads(get(f"{API}/core/items/{uuid}?embed=bundles/bitstreams"))
    bundles = d.get("_embedded", {}).get("bundles", {})
    blist = bundles.get("_embedded", {}).get("bundles", []) if isinstance(bundles, dict) else []
    tb = next((b for b in blist if b.get("name") == "TEXT"), None)
    if not tb:
        return None
    bs_holder = tb.get("_embedded", {}).get("bitstreams", {})
    bitstreams = (bs_holder.get("_embedded", {}).get("bitstreams", [])
                  if isinstance(bs_holder, dict) else [])
    if not bitstreams:                      # older DSpace: fall back to the extra call
        d2 = json.loads(get(f"{API}/core/bundles/{tb['uuid']}/bitstreams"))
        bitstreams = d2.get("_embedded", {}).get("bitstreams", [])
    parts = []
    for bs in bitstreams:
        href = bs.get("_links", {}).get("content", {}).get("href")
        if href:
            parts.append(get(href).decode("utf-8", errors="replace"))
    return "\n\n".join(parts) if parts else None


def harvest_text(workers: int, delay: float, min_chars: int,
                 shard: int = 0, num_shards: int = 1) -> None:
    import concurrent.futures as cf

    global LIMITER, BREAKER
    LIMITER = RateLimiter(delay)
    BREAKER = CircuitBreaker()
    print(f"  hız sınırı: global {1/delay:.1f} istek/sn, {workers} işçi")

    meta_path = OUT / "meta.jsonl"
    if not meta_path.exists():
        raise SystemExit("run `meta` stage first")
    suffix = "" if num_shards == 1 else f".shard{shard}"
    out_path = OUT / f"text{suffix}.jsonl"
    fail_path = OUT / f"text{suffix}.failed.jsonl"

    done = set()
    if out_path.exists():
        for line in out_path.open():
            try:
                done.add(json.loads(line)["handle"])
            except Exception:
                pass
    # Only PERMANENT failures count as done. A transient HTTP error or timeout must
    # be retried on the next run; treating those as final silently drops documents
    # that were merely unlucky.
    PERMANENT = {"no_text_bundle", "no_uuid"}
    if fail_path.exists():
        for line in fail_path.open():
            try:
                rec = json.loads(line)
                err = str(rec.get("error", ""))
                if err in PERMANENT or err.startswith("too_short"):
                    done.add(rec["handle"])
            except Exception:
                pass

    import hashlib

    rows = []
    for line in meta_path.open():
        r = json.loads(line)
        h = r.get("handle")
        if not h or h in done:
            continue
        # Shard on a hash of the handle, NOT the line index. Index-based splitting
        # silently breaks when two machines harvest meta separately: the files end
        # up in different orders, so shards overlap and other records are never
        # fetched at all. Hashing the handle is order-independent, so every machine
        # computes the same assignment from any copy of the metadata.
        if num_shards > 1:
            digest = hashlib.blake2b(h.encode(), digest_size=8).digest()
            if int.from_bytes(digest, "big") % num_shards != shard:
                continue
        rows.append(r)
    print(f"shard {shard}/{num_shards}: {len(done)} done, {len(rows)} remaining")

    def work(r):
        h = r["handle"]
        try:
            u = item_uuid(h)
            if not u:
                return h, None, "no_uuid", r
            t = text_for_item(u)
            if not t:
                return h, None, "no_text_bundle", r
            t = clean(t)
            if len(t) < min_chars:
                return h, None, f"too_short_{len(t)}", r
            return h, t, None, r
        except Exception as e:  # noqa: BLE001
            return h, None, f"{type(e).__name__}", r

    ok = bad = 0
    chars = 0
    t0 = time.time()
    with out_path.open("a") as fout, fail_path.open("a") as ffail, \
            cf.ThreadPoolExecutor(workers) as ex:
        for i, (h, text, err, r) in enumerate(ex.map(work, rows), 1):
            if text:
                fout.write(json.dumps({
                    "handle": h, "text": text,
                    "title": (r.get("title") or [None])[0],
                    "type": (r.get("type") or [None])[0],
                    "date": (r.get("date") or [None])[-1],
                    "language": (r.get("language") or [None])[0],
                    "publisher": (r.get("publisher") or [None])[0],
                    "source": REPO,
                }, ensure_ascii=False) + "\n")
                ok += 1
                chars += len(text)
            else:
                ffail.write(json.dumps({"handle": h, "error": err}, ensure_ascii=False) + "\n")
                bad += 1
            if i % 50 == 0:
                fout.flush(); ffail.flush()
                rate = i / max(time.time() - t0, 1)
                eta = (len(rows) - i) / max(rate, 1e-6) / 3600
                print(f"  {i}/{len(rows)} ok={ok} fail={bad} "
                      f"{chars/1e6:.1f}M karakter (~{chars/4/1e6:.1f}M token) "
                      f"{rate:.1f}/s ETA {eta:.1f}h", flush=True)
    if BREAKER is not None and BREAKER.tripped:
        print("!! DEVRE KESİCİ ATTI — sunucu üst üste hata verdi. Saatler sonra "
              "--delay 5 --workers 1 ile tekrar dene.")
    print(f"done: ok={ok} fail={bad} chars={chars/1e6:.1f}M (~{chars/4/1e6:.0f}M token)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["meta", "text"])
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--delay", type=float, default=1.5,
                    help="minimum seconds BETWEEN requests, enforced globally")
    ap.add_argument("--min-chars", type=int, default=2000)
    ap.add_argument("--repo", default="itu", choices=list(REPOS))
    ap.add_argument("--shard", type=int, default=0,
                    help="which slice of the work this machine takes (0-based)")
    ap.add_argument("--num-shards", type=int, default=1,
                    help="how many machines are splitting the work")
    a = ap.parse_args()
    global OAI, API, OUT, REPO
    REPO = a.repo
    base = REPOS[a.repo]
    OAI = f"{base}/server/oai/request"
    API = f"{base}/server/api"
    OUT = Path(f"data/repos/{a.repo}")
    if a.stage == "meta":
        harvest_meta(a.delay)
    else:
        harvest_text(a.workers, a.delay, a.min_chars, a.shard, a.num_shards)


if __name__ == "__main__":
    main()
