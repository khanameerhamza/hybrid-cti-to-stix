#!/usr/bin/env python3
# kb_build.py — Build Knowledge Base CSVs from MITRE ATT&CK.
# Strategy:
#   1) Try attackcti (TAXII). If rate-limited (429) or offline, fall back to CTI GitHub JSON.
#   2) Cache GitHub JSON locally so subsequent runs are offline.

import argparse, csv, os, sys, json, time
from typing import Iterable, List, Dict, Any

ATTACK_GITHUB_JSON = {
    "enterprise-attack": "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json",
    "mobile-attack":     "https://raw.githubusercontent.com/mitre/cti/master/mobile-attack/mobile-attack.json",
    "ics-attack":        "https://raw.githubusercontent.com/mitre/cti/master/ics-attack/ics-attack.json",
}

def ensure_dir(p: str): os.makedirs(p, exist_ok=True)

def safe(val, default=""):
    if val is None: return default
    if isinstance(val, list): return "; ".join([str(x) for x in val if x is not None])
    return str(val)

def get_external_id(obj: Dict[str, Any]) -> str:
    for ref in obj.get("external_references", []) or []:
        sn = (ref.get("source_name") or "").lower()
        if sn in ("mitre-attack", "mitre-mobile-attack", "mitre-ics-attack"):
            if ref.get("external_id"): return ref["external_id"]
    return ""

def get_aliases(obj: Dict[str, Any]) -> List[str]:
    aliases = []
    for k in ("aliases", "x_mitre_aliases"):
        if isinstance(obj.get(k), list):
            aliases.extend([a for a in obj[k] if isinstance(a, str)])
    seen, out = set(), []
    for a in aliases:
        k = a.strip().lower()
        if k and k not in seen:
            seen.add(k); out.append(a.strip())
    return out

def is_active(obj: Dict[str, Any]) -> bool:
    return not (obj.get("revoked") is True or obj.get("x_mitre_deprecated") is True)

def domain_ok(obj: Dict[str, Any], allowed_domains: Iterable[str]) -> bool:
    doms = obj.get("x_mitre_domains") or []
    if not doms: return True
    return any(d in allowed_domains for d in doms)

def rows_for_aliases(canonical: str, aliases: List[str]) -> List[str]:
    vals = [canonical] + [a for a in aliases if a.lower() != canonical.lower()] if aliases else [canonical]
    seen, out = set(), []
    for v in vals:
        k = v.strip().lower()
        if k and k not in seen:
            seen.add(k); out.append(v.strip())
    return out

def write_intrusion_sets(csv_path: str, groups: List[Dict[str, Any]]):
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["canonical_name","alias","stix_id","external_id","description","created","modified"])
        for g in groups:
            canon = g.get("name","").strip()
            exid  = get_external_id(g)
            for alias in rows_for_aliases(canon, get_aliases(g)):
                w.writerow([canon, alias, g.get("id",""), exid,
                            safe(g.get("description","")), safe(g.get("created","")), safe(g.get("modified",""))])

def write_software(csv_path_mal: str, csv_path_tools: str, sw: List[Dict[str, Any]]):
    def write(path, items):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["canonical_name","alias","stix_id","external_id","platforms","description","created","modified"])
            for s in items:
                canon = s.get("name","").strip()
                exid  = get_external_id(s)
                plats = s.get("x_mitre_platforms",[])
                for alias in rows_for_aliases(canon, get_aliases(s)):
                    w.writerow([canon, alias, s.get("id",""), exid, safe(plats),
                                safe(s.get("description","")), safe(s.get("created","")), safe(s.get("modified",""))])
    write(csv_path_mal,  [s for s in sw if s.get("type") == "malware"])
    write(csv_path_tools,[s for s in sw if s.get("type") == "tool"])

def write_techniques(csv_path: str, techs: List[Dict[str, Any]]):
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["technique_id","name","stix_id","is_subtechnique","tactics","platforms","created","modified","description"])
        for t in techs:
            exid = get_external_id(t)
            tactics = []
            for kcp in t.get("kill_chain_phases", []) or []:
                if (kcp.get("kill_chain_name") or "").startswith("mitre"):
                    tactics.append(kcp.get("phase_name"))
            tactics = list(dict.fromkeys([x for x in tactics if x]))
            w.writerow([exid, safe(t.get("name","")), t.get("id",""),
                        "yes" if t.get("x_mitre_is_subtechnique") else "no",
                        safe(tactics), safe(t.get("x_mitre_platforms",[])),
                        safe(t.get("created","")), safe(t.get("modified","")),
                        safe(t.get("description",""))])

# ----------------- Loaders -----------------

def try_attackcti(allowed_domains):
    try:
        from attackcti import attack_client
        lift = attack_client()
        # simple retries around the heavy calls
        def _retry(callable_, tries=3, wait=5):
            for i in range(tries):
                try:
                    return callable_()
                except Exception as e:
                    if i == tries-1: raise
                    time.sleep(wait)
        groups    = _retry(lambda: lift.get_groups(stix_format=False)) or []
        software  = _retry(lambda: lift.get_software(stix_format=False)) or []
        # techniques sometimes 429 — catch and bubble to fallback
        techniques = lift.get_techniques(stix_format=False) or []
        # filter
        filt = lambda xs: [x for x in xs if is_active(x) and domain_ok(x, allowed_domains)]
        return filt(groups), filt(software), filt(techniques)
    except Exception as e:
        print(f"[attackcti] falling back due to: {e.__class__.__name__}: {e}")
        return None

def load_from_cti_github(allowed_domains, cache_dir=".kb_cache"):
    import requests
    ensure_dir(cache_dir)
    objs: List[Dict[str,Any]] = []
    for dom, url in ATTACK_GITHUB_JSON.items():
        if dom not in allowed_domains: continue
        cache_path = os.path.join(cache_dir, f"{dom}.json")
        if not os.path.exists(cache_path):
            print(f"Downloading {dom} bundle…")
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            open(cache_path, "wb").write(r.content)
        data = json.load(open(cache_path, "r", encoding="utf-8"))
        # bundle has {"type":"bundle","objects":[...]}
        objs.extend(data.get("objects", []))
    # filter active + domain_ok (objects include x_mitre_domains)
    objs = [o for o in objs if is_active(o) and domain_ok(o, allowed_domains)]
    groups    = [o for o in objs if o.get("type") == "intrusion-set"]
    software  = [o for o in objs if o.get("type") in ("malware","tool")]
    techniques= [o for o in objs if o.get("type") == "attack-pattern"]
    return groups, software, techniques

# ----------------- Main -----------------

def main():
    ap = argparse.ArgumentParser(description="Build KB CSVs from MITRE ATT&CK (TAXII or GitHub fallback)")
    ap.add_argument("--out", default=os.path.join("Entity-Extraction","Knowledge-Base"),
                    help="Output directory for CSVs")
    ap.add_argument("--domains", default="enterprise-attack",
                    help="Comma-separated ATT&CK domains: enterprise-attack,mobile-attack,ics-attack")
    ap.add_argument("--offline", action="store_true",
                    help="Force using cached GitHub JSON in .kb_cache (no network)")
    args = ap.parse_args()

    out_dir = args.out
    ensure_dir(out_dir)
    allowed_domains = [d.strip() for d in args.domains.split(",") if d.strip()]

    # 1) Try attackcti unless offline requested
    if not args.offline:
        print("Trying TAXII (attackcti)…")
        res = try_attackcti(allowed_domains)
    else:
        res = None

    # 2) Fallback to GitHub CTI JSON
    if res is None:
        print("Using GitHub CTI JSON (with local cache)…")
        groups, software, techniques = load_from_cti_github(allowed_domains)
    else:
        groups, software, techniques = res

    # Write CSVs
    intrusions_csv = os.path.join(out_dir, "intrusion_sets.csv")
    malware_csv    = os.path.join(out_dir, "malware.csv")
    tools_csv      = os.path.join(out_dir, "tools.csv")
    techniques_csv = os.path.join(out_dir, "techniques.csv")

    print(f"Writing {intrusions_csv}")
    write_intrusion_sets(intrusions_csv, groups)

    print(f"Writing {malware_csv}")
    print(f"Writing {tools_csv}")
    write_software(malware_csv, tools_csv, software)

    print(f"Writing {techniques_csv}")
    write_techniques(techniques_csv, techniques)

    print("\nKB build complete ✅")
    print(f"Files created in: {os.path.abspath(out_dir)}")
    print(" - intrusion_sets.csv")
    print(" - malware.csv")
    print(" - tools.csv")
    print(" - techniques.csv")

if __name__ == "__main__":
    main()
