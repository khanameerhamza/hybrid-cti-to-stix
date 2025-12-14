# kb_filters.py
import re

# hard filters to avoid generic words that sneak in as ATT&CK names
_BAD_CANON = {
    # techniques/tools that collide with common words
    "At", "Domains", "Malware", "DLL", "Python", "JavaScript"
}

def _overlap(a, b):
    return not (a["end"] <= b["start"] or b["end"] <= a["start"])

def _longer(a, b):
    return (a["end"] - a["start"]) > (b["end"] - b["start"])

def dedup_and_filter(matches, text):
    """
    Input: list of dicts with keys: text,start,end,type,canonical,external_id
    Returns: filtered, deduped list.
    """
    # 1) drop blatantly generic or too-short items
    keep = []
    for m in matches:
        # trim surrounding punctuation spaces if any
        token = text[m["start"]:m["end"]]
        token = token.strip(" ,.;:()[]{}\"'`")
        if not token:
            continue

        m = dict(m)
        m["text"] = token
        # generic/ambiguous canonicals to skip
        if m.get("canonical") in _BAD_CANON:
            continue
        # very short non-APT tokens are noisy (e.g., “at”)
        if len(token) < 3 and not token.upper().startswith("APT"):
            continue
        keep.append(m)

    # 2) sort by (start asc, length desc) to prefer longer spans at same spot
    keep.sort(key=lambda x: (x["start"], -(x["end"] - x["start"])))

    # 3) remove overlaps (keep the longest at each region)
    result = []
    for m in keep:
        if result and _overlap(result[-1], m):
            # if current is longer, replace; else skip
            if _longer(m, result[-1]):
                result[-1] = m
            # if same length but one is exact-case match, prefer exact-case
            elif (m["end"] - m["start"]) == (result[-1]["end"] - result[-1]["start"]):
                if text[m["start"]:m["end"]] == m["text"]:
                    result[-1] = m
            continue
        result.append(m)

    # 4) collapse exact duplicates across the doc
    seen = set()
    final = []
    for m in result:
        key = (m["start"], m["end"], m["canonical"], m["type"], m.get("external_id"))
        if key in seen:
            continue
        seen.add(key)
        final.append(m)

    return final
