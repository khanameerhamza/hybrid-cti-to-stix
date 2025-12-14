#!/usr/bin/env python3
import csv, os, re, json, argparse
from typing import Dict, List

KB_DIR = os.path.join("Entity-Extraction", "Knowledge-Base")

_BAD_CANON = {"At","Domains","Malware","DLL","Python","JavaScript","Server","Proxy"}

def is_word_boundary(text, start, end):
    left_ok  = (start == 0) or not re.match(r"\w", text[start-1])
    right_ok = (end   == len(text)) or not re.match(r"\w", text[end])
    return left_ok and right_ok

def _overlap(a, b): return not (a["end"] <= b["start"] or b["end"] <= a["start"])
def _longer(a, b):  return (a["end"] - a["start"]) > (b["end"] - b["start"])
def _canon_nat(s):  return re.sub(r"\s+", " ", s.strip().lower())

def dedup_and_filter(matches, text):
    keep = []
    for m in matches:
        if not is_word_boundary(text, m["start"], m["end"]):
            continue
        token = text[m["start"]:m["end"]].strip(" ,.;:()[]{}\"'`")
        if not token:
            continue
        m = dict(m); m["text"] = token
        if m.get("canonical") in _BAD_CANON:  # drop noisy canonicals
            continue
        if len(token) < 3 and not token.upper().startswith("APT"):  # drop very short non-APT
            continue
        keep.append(m)

    keep.sort(key=lambda x: (x["start"], -(x["end"] - x["start"])))

    result = []
    for m in keep:
        if result and _overlap(result[-1], m):
            if _longer(m, result[-1]):
                result[-1] = m
            elif (m["end"] - m["start"]) == (result[-1]["end"] - result[-1]["start"]):
                if text[m["start"]:m["end"]] == m["text"]:
                    result[-1] = m
            continue
        result.append(m)

    seen = set(); final = []
    for m in result:
        key = (m["start"], m["end"], m["canonical"], m["type"], m.get("external_id"))
        if key in seen: continue
        seen.add(key); final.append(m)
    return final

def _load_alias_map(csv_path: str, kind: str, canon_col="canonical_name", alias_col="alias", id_col="external_id"):
    out = []
    if not os.path.exists(csv_path): return out
    with open(csv_path, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            alias = (row.get(alias_col) or "").strip()
            canon = (row.get(canon_col) or "").strip()
            extid = (row.get(id_col) or "").strip()
            if alias and canon:
                out.append({"alias": alias, "alias_l": alias.lower(), "canon": canon, "kind": kind, "ext_id": extid})
    out.sort(key=lambda x: len(x["alias"]), reverse=True)
    return out

def _load_nationalities(csv_path: str):
    out = []
    if not os.path.exists(csv_path): return out
    with open(csv_path, encoding="utf-8") as f:
        r = csv.DictReader(f, delimiter=",")
        if r.fieldnames and len(r.fieldnames) == 1 and "\t" in r.fieldnames[0]:
            f.seek(0)
            r = csv.DictReader(f, delimiter="\t")
        for row in r:
            dem  = (row.get("Nationality") or "").strip()
            nation = (row.get("Nation") or "").strip()
            if not dem and not nation:
                continue
            canon = dem or nation
            aliases = []
            if dem:    aliases.append(dem)
            if nation: aliases.append(nation)
            for alias in sorted(set(aliases), key=len, reverse=True):
                out.append({
                    "alias": alias,
                    "alias_l": alias.lower(),
                    "canon": canon,
                    "kind": "nationality",
                    "ext_id": ""
                })
    seen, dedup = set(), []
    for x in out:
        k = (x["alias_l"], x["kind"])
        if k not in seen:
            seen.add(k); dedup.append(x)
    return dedup

def load_kb():
    kb = []
    # intrusion sets / malware / tools (alias-per-row)
    kb += _load_alias_map(os.path.join(KB_DIR, "intrusion_sets.csv"), "intrusion-set", id_col="external_id")
    kb += _load_alias_map(os.path.join(KB_DIR, "malware.csv"),        "malware",        id_col="external_id")
    kb += _load_alias_map(os.path.join(KB_DIR, "tools.csv"),          "tool",           id_col="external_id")
    # NEW: campaigns (you renamed campaigns_aliasmap.csv -> campaigns.csv)
    kb += _load_alias_map(os.path.join(KB_DIR, "campaigns.csv"),      "campaign",       id_col="external_id")

    # techniques (name + technique_id)
    tpath = os.path.join(KB_DIR, "techniques.csv")
    if os.path.exists(tpath):
        with open(tpath, encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                name = (row.get("name") or "").strip()
                tid  = (row.get("technique_id") or "").strip()
                if name and tid:
                    kb.append({"alias": name, "alias_l": name.lower(), "canon": name, "kind": "attack-pattern", "ext_id": tid})

    # nationalities
    kb += _load_nationalities(os.path.join(KB_DIR, "nationalities.csv"))

    # compile regexes
    for x in kb:
        pat = r"(?<!\w)(" + re.escape(x["alias"]) + r")(?!\w)"
        pat = pat.replace(r"\ ", r"\s+")
        x["regex"] = re.compile(pat, re.IGNORECASE)
    return kb

def match_text(text: str, kb) -> List[Dict]:
    hits = []
    for entry in kb:
        for m in entry["regex"].finditer(text):
            hits.append({
                "text": m.group(0),
                "start": m.start(),
                "end":   m.end(),
                "type": entry["kind"],
                "canonical": entry["canon"],
                "external_id": entry["ext_id"],
            })
    uniq = {}
    for h in hits:
        k = (h["start"], h["end"], h["type"])
        if k not in uniq: uniq[k] = h
    return list(uniq.values())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="path to a .txt report")
    ap.add_argument("--out", help="JSON output path (default prints)")
    args = ap.parse_args()

    kb = load_kb()
    text = open(args.file, encoding="utf-8", errors="ignore").read()

    matches = dedup_and_filter(match_text(text, kb), text)

    nats = sorted({_canon_nat(m["text"]) for m in matches if m["type"].lower() == "nationality"})

    out = {
        "file": os.path.basename(args.file),
        "kb_matches": {
            "matches": matches,
            "nationalities": nats
        }
    }

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
    else:
        print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
