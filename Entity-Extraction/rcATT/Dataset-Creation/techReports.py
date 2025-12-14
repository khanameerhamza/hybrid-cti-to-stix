# techReports.py  — robust, resumable URL harvester for rcATT
import os
import re
import json
import time
import argparse
from datetime import datetime
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from attackcti import attack_client

# ------------------------
# Config (tweak as needed)
# ------------------------
ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "URL_Content"                     # where pages get saved
STATE_PATH = ROOT / "progress.json"                # resume state
USER_AGENT = "rcATT-url-fetcher/1.0 (+https://attack.mitre.org)"
CONNECT_TIMEOUT = 6       # seconds for TCP connect
READ_TIMEOUT = 12         # seconds for server response
MAX_BYTES = 1_000_000     # 1MB cap per page (avoid huge dumps)
SLEEP_BETWEEN = 0.25      # politeness delay

# ------------------------
# Utilities
# ------------------------
def now():
    return datetime.now().strftime("%H:%M:%S")

def sanitize_filename(name: str) -> str:
    # Keep technique folder names stable
    name = name.replace("/", "_").replace("\\", "_")
    name = re.sub(r"[^\w\-\.\s\(\)_]", "_", name)
    return name[:128]  # avoid very long filenames

def build_session() -> requests.Session:
    sess = requests.Session()
    retries = Retry(
        total=2,  # a couple of automatic retries on transient issues
        connect=2,
        read=2,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"]
    )
    sess.headers.update({"User-Agent": USER_AGENT})
    sess.mount("http://", HTTPAdapter(max_retries=retries))
    sess.mount("https://", HTTPAdapter(max_retries=retries))
    return sess

def fetch_text(session: requests.Session, url: str) -> str | None:
    try:
        r = session.get(url, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT), allow_redirects=True, verify=True)
        ct = (r.headers.get("content-type") or "").lower()
        # Skip obvious binaries
        if any(bad in ct for bad in ["application/pdf", "application/zip", "image/", "audio/", "video/"]):
            return None
        # Decode text safely, cap size
        text = r.text
        if not text or not text.strip():
            return None
        if len(text) > MAX_BYTES:
            text = text[:MAX_BYTES]
        return text
    except requests.Timeout:
        print("    [⏰ TIMEOUT]")
        return None
    except requests.RequestException as e:
        print(f"    [❌ {e.__class__.__name__}: {e}]")
        return None

def save_page(dir_path: Path, index: int, url: str, content: str):
    dir_path.mkdir(parents=True, exist_ok=True)
    # stable per-URL filename (index + short hash)
    short = abs(hash(url)) % (10**8)
    fname = f"{index:03d}__{short}.txt"
    with open(dir_path / fname, "w", encoding="utf-8", errors="ignore") as f:
        f.write(content)

def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except Exception:
            pass
    return {"last_index": -1}

def save_state(i: int):
    STATE_PATH.write_text(json.dumps({"last_index": i}, indent=2))

def iter_techniques(limit: int | None, start: int) -> list[dict]:
    lift = attack_client()
    techniques = lift.get_enterprise_techniques()
    # Sort for stable ordering
    techniques = sorted(techniques, key=lambda t: t.get("name", "").lower())
    # Slice
    if start:
        techniques = techniques[start:]
    if limit is not None:
        techniques = techniques[:limit]
    return techniques

def technique_urls(tech: dict) -> list[str]:
    urls = []
    for ref in tech.get("external_references", []) or []:
        u = ref.get("url")
        if u and isinstance(u, str) and u.startswith(("http://", "https://")):
            urls.append(u)
    # Dedup while preserving order
    seen = set()
    uniq = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq

# ------------------------
# Main
# ------------------------
def main():
    parser = argparse.ArgumentParser(description="Fetch external URLs for ATT&CK techniques (robust + resumable)")
    parser.add_argument("--limit", type=int, default=None, help="Process only the first N techniques (after --start)")
    parser.add_argument("--start", type=int, default=0, help="Skip the first START techniques")
    parser.add_argument("--resume", action="store_true", help="Resume from progress.json")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    all_techs = iter_techniques(args.limit, args.start)

    # Resume logic
    if args.resume:
        state = load_state()
        last = state.get("last_index", -1)
    else:
        last = -1

    session = build_session()

    total = len(all_techs)
    for i, tech in enumerate(all_techs):
        # resume skip
        if i <= last:
            continue

        name = tech.get("name") or "unknown-technique"
        urls = technique_urls(tech)
        folder = OUT_DIR / sanitize_filename(name)

        print(f"[🔎 TECHNIQUE {i+1}/{total}] {name}")
        if not urls:
            print("    [ℹ️  No external URLs listed]")
            save_state(i)
            continue

        for j, url in enumerate(urls, 1):
            print(f"    [🌐 URL {j}/{len(urls)}] [🕛 {now()}] {url}")
            text = fetch_text(session, url)
            if text:
                save_page(folder, j, url, text)
            else:
                print("    [❌ URL SKIPPED]")
            time.sleep(SLEEP_BETWEEN)

        save_state(i)

    print("✅ Done. Collected pages are under:", OUT_DIR)

if __name__ == "__main__":
    main()
