import json, glob, os, re

SRC_DIR = "results/ioc"
DST_DIR = "results/ioc_filtered"
os.makedirs(DST_DIR, exist_ok=True)

# Keep CVEs only if they appear near these words (tunable)
CVE_VERBS = r"(?:use[sd]?|exploit(?:ed|s|ing)?|leverag(?:e|ed|es|ing)|target(?:ed|s|ing)?|weaponiz(?:e|ed|es|ing)|abuse[sd]?|deliver(?:ed|s|ing)|drop(?:ped|s|ping))"
# within N tokens of the CVE
WINDOW_TOKENS = 10

# Domain sanity + context filters
TLD_ALLOW = set("com org net edu gov mil info io co uk de fr it ru cn jp in br au ca nl es se no fi ch".split())
DOMAIN_VERBS = r"(?:register(?:ed|s|ing)?|host(?:ed|s|ing)?|c2|command\s*and\s*control|beacon(?:ed|s|ing)?|resolv(?:e|ed|es|ing))"

def is_clean_domain(d):
    d = d.lower().strip(".")
    parts = d.split(".")
    if len(parts) < 2: return False
    tld = parts[-1]
    if tld not in TLD_ALLOW and not (len(tld) == 2 and tld.isalpha()):
        return False
    for p in parts:
        if not p or p[0] == "-" or p[-1] == "-": return False
        if not re.fullmatch(r"[a-z0-9-]{1,63}", p): return False
    # drop common tech/libraries misfired as domains
    if d in {"asp.net"}: return False
    return True

def norm_cve(c):
    c = c.upper().strip()
    m = re.match(r"CVE-(\d{4})-(\d{4,7})", c)
    return f"CVE-{m.group(1)}-{m.group(2)}" if m else c

def keep_cve_in_context(text, cve):
    # crude token window: keep if verb appears within N tokens from CVE
    # tokenize lightly
    toks = re.findall(r"\w+|\S", text)
    cve_upper = cve.upper()
    indices = [i for i,t in enumerate(toks) if cve_upper in t.upper()]
    if not indices:  # fallback exact regex search
        for m in re.finditer(re.escape(cve_upper), text.upper()):
            indices.append(len(text[:m.start()].split()))
    verb_rx = re.compile(CVE_VERBS, re.I)
    for idx in indices:
        a = max(0, idx - WINDOW_TOKENS)
        b = min(len(toks), idx + WINDOW_TOKENS + 1)
        window = " ".join(toks[a:b])
        if verb_rx.search(window):
            return True
    return False

def keep_domain_in_context(text, dom):
    if not is_clean_domain(dom):
        return False
    # retain if domain appears near C2/registration/hosting keywords
    toks = re.findall(r"\w+|\S", text)
    indices = [i for i,t in enumerate(toks) if dom.lower() in t.lower()]
    verb_rx = re.compile(DOMAIN_VERBS, re.I)
    for idx in indices:
        a = max(0, idx - 10)
        b = min(len(toks), idx + 10 + 1)
        window = " ".join(toks[a:b])
        if verb_rx.search(window):
            return True
    return False

# Load raw texts once for context
DATA_TEXT = {}
for fp in glob.glob("Dataset/Data/*.txt"):
    DATA_TEXT[os.path.basename(fp)] = open(fp, encoding="utf-8", errors="ignore").read()

for fp in glob.glob(os.path.join(SRC_DIR, "*.json")):
    data = json.load(open(fp))
    name = data.get("file") or os.path.basename(fp).replace(".json","")
    txt = DATA_TEXT.get(name, "")
    lst = data.get("iocs", {})
    # CVEs
    cv_raw = [norm_cve(x) for x in lst.get("cves", [])]
    cv_keep = sorted({c for c in cv_raw if keep_cve_in_context(txt, c)})
    # Domains
    dom_raw = [d.lower() for d in lst.get("domains", [])]
    dom_keep = sorted({d for d in dom_raw if keep_domain_in_context(txt, d)})

    out = {"file": name, "iocs": dict(lst, cves=cv_keep, domains=dom_keep)}
    dst = os.path.join(DST_DIR, os.path.basename(fp))
    json.dump(out, open(dst, "w"), indent=2)
    print("✓", os.path.basename(fp))
