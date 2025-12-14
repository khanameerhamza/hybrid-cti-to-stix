# novel_entities.py
import os, glob, json, re, spacy
from preprocess import load_and_clean_txt

# --- load spaCy once
NLP = spacy.load("en_core_web_sm")

# --- bring in KB aliases so we can filter out known entities
from kb_match import load_kb
KB_ALIASES = {x["alias_l"] for x in load_kb()}  # lowercased alias set

# Patterns that often introduce novel names
PATTERNS = [
    # (Regex, Name Group Index) - Use -1 for last group
    # “dubbed X”, “named X”, “called X”
    (re.compile(r"\b(dubbed|named|called)\s+([A-Z][A-Za-z0-9\- ]{2,})"), -1),
    # “we track this group as X / tracked as X”
    (re.compile(r"\b(track(?:ed)?\s+(?:as|under)\s+)([A-Z][A-Za-z0-9\- ]{2,})"), -1),
    # “the threat actor X”, “group X”, “campaign X”
    (re.compile(r"\b(threat actor|group|campaign)\s+([A-Z][A-Za-z0-9\- ]{2,})"), -1),
    # “new/novel malware|tool|family X”
    (re.compile(r"\b(new|novel)\s+(malware|tool|family)\s+([A-Z][A-Za-z0-9\- ]{2,})"), -1),
    # "X is a ... group" (Name is Group 1)
    (re.compile(r"\b([A-Z][A-Za-z0-9\-]{2,})\s+is\s+(?:a\s+)?(?:suspected\s+)?(?:[A-Za-z]+\s+)?(group|threat actor|campaign|malware|family)"), 1),
]

def extract(text: str):
    doc = NLP(text)
    hits = []
    for pat, name_idx in PATTERNS:
        for m in pat.finditer(text):
            # pick the specified group as the proposed name
            if name_idx == -1:
                idx = m.lastindex
            else:
                idx = name_idx
            
            cand = m.group(idx)
            if not cand:
                continue
            cand = cand.strip()
            # --- NEW: trim/length guard
            if not (3 <= len(cand) <= 60):
                continue

            st = m.start(m.lastindex)
            en = m.end(m.lastindex)

            # simple type guess from the whole matched phrase
            low = m.group(0).lower()
            if ("malware" in low) or ("family" in low):
                etype = "malware"
            elif ("group" in low) or ("actor" in low) or ("campaign" in low):
                etype = "intrusion-set"
            else:
                etype = "malware"

            # require mostly proper nouns in the span (reduces junk)
            span = doc.char_span(st, en, alignment_mode="contract")
            if span and sum(1 for t in span if t.pos_ == "PROPN") >= max(1, len(span)//2):
                hits.append({
                    "text": cand,
                    "start": st,
                    "end": en,
                    "type": etype,
                    "source_rule": pat.pattern
                })

    # dedup by exact span
    uniq, out = set(), []
    for h in hits:
        k = (h["start"], h["end"])
        if k not in uniq:
            uniq.add(k)
            out.append(h)
    return out

def batch():
    os.makedirs("results/novel", exist_ok=True)
    for fp in sorted(glob.glob("Data/*.txt")):
        name = os.path.basename(fp)
        text = load_and_clean_txt(fp)

        # raw candidates from patterns
        res = extract(text)

        # --- NEW: filter out anything already in the KB; dedup by (text_lc, span)
        clean = []
        seen = set()
        for h in res:
            t_lc = h["text"].lower()
            if t_lc in KB_ALIASES:
                continue  # already known in KB → not novel
            key = (t_lc, h["start"], h["end"])
            if key in seen:
                continue
            seen.add(key)
            clean.append(h)

        out_path = os.path.join("results/novel", f"{name}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"file": name, "novel": clean}, f, indent=2)
        print(f"✓ {name} -> results/novel/  (novel={len(clean)})")
    print("Done.")

if __name__ == "__main__":
    batch()
