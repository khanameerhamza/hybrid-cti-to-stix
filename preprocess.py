# preprocess.py
import re

def clean_text(text: str) -> str:
    # Normalize whitespace & hyphenation; keep punctuation for IOCs
    t = text.replace("\r", "\n")
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    # Unwrap hyphenated line breaks: e.g., "mal-\nware" -> "malware"
    t = re.sub(r"(\w)-\n(\w)", r"\1\2", t)
    # Collapse spaces
    t = re.sub(r"[ \t]+", " ", t)
    return t.strip()

def load_and_clean_txt(path: str) -> str:
    text = open(path, encoding="utf-8", errors="ignore").read()
    try:
        from ioc_fanger import ioc_fanger as fanger  # re-fang defanged IOCs
        text = fanger.fang(text)
    except Exception:
        pass
    return clean_text(text)
