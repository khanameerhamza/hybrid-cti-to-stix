# merge_entities_and_ttp.py
import os, re, glob, json
from urllib.parse import urlparse
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
IOC_DIR   = os.path.join(ROOT, "results", "ioc")
KB_DIR    = os.path.join(ROOT, "results", "kb")
NOVEL_DIR = os.path.join(ROOT, "results", "novel")
TTP_DIR   = os.path.join(ROOT, "results", "attack_ttp")
OUT_DIR   = os.path.join(ROOT, "results", "merged")
os.makedirs(OUT_DIR, exist_ok=True)

_CVE_RE = re.compile(r"^CVE-\d{4}-\d{4,}$", re.IGNORECASE)

def norm_base_from_any_json(path: str) -> str:
    """
    Turn any of:
      'Name.txt.txt.json'  -> 'Name.txt'
      'Name.txt.ttps.json' -> 'Name.txt'
      'Name.txt.json'      -> 'Name.txt'
      'Name.json'          -> 'Name' (rare)
    """
    base = os.path.basename(path)
    if base.endswith(".txt.txt.json"):
        return base[:-len(".txt.txt.json")] + ".txt"
    if base.endswith(".txt.ttps.json"):
        return base[:-len(".txt.ttps.json")] + ".txt"
    if base.endswith(".txt.json"):
        return base[:-len(".txt.json")] + ".txt"
    if base.endswith(".json"):
        return base[:-5]
    return base

def load_json_safe(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def to_main_tech(code_or_name: str) -> str:
    """
    If 'T1047.001' -> 'T1047'. If 'T1047' -> 'T1047'. Otherwise try to extract T#### pattern.
    """
    if not code_or_name:
        return ""
    s = str(code_or_name).strip()
    m = re.search(r"(T\d{4})(?:\.\d{3})?", s, flags=re.I)
    return (m.group(1).upper() if m else "").strip()

def uniq_keep_order(seq):
    seen = set(); out = []
    for x in seq:
        if x not in seen:
            out.append(x); seen.add(x)
    return out

def merge_one(basename: str, files):
    """
    files: dict with keys 'ioc','kb','novel','ttp' -> full path or None
    """
    entities = {
        "intrusion_sets": [], "malware": [], "tools": [], "campaigns": [],
        "locations": [], "persons": [], "orgs": [], "nationalities": [],
        "urls": [], "domains": [], "ips": [], "hashes": [], "emails": [],
        "file_paths": [], "cves": []
    }
    attack = {"tactics": [], "techniques": []}
    prov = {"ioc_file": None, "kb_file": None, "novel_file": None, "ttp_file": None}

    # --- IOC ---
    if files.get("ioc"):
        data = load_json_safe(files["ioc"])
        prov["ioc_file"] = files["ioc"]
        if isinstance(data, dict):
            iocs = data.get("iocs", {}) or {}
            # URLs -> domains
            for u in iocs.get("urls", []) or []:
                if isinstance(u, str) and u.strip():
                    u = u.strip()
                    entities["urls"].append(u)
                    try:
                        host = urlparse(u).netloc
                        if host:
                            entities["domains"].append(host.lower())
                    except Exception:
                        pass
            # Domains
            for d in iocs.get("domains", []) or []:
                if isinstance(d, str) and d.strip():
                    entities["domains"].append(d.strip().lower())
            # Emails
            emails = set(iocs.get("email_addresses", []) or []) | set(iocs.get("email_addresses_complete", []) or [])
            for e in emails:
                if isinstance(e, str) and e.strip():
                    entities["emails"].append(e.strip().lower())
            # IPv4s + CIDR heads
            for ip in iocs.get("ipv4s", []) or []:
                if isinstance(ip, str) and ip.strip():
                    entities["ips"].append(ip.strip())
            for cidr in iocs.get("ipv4_cidrs", []) or []:
                if isinstance(cidr, str) and "/" in cidr:
                    entities["ips"].append(cidr.split("/", 1)[0].strip())
            # Hashes
            for k in ("sha256s","sha1s","md5s","sha512s","ssdeeps","imphashes","authentihashes"):
                for h in iocs.get(k, []) or []:
                    if isinstance(h, str) and h.strip():
                        entities["hashes"].append(h.strip())
            # File paths
            for p in iocs.get("file_paths", []) or []:
                if isinstance(p, str) and p.strip():
                    entities["file_paths"].append(p.strip())
            # CVEs
            for c in iocs.get("cves", []) or []:
                if isinstance(c, str):
                    cve = c.strip().upper()
                    if _CVE_RE.match(cve):
                        entities["cves"].append(cve)

    # --- KB ---
    if files.get("kb"):
        data = load_json_safe(files["kb"])
        prov["kb_file"] = files["kb"]
        if isinstance(data, dict):
            km = data.get("kb_matches")
            if isinstance(km, dict):
                # explicit nationalities
                for n in km.get("nationalities", []) or []:
                    if isinstance(n, str) and n.strip():
                        entities["nationalities"].append(n.strip().lower())
                # matches list
                for m in km.get("matches", []) or []:
                    if not isinstance(m, dict): 
                        continue
                    t = (m.get("type") or "").lower()
                    txt = (m.get("canonical") or m.get("text") or "").strip()
                    if not txt and t not in {"attack-pattern","technique","attack_technique","vulnerability","cve"}:
                        continue

                    if t == "intrusion-set":
                        entities["intrusion_sets"].append(txt)
                    elif t == "malware":
                        entities["malware"].append(txt)
                    elif t == "tool":
                        entities["tools"].append(txt)
                    elif t == "campaign":
                        entities["campaigns"].append(txt)
                    elif t == "location":
                        entities["locations"].append(txt)
                    elif t == "person":
                        entities["persons"].append(txt)
                    elif t in {"organization","org"}:
                        entities["orgs"].append(txt)
                    elif t in {"attack-pattern","technique","attack_technique"}:
                        code = to_main_tech(m.get("external_id") or txt)
                        if code:
                            attack["techniques"].append({"code": code, "name": txt, "score": None})
                    elif t in {"vulnerability","cve"}:
                        cve = (m.get("external_id") or txt).strip().upper()
                        if _CVE_RE.match(cve):
                            entities["cves"].append(cve)

    # --- NOVEL ---
    if files.get("novel"):
        data = load_json_safe(files["novel"])
        prov["novel_file"] = files["novel"]
        if isinstance(data, dict):
            for m in data.get("novel", []) or []:
                if not isinstance(m, dict): 
                    continue
                t = (m.get("type") or "").lower()
                txt = (m.get("canonical") or m.get("text") or "").strip()
                if not txt: 
                    continue
                if t in {"intrusion-set","intrusionset"}:
                    entities["intrusion_sets"].append(txt)
                elif t == "malware":
                    entities["malware"].append(txt)
                elif t == "tool":
                    entities["tools"].append(txt)
                elif t == "campaign":
                    entities["campaigns"].append(txt)
                elif t == "location":
                    entities["locations"].append(txt)
                elif t == "person":
                    entities["persons"].append(txt)
                elif t in {"org","organization"}:
                    entities["orgs"].append(txt)

    # --- TTP (rcATT) ---
    if files.get("ttp"):
        data = load_json_safe(files["ttp"])
        prov["ttp_file"] = files["ttp"]
        if isinstance(data, dict):
            # accept either detail list or iocs->attack_techniques
            details = data.get("ttp_details", {}) or {}
            for t in details.get("techniques", []) or []:
                code = to_main_tech(t.get("code") or "")
                name = t.get("name") or ""
                score = t.get("score")
                if code:
                    attack["techniques"].append({"code": code, "name": name, "score": score})

            iocs = data.get("iocs", {}) or {}
            ent = iocs.get("attack_techniques", {}).get("enterprise", []) or []
            for code in ent:
                code = to_main_tech(code)
                if code:
                    attack["techniques"].append({"code": code, "name": "", "score": None})

    # de-dupe + normalize some fields
    entities["domains"]       = uniq_keep_order([d.lower() for d in entities["domains"] if d])
    entities["emails"]        = uniq_keep_order([e.lower() for e in entities["emails"] if e])
    entities["ips"]           = uniq_keep_order([ip for ip in entities["ips"] if ip])
    entities["hashes"]        = uniq_keep_order([h for h in entities["hashes"] if h])
    entities["urls"]          = uniq_keep_order([u for u in entities["urls"] if u])
    entities["nationalities"] = uniq_keep_order([n.lower() for n in entities["nationalities"] if n])
    entities["cves"]          = uniq_keep_order([c.upper() for c in entities["cves"] if c])

    # techniques: unique by code; keep the first non-empty name/score seen
    seen_codes = set(); tech_out = []
    for t in attack["techniques"]:
        code = to_main_tech(t.get("code") or "")
        if not code or code in seen_codes:
            continue
        seen_codes.add(code)
        tech_out.append({"code": code, "name": t.get("name") or "", "score": t.get("score")})
    attack["techniques"] = tech_out

    out = {
        "file": basename,
        "entities": entities,
        "attack": attack,
        "provenance": prov,
    }
    return out

def index_sources():
    idx = defaultdict(lambda: {"ioc": None, "kb": None, "novel": None, "ttp": None})

    for path in glob.glob(os.path.join(IOC_DIR, "*.json")):
        idx[norm_base_from_any_json(path)]["ioc"] = path
    for path in glob.glob(os.path.join(KB_DIR, "*.json")):
        idx[norm_base_from_any_json(path)]["kb"] = path
    for path in glob.glob(os.path.join(NOVEL_DIR, "*.json")):
        idx[norm_base_from_any_json(path)]["novel"] = path
    for path in glob.glob(os.path.join(TTP_DIR, "*.json")):
        idx[norm_base_from_any_json(path)]["ttp"] = path

    return idx

def main():
    idx = index_sources()
    keys = sorted(idx.keys())
    print(f"[merge] Found {len(keys)} report keys.")

    for i, base in enumerate(keys, 1):
        merged = merge_one(base, idx[base])
        out_name = base + ".json" if not base.endswith(".txt") else base + ".json"
        out_path = os.path.join(OUT_DIR, os.path.basename(out_name))
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        print(f"[{i}/{len(keys)}] wrote {out_path}")

if __name__ == "__main__":
    main()
