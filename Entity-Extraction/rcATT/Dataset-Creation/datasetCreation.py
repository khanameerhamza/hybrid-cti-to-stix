# datasetCreation.py (patched)
import csv
import os
import sys
import pandas as pd
from attackcti import attack_client

# --- CSV field size guard (as in original) ---
maxInt = sys.maxsize
while True:
    try:
        csv.field_size_limit(maxInt)
        break
    except OverflowError:
        maxInt = int(maxInt / 10)

# --- Constants from the rcATT paper/repo ---
CODE_TACTICS = [
    'TA0043', 'TA0042', 'TA0001', 'TA0002', 'TA0003', 'TA0004', 'TA0005',
    'TA0006', 'TA0007', 'TA0008', 'TA0009', 'TA0011', 'TA0010', 'TA0040'
]
NAME_TACTICS = [
    'Reconnaissance', 'Resource Development', 'Initial Access', 'Execution',
    'Persistence', 'Privilege Escalation', 'Defense Evasion', 'Credential Access',
    'Discovery', 'Lateral Movement', 'Collection', 'Command and Control',
    'Exfiltration', 'Impact'
]

CODE_TECHNIQUES = [
    'T1595','T1592','T1589','T1590','T1591','T1598','T1597','T1596','T1593','T1594',
    'T1583','T1586','T1584','T1587','T1585','T1588','T1608','T1189','T1190','T1133',
    'T1200','T1566','T1091','T1195','T1199','T1078','T1059','T1609','T1610','T1203',
    'T1559','T1106','T1053','T1129','T1072','T1569','T1204','T1047','T1098','T1197',
    'T1547','T1037','T1176','T1554','T1136','T1543','T1546','T1574','T1525','T1556',
    'T1137','T1542','T1505','T1205','T1548','T1134','T1484','T1611','T1068','T1055',
    'T1612','T1622','T1140','T1006','T1480','T1211','T1222','T1564','T1562','T1070',
    'T1202','T1036','T1578','T1112','T1601','T1599','T1027','T1647','T1620','T1207',
    'T1014','T1553','T1218','T1216','T1221','T1127','T1535','T1550','T1497','T1600',
    'T1220','T1557','T1110','T1555','T1212','T1187','T1606','T1056','T1111','T1621',
    'T1040','T1003','T1528','T1558','T1539','T1552','T1087','T1010','T1217','T1580',
    'T1538','T1526','T1619','T1613','T1482','T1083','T1615','T1046','T1135','T1201',
    'T1120','T1069','T1057','T1012','T1018','T1518','T1082','T1614','T1016','T1049',
    'T1033','T1007','T1124','T1210','T1534','T1570','T1563','T1021','T1080','T1560',
    'T1123','T1119','T1185','T1115','T1530','T1602','T1213','T1005','T1039','T1025',
    'T1074','T1114','T1113','T1125','T1071','T1092','T1132','T1001','T1568','T1573',
    'T1008','T1105','T1104','T1095','T1571','T1572','T1090','T1219','T1102','T1020',
    'T1030','T1048','T1041','T1011','T1052','T1567','T1029','T1537','T1531','T1485',
    'T1486','T1565','T1491','T1561','T1499','T1495','T1490','T1498','T1496','T1489','T1529'
]

# tactic -> techniques (as in original code)
import pandas as pd
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

# --- Paths (relative to repo root) ---
OUT_DATASET = os.path.join('.', 'Entity-Extraction', 'rcATT', 'Dataset.csv')
URL_CONTENT_BASE = os.path.join('.', 'Entity-Extraction', 'rcATT', 'Dataset-Creation', 'URL_Content')
OLD_DATASET = os.path.join('.', 'Entity-Extraction', 'rcATT', 'Dataset-Creation', 'oldDataset.csv')

# --- ATT&CK client ---
lift = attack_client()
tactics = lift.get_enterprise_tactics()
techniques = lift.get_enterprise_techniques()

# --- Build header: Text + all TTP flags ---
header = ['Text'] + CODE_TACTICS + CODE_TECHNIQUES
n_flags = len(header) - 1  # number of binary columns (all TTPs)

os.makedirs(os.path.dirname(OUT_DATASET), exist_ok=True)

with open(OUT_DATASET, 'w', encoding='utf8', newline='') as dataset:
    writer = csv.writer(dataset, lineterminator='\n')
    writer.writerow(header)

    # ---------- TACTICS ----------
    print('[🖋️ WRITING TACTICS]')
    for i_tact, code in enumerate(CODE_TACTICS):
        for tact in tactics:
            try:
                ext_id = tact.get('external_references', [{}])[0].get('external_id', '')
            except Exception:
                ext_id = ''
            if ext_id == code:
                desc = (tact.get('description') or '').replace('\n', ' ')
                row = [desc]
                flags = ['0'] * n_flags
                flags[i_tact] = '1'  # set the correct tactic flag
                row.extend(flags)
                writer.writerow(row)

    # ---------- TECHNIQUES ----------
    print('[🖋️ WRITING TECHNIQUES]')
    for code in CODE_TECHNIQUES:
        for tech in techniques:
            try:
                ext_id = tech.get('external_references', [{}])[0].get('external_id', '')
            except Exception:
                ext_id = ''
            # Include both techniques and sub-techniques (split at dot)
            if ext_id.split('.')[0] == code:
                desc = (tech.get('description') or '').replace('\n', ' ')
                flags = ['0'] * n_flags

                # set technique flag (after all tactics)
                # positions: [0..len(CODE_TACTICS)-1] are tactics, then techniques
                tech_pos = len(CODE_TACTICS) + CODE_TECHNIQUES.index(code)
                flags[tech_pos] = '1'

                # set related tactic flags based on relationship table
                for tact_code in CODE_TACTICS:
                    tact_series = TACTICS_TECHNIQUES_RELATIONSHIP_DF.get(tact_code, pd.Series(dtype=str))
                    if not tact_series.empty and code in set(tact_series.dropna().tolist()):
                        flags[CODE_TACTICS.index(tact_code)] = '1'

                # write row for the technique description
                writer.writerow([desc] + flags)

                # add any external URL text we may have downloaded
                technique_name = (tech.get('name') or '').replace('/', '_')
                url_dir_path = os.path.join(URL_CONTENT_BASE, technique_name)
                if os.path.isdir(url_dir_path):
                    for fname in os.listdir(url_dir_path):
                        fpath = os.path.join(url_dir_path, fname)
                        try:
                            with open(fpath, 'r', encoding='utf8') as f:
                                content = f.read().replace('\n', ' ')
                                writer.writerow([content] + flags)
                        except Exception as e:
                            print(f'[WARN] Could not read URL content: {fpath} ({e})')

    # ---------- MERGE legacy rcATT dataset if present ----------
    print('[🖋️ ADDING rcATT DATASET (if present)]')
    if os.path.exists(OLD_DATASET):
        try:
            with open(OLD_DATASET, 'r', encoding='utf8', newline='') as rcATT:
                reader = csv.reader(rcATT)
                rcATT_header = next(reader)  # first row

                # Our header minus 'Text'
                new_ttp_header = header[1:]
                old_ttp_header = rcATT_header[1:]

                # Deprecated/unknown TTPs present in old but not in new
                deprecated_old_ttps = [x for x in old_ttp_header if x not in new_ttp_header]

                for line in reader:
                    if not line:
                        continue
                    text = line[0]
                    old_flags = line[1:]

                    # indices with '1' in the old dataset
                    old_ones = [i for i, v in enumerate(old_flags) if isinstance(v, str) and v.strip().lower() == '1']

                    # map to new positions
                    new_flags = ['0'] * n_flags
                    for old_idx in old_ones:
                        if 0 <= old_idx < len(old_ttp_header):
                            ttp_name = old_ttp_header[old_idx]
                            if ttp_name in deprecated_old_ttps:
                                continue
                            try:
                                new_idx = new_ttp_header.index(ttp_name)
                                new_flags[new_idx] = '1'
                            except ValueError:
                                # TTP truly not in new header; skip
                                pass

                    writer.writerow([text] + new_flags)

            print('[rcATT] Merged oldDataset.csv successfully.')
        except Exception as e:
            print(f'[rcATT] WARNING: Failed to merge oldDataset.csv ({e}). Continuing without it.')
    else:
        print('[rcATT] oldDataset.csv not found — skipping merge.')

print(f'[✅ DONE] Wrote dataset to: {OUT_DATASET}')
