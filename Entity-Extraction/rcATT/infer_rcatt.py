#!/usr/bin/env python3
import os, json, glob, re
import joblib
import numpy as np
import pandas as pd

# --- scikit plumbing used inside pickled pipelines ---
from sklearn.base import BaseEstimator, TransformerMixin

# --- NLTK deps used by tokenizers inside the models ---
import nltk
from nltk.stem import WordNetLemmatizer, SnowballStemmer
from nltk.tokenize import word_tokenize

# Ensure NLTK data
for pkg in ["punkt", "punkt_tab", "wordnet", "omw-1.4", "stopwords"]:
    try:
        nltk.data.find(pkg if "/" in pkg else f"tokenizers/{pkg}")
    except (LookupError, OSError):
        nltk.download(pkg, quiet=True)

# === Classes with the SAME names used at training time ===
class TextSelector(BaseEstimator, TransformerMixin):
    def __init__(self, key): self.key = key
    def fit(self, X, y=None): return self
    def transform(self, X): return X[self.key].values

class LemmaTokenizer(object):
    def __init__(self):
        try:
            self.wnl = WordNetLemmatizer()
        except Exception:
            self.wnl = None
    def __call__(self, doc):
        if getattr(self, "wnl", None) is None:
            self.wnl = WordNetLemmatizer()
        return [self.wnl.lemmatize(t) for t in word_tokenize(doc)]

class StemTokenizer(object):
    def __init__(self):
        try:
            self.stemmer = SnowballStemmer("english")
        except Exception:
            self.stemmer = None
    def __call__(self, doc):
        if getattr(self, "stemmer", None) is None:
            self.stemmer = SnowballStemmer("english")
        return [self.stemmer.stem(t) for t in word_tokenize(doc)]


# === Static (code->name) maps for pretty output (safe to keep) ===
CODE_TACTICS = ['TA0043','TA0042','TA0001','TA0002','TA0003','TA0004','TA0005','TA0006','TA0007','TA0008','TA0009','TA0011','TA0010','TA0040']
NAME_TACTICS = ['Reconnaissance','Resource Development','Initial Access','Execution','Persistence','Privilege Escalation','Defense Evasion','Credential Access','Discovery','Lateral Movement','Collection','Command and Control','Exfiltration','Impact']

CODE_TECHNIQUES = ['T1595','T1592','T1589','T1590','T1591','T1598','T1597','T1596','T1593','T1594','T1583','T1586','T1584','T1587','T1585','T1588','T1608','T1189','T1190','T1133','T1200','T1566','T1091','T1195','T1199','T1078','T1059','T1609','T1610','T1203','T1559','T1106','T1053','T1129','T1072','T1569','T1204','T1047','T1098','T1197','T1547','T1037','T1176','T1554','T1136','T1543','T1546','T1574','T1525','T1556','T1137','T1542','T1505','T1205','T1548','T1134','T1484','T1611','T1068','T1055','T1612','T1622','T1140','T1006','T1480','T1211','T1222','T1564','T1562','T1070','T1202','T1036','T1578','T1112','T1601','T1599','T1027','T1647','T1620','T1207','T1014','T1553','T1218','T1216','T1221','T1127','T1535','T1550','T1497','T1600','T1220','T1557','T1110','T1555','T1212','T1187','T1606','T1056','T1111','T1621','T1040','T1003','T1528','T1558','T1539','T1552','T1087','T1010','T1217','T1580','T1538','T1526','T1619','T1613','T1482','T1083','T1615','T1046','T1135','T1201','T1120','T1069','T1057','T1012','T1018','T1518','T1082','T1614','T1016','T1049','T1033','T1007','T1124','T1210','T1534','T1570','T1563','T1021','T1080','T1560','T1123','T1119','T1185','T1115','T1530','T1602','T1213','T1005','T1039','T1025','T1074','T1114','T1113','T1125','T1071','T1092','T1132','T1001','T1568','T1573','T1008','T1105','T1104','T1095','T1571','T1572','T1090','T1219','T1102','T1020','T1030','T1048','T1041','T1011','T1052','T1567','T1029','T1537','T1531','T1485','T1486','T1565','T1491','T1561','T1499','T1495','T1490','T1498','T1496','T1489','T1529']

NAME_TECHNIQUES = ['Active Scanning','Gather Victim Host Information','Gather Victim Identity Information','Gather Victim Network Information','Gather Victim Org Information','Phishing for Information','Search Closed Sources','Search Open Technical Databases','Search Open Websites/Domains','Search Victim-Owned Websites','Acquire Infrastructure','Compromise Accounts','Compromise Infrastructure','Develop Capabilities','Establish Accounts','Obtain Capabilities','Stage Capabilities','Drive-by Compromise','Exploit Public-Facing Application','External Remote Services','Hardware Additions','Phishing','Replication Through Removable Media','Supply Chain Compromise','Trusted Relationship','Valid Accounts','Command and Scripting Interpreter','Container Administration Command','Deploy Container','Exploitation for Client Execution','Inter-Process Communication','Native API','Scheduled Task/Job','Shared Modules','Software Deployment Tools','System Services','User Execution','Windows Management Instrumentation','Account Manipulation','BITS Jobs','Boot or Logon Autostart Execution','Boot or Logon Initialization Scripts','Browser Extensions','Compromise Client Software Binary','Create Account','Create or Modify System Process','Event Triggered Execution','Hijack Execution Flow','Implant Internal Image','Modify Authentication Process','Office Application Startup','Pre-OS Boot','Server Software Component','Traffic Signaling','Abuse Elevation Control Mechanism','Access Token Manipulation','Domain Policy Modification','Escape to Host','Exploitation for Privilege Escalation','Process Injection','Build Image on Host','Debugger Evasion','Deobfuscate/Decode Files or Information','Direct Volume Access','Execution Guardrails','Exploitation for Defense Evasion','File and Directory Permissions Modification','Hide Artifacts','Impair Defenses','Indicator Removal on Host','Indirect Command Execution','Masquerading','Modify Cloud Compute Infrastructure','Modify Registry','Modify System Image','Network Boundary Bridging','Obfuscated Files or Information','Plist File Modification','Reflective Code Loading','Rogue Domain Controller','Rootkit','Subvert Trust Controls','Signed Binary Proxy Execution','Signed Script Proxy Execution','Template Injection','Trusted Developer Utilities Proxy Execution','Unused/Unsupported Cloud Regions','Use Alternate Authentication Material','Virtualization/Sandbox Evasion','Weaken Encryption','XSL Script Processing','Adversary-in-the-Middle','Brute Force','Credentials from Password Stores','Exploitation for Credential Access','Forced Authentication','Forge Web Credentials','Input Capture','Two-Factor Authentication Interception','Multi-Factor Authentication Request Generation','Network Sniffing','OS Credential Dumping','Steal Application Access Token','Steal or Forge Kerberos Tickets','Steal Web Session Cookie','Unsecured Credentials','Account Discovery','Application Window Discovery','Browser Bookmark Discovery','Cloud Infrastructure Discovery','Cloud Service Dashboard','Cloud Service Discovery','Cloud Storage Object Discovery','Container and Resource Discovery','Domain Trust Discovery','File and Directory Discovery','Group Policy Discovery','Network Service Scanning','Network Share Discovery','Password Policy Discovery','Peripheral Device Discovery','Permission Groups Discovery','Process Discovery','Query Registry','Remote System Discovery','Software Discovery','System Information Discovery','System Location Discovery','System Network Configuration Discovery','System Network Connections Discovery','System Owner/User Discovery','System Service Discovery','System Time Discovery','Exploitation of Remote Services','Internal Spearphishing','Lateral Tool Transfer','Remote Service Session Hijacking','Remote Services','Taint Shared Content','Archive Collected Data','Audio Capture','Automated Collection','Browser Session Hijacking','Clipboard Data','Data from Cloud Storage Object','Data from Configuration Repository','Data from Information Repositories','Data from Local System','Data from Network Shared Drive','Data from Removable Media','Data Staged','Email Collection','Screen Capture','Video Capture','Application Layer Protocol','Communication Through Removable Media','Data Encoding','Data Obfuscation','Dynamic Resolution','Encrypted Channel','Fallback Channels','Ingress Tool Transfer','Multi-Stage Channels','Non-Application Layer Protocol','Non-Standard Port','Protocol Tunneling','Proxy','Remote Access Software','Web Service','Automated Exfiltration','Data Transfer Size Limits','Exfiltration Over Alternative Protocol','Exfiltration Over C2 Channel','Exfiltration Over Other Network Medium','Exfiltration Over Physical Medium','Exfiltration Over Web Service','Scheduled Transfer','Transfer Data to Cloud Account','Account Access Removal','Data Destruction','Data Encrypted for Impact','Data Manipulation','Defacement','Disk Wipe','Endpoint Denial of Service','Firmware Corruption','Inhibit System Recovery','Network Denial of Service','Resource Hijacking','Service Stop','System Shutdown/Reboot']

NAME_TACTICS_MAP = {c: n for c, n in zip(CODE_TACTICS, NAME_TACTICS)}
NAME_TECH_MAP    = {c: n for c, n in zip(CODE_TECHNIQUES, NAME_TECHNIQUES)}

# === Relationship table needed for post-processing (by code, safe) ===
TACTICS_TECHNIQUES_RELATIONSHIP_DF = pd.DataFrame({
    'TA0043': pd.Series(['T1595','T1592','T1589','T1590','T1591','T1598','T1597','T1596','T1593','T1594']),
    'TA0042': pd.Series(['T1583','T1586','T1584','T1587','T1585','T1588','T1608']),
    'TA0001': pd.Series(['T1189','T1190','T1133','T1200','T1566','T1091','T1195','T1199','T1078']),
    'TA0002': pd.Series(['T1059','T1609','T1610','T1203','T1559','T1106','T1053','T1129','T1072','T1569','T1204','T1047']),
    'TA0003': pd.Series(['T1098','T1197','T1547','T1037','T1176','T1554','T1136','T1543','T1546','T1133','T1574','T1525','T1556','T1137','T1542','T1053','T1505','T1205','T1078']),
    'TA0004': pd.Series(['T1548','T1134','T1547','T1037','T1543','T1484','T1611','T1546','T1068','T1574','T1055','T1053','T1078']),
    'TA0005': pd.Series(['T1548','T1134','T1197','T1612','T1622','T1140','T1610','T1006','T1484','T1480','T1211','T1222','T1564','T1574','T1562','T1070','T1202','T1036','T1556','T1578','T1112','T1601','T1599','T1027','T1647','T1542','T1055','T1620','T1207','T1014','T1553','T1218','T1216','T1221','T1205','T1127','T1535','T1550','T1078','T1497','T1600','T1220']),
    'TA0006': pd.Series(['T1557','T1110','T1555','T1212','T1187','T1606','T1056','T1556','T1111','T1621','T1040','T1003','T1528','T1558','T1539','T1552']),
    'TA0007': pd.Series(['T1087','T1010','T1217','T1580','T1538','T1526','T1619','T1613','T1622','T1482','T1083','T1615','T1046','T1135','T1040','T1201','T1120','T1069','T1057','T1012','T1018','T1518','T1082','T1614','T1016','T1049','T1033','T1007','T1124','T1497']),
    'TA0008': pd.Series(['T1210','T1534','T1570','T1563','T1021','T1091','T1072','T1080','T1550']),
    'TA0009': pd.Series(['T1557','T1560','T1123','T1119','T1185','T1115','T1530','T1602','T1213','T1005','T1039','T1025','T1074','T1114','T1056','T1113','T1125']),
    'TA0011': pd.Series(['T1071','T1092','T1132','T1001','T1568','T1573','T1008','T1105','T1104','T1095','T1571','T1572','T1090','T1219','T1205','T1102']),
    'TA0010': pd.Series(['T1020','T1030','T1048','T1041','T1011','T1052','T1567','T1029','T1537']),
    'TA0040': pd.Series(['T1531','T1485','T1486','T1565','T1491','T1561','T1499','T1495','T1490','T1498','T1496','T1489','T1529'])
})

# === Use the exact training clean_text ===
def clean_text(text):
    text = str(text).lower()
    text = re.sub("\r\n", "\t", text)
    text = re.sub(r"what's", "what is ", text)
    text = re.sub(r"\'s", " ", text)
    text = re.sub(r"\'ve", " have ", text)
    text = re.sub(r"can't", "can not ", text)
    text = re.sub(r"n't", " not ", text)
    text = re.sub(r"i'm", "i am ", text)
    text = re.sub(r"\'re", " are ", text)
    text = re.sub(r"\'d", " would ", text)
    text = re.sub(r"\'ll", " will ", text)
    text = re.sub(r"\'scuse", " excuse ", text)
    text = re.sub('(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(/(?:[0-2][0-9]|3[0-2]|[0-9]))?', 'IPv4', text)
    text = re.sub(r'\b(CVE\-\d{4}\-\d{4,6})\b', 'CVE', text)
    text = re.sub(r'\b([a-z][_a-z0-9-.]+@[a-z0-9-]+\.[a-z]+)\b', 'email', text)
    text = re.sub(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', 'IP', text)
    text = re.sub(r'\b([a-f0-9]{32}|[A-F0-9]{32})\b', 'MD5', text)
    text = re.sub(r'\b((HKLM|HKCU)\\[\\A-Za-z0-9-_]+)\b', 'registry', text)
    text = re.sub(r'\b([a-f0-9]{40}|[A-F0-9]{40})\b', 'SHA1', text)
    text = re.sub(r'\b([a-f0-9]{64}|[A-F0-9]{64})\b', 'SHA250', text)
    text = re.sub(r'http(s)?:\\[0-9a-zA-Z_\.\-\\]+.', 'URL', text)
    text = re.sub(r'CVE-\d{4}-\d{4,6}', 'vulnerability', text)
    text = re.sub(r'[a-zA-Z]{1}:[\\][0-9a-zA-Z_\.\-\\]+', 'file', text)
    text = re.sub(r'\b[a-fA-F\d]{32}\b|\b[a-fA-F\d]{40}\b|\b[a-fA-F\d]{64}\b', 'hash', text)
    text = re.sub('x[A-Fa-f0-9]{2}', ' ', text)
    text = re.sub(r'\W', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def df_from_text(text: str) -> pd.DataFrame:
    df = pd.DataFrame({"Text": [text]})
    df["processed"] = df["Text"].apply(clean_text)
    return df


# === Post-processing (reworked to use dynamic label lists) ===
def confidence_propagation(predprob_tactics, pred_techniques, predprob_techniques,
                           tactic_codes, technique_codes):
    pred_techniques = pred_techniques.copy()
    predprob_techniques = predprob_techniques.copy()

    # tactics scores frame with the *actual* tactic codes used
    tconf_df = pd.DataFrame(data=predprob_tactics, columns=tactic_codes)

    for j, tech_code in enumerate(technique_codes):
        for i in range(predprob_techniques.shape[0]):
            # sum contributions from related tactics (by CODE, not index)
            for tact in tactic_codes:
                rel = TACTICS_TECHNIQUES_RELATIONSHIP_DF.get(tact)
                if rel is not None and (rel == tech_code).any():
                    # classic CP lambda
                    lam = 1.0 / (np.exp(abs(predprob_techniques[i][j] - tconf_df[tact].iloc[i])))
                    predprob_techniques[i][j] += lam * tconf_df[tact].iloc[i]
            pred_techniques[i][j] = 1 if predprob_techniques[i][j] >= 0 else 0
    return pred_techniques, predprob_techniques

def hanging_node(pred_tactics, predprob_tactics, pred_techniques, predprob_techniques,
                 c, d, tactic_codes, technique_codes):
    out = pred_techniques.copy()
    for i in range(len(out)):
        for j, tech_code in enumerate(technique_codes):
            for k, tact_code in enumerate(tactic_codes):
                rel = TACTICS_TECHNIQUES_RELATIONSHIP_DF.get(tact_code)
                if rel is not None and (rel == tech_code).any():
                    if (0 < predprob_techniques[i][j] < c) and (predprob_tactics[i][k] < d):
                        out[i][j] = 0
    return out


# === Paths ===
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(ROOT, "Data")
OUT_DIR = os.path.join(ROOT, "results", "attack_ttp")
os.makedirs(OUT_DIR, exist_ok=True)

MODELS_DIR = os.path.join(ROOT, "Entity-Extraction", "rcATT", "Models")
TACTICS_MODEL = os.path.join(MODELS_DIR, "tactics.joblib")
TECHNIQUES_MODEL = os.path.join(MODELS_DIR, "techniques.joblib")
CONFIG_PATH = os.path.join(MODELS_DIR, "configuration.joblib")
LABEL_ORDER_PATH = os.path.join(MODELS_DIR, "label_order.json")

def load_label_order():
    labels_all = json.load(open(LABEL_ORDER_PATH, "r", encoding="utf-8"))
    # Tactics are TA*, techniques are everything else (Txxxx / Txxxx.xxx)
    labs_ta_all = [c for c in labels_all if c.startswith("TA")]
    labs_te_all = [c for c in labels_all if not c.startswith("TA")]
    return labs_ta_all, labs_te_all

def load_models():
    return joblib.load(TACTICS_MODEL), joblib.load(TECHNIQUES_MODEL)

def apply_postprocessing_and_soften(pred_tac, scr_tac, pred_tech, scr_tech,
                                    tactic_codes, technique_codes):
    # optional HN/CP depending on your saved config
    if os.path.exists(CONFIG_PATH):
        params = joblib.load(CONFIG_PATH)
        mode = params[0]
        if mode == "HN":
            c, d = params[1]
            pred_tech = hanging_node(pred_tac, scr_tac, pred_tech, scr_tech, c, d,
                                     tactic_codes, technique_codes)
        elif mode == "CP":
            pred_tech, scr_tech = confidence_propagation(scr_tac, pred_tech, scr_tech,
                                                         tactic_codes, technique_codes)

    # ===== OPTION A: no forced top-k; keep only techniques with score >= margin =====
    margin = 0.0  # set to 0.1 if you want a stricter cutoff
    soft = (scr_tech >= margin).astype(int)
    return pred_tac, scr_tac, soft, scr_tech

def name_for_code(code: str) -> str:
    if code.startswith("TA"):
        return NAME_TACTICS_MAP.get(code, "")
    return NAME_TECH_MAP.get(code, "")

def predict_on_text(text, tactics_pipe, techniques_pipe, labs_ta_all, labs_te_all):
    df = df_from_text(text)

    # raw predictions
    pred_tac  = tactics_pipe.predict(df)
    scr_tac   = tactics_pipe.decision_function(df)
    pred_tech = techniques_pipe.predict(df)
    scr_tech  = techniques_pipe.decision_function(df)

    # reconcile lengths with saved label order slices
    n_ta = int(np.asarray(pred_tac).reshape(-1).shape[0])
    n_te = int(np.asarray(pred_tech).reshape(-1).shape[0])

    labs_ta = labs_ta_all[:n_ta]
    labs_te = labs_te_all[:n_te]

    if (n_ta != len(labs_ta_all)) or (n_te != len(labs_te_all)):
        print(f"[warn] label/order mismatch: "
              f"tactics model={n_ta} vs labels={len(labs_ta_all)}; "
              f"techniques model={n_te} vs labels={len(labs_te_all)}. "
              f"Using first {n_ta}/{n_te} respectively.")

    # post-processing with the correct codes
    pred_tac, scr_tac, pred_tech, scr_tech = apply_postprocessing_and_soften(
        pred_tac, scr_tac, pred_tech, scr_tech, labs_ta, labs_te
    )

    # map indices → codes (by current slices)
    tacs = [{"code": labs_ta[i],
             "name": name_for_code(labs_ta[i]),
             "score": float(scr_tac[0][i])}
            for i, v in enumerate(pred_tac[0]) if int(v) == 1]

    techs = [{"code": labs_te[i],
              "name": name_for_code(labs_te[i]),
              "score": float(scr_tech[0][i])}
             for i, v in enumerate(pred_tech[0]) if int(v) == 1]

    tacs.sort(key=lambda x: x["score"], reverse=True)
    techs.sort(key=lambda x: x["score"], reverse=True)
    return tacs, techs, (n_ta, n_te, len(labs_ta_all), len(labs_te_all))

def main():
    # load models + label order
    labs_ta_all, labs_te_all = load_label_order()
    tactics_pipe, techniques_pipe = load_models()

    txt_files = sorted(glob.glob(os.path.join(DATA_DIR, "*.txt")))
    if not txt_files:
        print(f"[!] No reports found in {DATA_DIR}")
        return

    for idx, path in enumerate(txt_files, 1):
        fname = os.path.basename(path)
        print(f"[{idx}/{len(txt_files)}] {fname}")
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except Exception as e:
            print(f"    [x] Failed to read: {e}")
            continue

        tacs, techs, dims = predict_on_text(text, tactics_pipe, techniques_pipe, labs_ta_all, labs_te_all)
        (n_ta, n_te, n_ta_lbl, n_te_lbl) = dims
        if (n_ta != n_ta_lbl) or (n_te != n_te_lbl):
            print(f"    [dbg] dims: tactics_out={n_ta}/{n_ta_lbl}, techniques_out={n_te}/{n_te_lbl}")

        result = {
            "file": fname,
            "iocs": {
                "attack_tactics":    {"pre_attack": [], "enterprise": [t['code'] for t in tacs], "mobile": []},
                "attack_techniques": {"pre_attack": [], "enterprise": [t['code'] for t in techs], "mobile": []},
            },
            "ttp_details": {"tactics": tacs, "techniques": techs}
        }
        out_path = os.path.join(OUT_DIR, f"{fname}.ttps.json")
        with open(out_path, "w", encoding="utf-8") as out:
            json.dump(result, out, indent=2)
        print(f"    [✓] Wrote {out_path}")

if __name__ == "__main__":
    main()
