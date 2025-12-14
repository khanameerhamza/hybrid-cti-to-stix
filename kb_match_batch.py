#!/usr/bin/env python3
import os, glob, json
from kb_match import load_kb, match_text, dedup_and_filter

def _canon_nat(s): 
    import re
    return re.sub(r"\s+", " ", s.strip().lower())

def main():
    kb = load_kb()
    os.makedirs("results/kb", exist_ok=True)
    for fp in sorted(glob.glob("Data/*.txt")):
        name = os.path.basename(fp)
        text = open(fp, encoding="utf-8", errors="ignore").read()
        matches = dedup_and_filter(match_text(text, kb), text)
        nats = sorted({_canon_nat(m["text"]) for m in matches if m["type"].lower() == "nationality"})
        out = {
            "file": name,
            "kb_matches": {
                "matches": matches,
                "nationalities": nats
            }
        }
        with open(os.path.join("results", "kb", f"{name}.json"), "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
        print("✓", name, "-> results/kb/")
    print("Done.")

if __name__ == "__main__":
    main()
