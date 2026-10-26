#!/usr/bin/env python3
"""Freeze a small, explicitly licensed World Bank API snapshot (stdlib only)."""
import argparse
import concurrent.futures
import datetime
import hashlib
import json
import pathlib
import time
import urllib.error
import urllib.request

SERIES = ["SP.POP.TOTL", "NY.GDP.MKTP.CD", "NY.GDP.PCAP.CD",
          "NY.GDP.MKTP.KD.ZG", "SP.DYN.LE00.IN", "EG.ELC.ACCS.ZS",
          "FP.CPI.TOTL.ZG", "SP.URB.TOTL.IN.ZS"]
ECONOMIES = dict(zip(
    "DZA BHR COM DJI EGY IRQ JOR KWT LBN LBY MRT MAR OMN PSE QAT SAU SOM SDN SYR TUN ARE YEM".split(),
    "DZ BH KM DJ EG IQ JO KW LB LY MR MA OM PS QA SA SO SD SY TN AE YE".split()))
TERMS = {
    "world-bank-public-licenses": "https://datacatalog.worldbank.org/public-licenses",
    "world-bank-summary-terms": "https://data.worldbank.org/summary-terms-of-use",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fetch_one(root, name, url, refresh=False):
    target = root / name
    receipt = root / (name + ".receipt.json")
    if target.exists() and receipt.exists() and not refresh:
        old = json.loads(receipt.read_text())
        if old.get("status") == 200 and digest(target.read_bytes()) == old.get("sha256"):
            return old
    attempts = []
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Bayanat-Public-Data-Reasoning/0.1 (bounded research snapshot)"})
            with urllib.request.urlopen(req, timeout=60) as response:
                data = response.read(8_000_001)
                if len(data) > 8_000_000:
                    raise ValueError("Bounded response exceeds 8 MB; receipt preserved")
                result = {"url": url, "resolved_url": response.url, "status": response.status,
                          "retrieved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                          "content_type": response.headers.get("Content-Type"),
                          "bytes": len(data), "sha256": digest(data), "file": name,
                          "attempts": attempts}
            target.write_bytes(data)
            receipt.write_text(json.dumps(result, indent=2) + "\n")
            return result
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            status = getattr(error, "code", None)
            attempts.append({"attempt": attempt + 1, "status": status, "error": str(error)})
            failure = {"url": url, "status": status, "attempts": attempts, "file": name}
            receipt.write_text(json.dumps(failure, indent=2) + "\n")
            if status not in (None, 408, 429, 500, 502, 503, 504) or attempt == 3:
                raise
            retry_after = getattr(error, "headers", {}).get("Retry-After") if getattr(error, "headers", None) else None
            try:
                delay = min(60, max(1, int(retry_after)))
            except (TypeError, ValueError):
                delay = 2 ** attempt * 2
            time.sleep(delay)
    raise RuntimeError(url)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[1])
    parser.add_argument("--refresh", action="store_true", help="Explicitly create a new live snapshot")
    args = parser.parse_args()
    root = args.project / "raw"
    root.mkdir(parents=True, exist_ok=True)
    calls = []
    cohort = ";".join(ECONOMIES.values())
    for series in SERIES:
        calls.extend([
            (f"{series}.metadata.json", f"https://api.worldbank.org/v2/sources/2/series/{series}/metadata?format=json"),
            (f"{series}.ar.json", f"https://api.worldbank.org/v2/ar/indicator/{series}?format=json&source=2"),
            (f"{series}.en.json", f"https://api.worldbank.org/v2/indicator/{series}?format=json&source=2"),
            (f"{series}.observations.json", f"https://api.worldbank.org/v2/ar/country/{cohort}/indicator/{series}?format=json&source=2&date=2000:2024&per_page=1000&page=1"),
        ])
    calls.extend((name + ".html", url) for name, url in TERMS.items())
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda call: fetch_one(root, *call, args.refresh), calls))
    manifest = {"version": "0.1.0", "source_id": "2", "period": "2000:2024", "economies": ECONOMIES,
                "series": SERIES, "files": sorted(results, key=lambda item: item["file"])}
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"files": len(results), "raw_bytes": sum(x["bytes"] for x in results),
                      "manifest_sha256": digest((root / "manifest.json").read_bytes())}))


if __name__ == "__main__":
    main()
