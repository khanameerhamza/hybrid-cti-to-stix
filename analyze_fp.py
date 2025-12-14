# analyze_fp.py
import json, glob, os

ANN="Dataset/Annotations.json"
IOC="results/ioc_filtered"  # switch to results/ioc to compare

def norm(x): return x.strip().lower()

# Load gold (Label Studio list format) -> {file: {label: set(values)}}
gold={}
for t in json.load(open(ANN,encoding="utf-8")):
    data=t.get("data",{}) or {}
    fname=data.get("file") or data.get("filename") or ""
    if fname and not fname.lower().endswith(".txt"): fname += ".txt"
    ents={}
    for ann in t.get("annotations",[]):
        for r in ann.get("result",[]):
            labs=(r.get("value",{}).get("labels") or [])
            txt = r.get("value",{}).get("text","")
            if not labs or not txt: continue
            lab=labs[0].upper()
            if lab=="VULNERABILITY": lab="CVE"
            if lab in ("CVE","DOMAIN"):
                ents.setdefault(lab,set()).add(norm(txt))
    if fname: gold[fname]=ents

fps={"CVE":[], "DOMAIN":[]}
for fp in glob.glob(os.path.join(IOC,"*.json")):
    name=os.path.basename(fp).replace(".json","")
    data=json.load(open(fp))
    lst=data.get("iocs",{})
    pred_cves = set(map(norm, lst.get("cves",[])))
    pred_domains = set(map(norm, lst.get("domains",[])))
    gold_cves = gold.get(name,{}).get("CVE", set())
    gold_domains = gold.get(name,{}).get("DOMAIN", set())
    for x in sorted(pred_cves - gold_cves):
        fps["CVE"].append((name,x))
    for x in sorted(pred_domains - gold_domains):
        fps["DOMAIN"].append((name,x))

print("FP CVEs (first 30):")
print("\n".join(f"{a}: {b}" for a,b in fps["CVE"][:30]))
print("\nFP Domains (first 30):")
print("\n".join(f"{a}: {b}" for a,b in fps["DOMAIN"][:30]))
