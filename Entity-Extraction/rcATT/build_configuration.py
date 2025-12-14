#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build a fresh configuration.joblib from your NEW dataset.

Supported inputs:
  A) CSV file with columns: text, label
  B) JSONL/JSON file where each record has: text, label
  C) A folder of .txt files + a separate labels file (CSV/JSON) mapping filename -> label

Outputs:
  - configuration.joblib (contains: label2id/id2label, tfidf vectorizer, basic hyperparams, seed)
  - config_summary.txt (human-readable summary of what was saved)

Usage examples:
  1) CSV:
     python build_configuration.py --csv path/to/train.csv --text-col text --label-col label --outdir cfg_out

  2) JSON Lines:
     python build_configuration.py --jsonl path/to/train.jsonl --text-key text --label-key label --outdir cfg_out

  3) Folder of .txt + labels CSV:
     python build_configuration.py --txt-dir data/ --labels-csv labels.csv --fname-col filename --label-col label --outdir cfg_out
"""
import argparse
import json
import os
import sys
import random
from pathlib import Path
from typing import List, Dict, Tuple, Any, Iterable, Optional

import joblib
import numpy as np

# Pandas and sklearn are standard in most ML environments
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer


def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)


def read_csv_text_labels(csv_path: str, text_col: str, label_col: str) -> Tuple[List[str], List[str]]:
    df = pd.read_csv(csv_path)
    if text_col not in df.columns or label_col not in df.columns:
        raise ValueError(f"CSV must contain columns '{text_col}' and '{label_col}'. Found: {list(df.columns)}")
    texts = df[text_col].astype(str).tolist()
    labels = df[label_col].astype(str).tolist()
    return texts, labels


def read_jsonl_text_labels(jsonl_path: str, text_key: str, label_key: str) -> Tuple[List[str], List[str]]:
    texts, labels = [], []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if text_key not in obj or label_key not in obj:
                raise ValueError(f"JSONL record missing keys. Expected '{text_key}' and '{label_key}'. Got: {obj.keys()}")
            text_val = obj[text_key]
            label_val = obj[label_key]
            # Normalize label to string (if list, join; adjust as needed)
            if isinstance(label_val, list):
                if len(label_val) != 1:
                    # Multi-label classification: join with "|" or handle differently per your pipeline.
                    label_val = "|".join(map(str, label_val))
                else:
                    label_val = str(label_val[0])
            texts.append(str(text_val))
            labels.append(str(label_val))
    return texts, labels


def read_json_text_labels(json_path: str, text_key: str, label_key: str) -> Tuple[List[str], List[str]]:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("JSON must be a list of objects.")
    texts, labels = [], []
    for obj in data:
        if text_key not in obj or label_key not in obj:
            raise ValueError(f"JSON record missing keys. Expected '{text_key}' and '{label_key}'. Got: {obj.keys()}")
        text_val = obj[text_key]
        label_val = obj[label_key]
        if isinstance(label_val, list):
            if len(label_val) != 1:
                label_val = "|".join(map(str, label_val))
            else:
                label_val = str(label_val[0])
        texts.append(str(text_val))
        labels.append(str(label_val))
    return texts, labels


def read_txt_dir_with_labels(txt_dir: str, labels_df: pd.DataFrame, fname_col: str, label_col: str) -> Tuple[List[str], List[str]]:
    # Expect labels_df to have filename (matching .txt files) and label
    if fname_col not in labels_df.columns or label_col not in labels_df.columns:
        raise ValueError(f"Labels CSV must contain '{fname_col}' and '{label_col}'. Found: {list(labels_df.columns)}")
    texts, labels = [], []
    base = Path(txt_dir)
    for _, row in labels_df.iterrows():
        fname = str(row[fname_col])
        label = str(row[label_col])
        fpath = base / fname
        if not fpath.exists():
            # Try adding .txt if missing
            if not fpath.suffix:
                fpath = base / (fname + ".txt")
        if not fpath.exists():
            raise FileNotFoundError(f"Text file not found for row: {row.to_dict()} -> looked for {fpath}")
        with open(fpath, "r", encoding="utf-8") as fh:
            text = fh.read()
        texts.append(text)
        labels.append(label)
    return texts, labels


def build_label_maps(labels: Iterable[str]) -> Tuple[Dict[str, int], Dict[int, str]]:
    unique = sorted(set(labels))
    label2id = {lbl: i for i, lbl in enumerate(unique)}
    id2label = {i: lbl for lbl, i in label2id.items()}
    return label2id, id2label


def fit_vectorizer(corpus: List[str],
                   ngram_range=(1, 2),
                   min_df=2,
                   max_df=0.9,
                   max_features=200000) -> TfidfVectorizer:
    """
    Fit a TF‑IDF vectorizer on YOUR corpus.
    Adjust ngram_range/min_df/max_df/max_features as needed for your task size.
    """
    vec = TfidfVectorizer(
        ngram_range=ngram_range,
        min_df=min_df,
        max_df=max_df,
        max_features=max_features,
        lowercase=True,
        strip_accents="unicode"
    )
    vec.fit(corpus)
    return vec


def save_configuration(outdir: str,
                       label2id: Dict[str, int],
                       id2label: Dict[int, str],
                       vectorizer: TfidfVectorizer,
                       seed: int,
                       extras: Optional[Dict[str, Any]] = None) -> str:
    cfg = {
        "label2id": label2id,
        "id2label": id2label,
        "num_labels": len(label2id),
        "vectorizer": vectorizer,
        "vectorizer_info": {
            "vocab_size": len(vectorizer.vocabulary_) if hasattr(vectorizer, "vocabulary_") else None,
            "ngram_range": vectorizer.ngram_range,
            "min_df": vectorizer.min_df,
            "max_df": vectorizer.max_df,
            "max_features": vectorizer.max_features,
        },
        "random_seed": seed,
        # You can add rcATT/STIX-specific knobs here if your training loop expects them:
        "model_hparams": {
            "hidden_dim": 256,
            "dropout": 0.2
        }
    }
    if extras:
        cfg.update(extras)

    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    cfg_path = outdir / "configuration.joblib"
    joblib.dump(cfg, cfg_path)

    # Also write a short summary for human inspection
    summary = [
        f"Saved: {cfg_path}",
        f"num_labels: {cfg['num_labels']}",
        f"labels: {sorted(label2id.keys())}",
        f"vectorizer.vocab_size: {cfg['vectorizer_info']['vocab_size']}",
        f"vectorizer.ngram_range: {cfg['vectorizer_info']['ngram_range']}",
        f"seed: {seed}",
    ]
    (outdir / "config_summary.txt").write_text("\n".join(summary), encoding="utf-8")
    return str(cfg_path)


def main():
    parser = argparse.ArgumentParser(description="Build configuration.joblib from a new dataset.")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--csv", type=str, help="Path to a CSV with text/label columns.")
    src.add_argument("--jsonl", type=str, help="Path to a JSONL file with records having text/label.")
    src.add_argument("--json", type=str, help="Path to a JSON list file with objects having text/label.")
    src.add_argument("--txt-dir", type=str, help="Path to a folder of .txt files (requires labels CSV/JSON).")

    parser.add_argument("--labels-csv", type=str, help="Labels CSV, required if --txt-dir is used.")
    parser.add_argument("--labels-json", type=str, help="Labels JSON (list of {filename,label}) if not using CSV.")

    parser.add_argument("--text-col", type=str, default="text", help="CSV text column name.")
    parser.add_argument("--label-col", type=str, default="label", help="CSV label column name.")
    parser.add_argument("--fname-col", type=str, default="filename", help="Filename column if using labels file.")

    parser.add_argument("--text-key", type=str, default="text", help="JSON/JSONL text key.")
    parser.add_argument("--label-key", type=str, default="label", help="JSON/JSONL label key.")

    parser.add_argument("--outdir", type=str, required=True, help="Output directory (will be created).")

    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility.")
    parser.add_argument("--ngram-min", type=int, default=1, help="Min n-gram size for TF-IDF.")
    parser.add_argument("--ngram-max", type=int, default=2, help="Max n-gram size for TF-IDF.")
    parser.add_argument("--min-df", type=int, default=2, help="TF-IDF min_df.")
    parser.add_argument("--max-df", type=float, default=0.9, help="TF-IDF max_df.")
    parser.add_argument("--max-features", type=int, default=200000, help="TF-IDF max_features.")

    args = parser.parse_args()

    set_seed(args.seed)

    # Load dataset (texts, labels)
    if args.csv:
        texts, labels = read_csv_text_labels(args.csv, args.text_col, args.label_col)
    elif args.jsonl:
        texts, labels = read_jsonl_text_labels(args.jsonl, args.text_key, args.label_key)
    elif args.json:
        texts, labels = read_json_text_labels(args.json, args.text_key, args.label_key)
    elif args.txt_dir:
        if not args.labels_csv and not args.labels_json:
            raise ValueError("When using --txt-dir, you must provide --labels-csv or --labels-json.")
        if args.labels_csv:
            labels_df = pd.read_csv(args.labels_csv)
        else:
            with open(args.labels_json, "r", encoding="utf-8") as f:
                records = json.load(f)
            labels_df = pd.DataFrame(records)
        texts, labels = read_txt_dir_with_labels(args.txt_dir, labels_df, args.fname_col, args.label_col)
    else:
        raise AssertionError("One input source must be provided.")

    if not texts:
        raise ValueError("No texts found.")
    if not labels:
        raise ValueError("No labels found.")
    if len(texts) != len(labels):
        raise ValueError(f"Mismatch: {len(texts)} texts vs {len(labels)} labels.")

    # Build label maps from YOUR labels
    label2id, id2label = build_label_maps(labels)

    # Fit TF-IDF on YOUR corpus with user-specified params
    vec = fit_vectorizer(
        texts,
        ngram_range=(args.ngram_min, args.ngram_max),
        min_df=args.min_df,
        max_df=args.max_df,
        max_features=args.max_features
    )

    # Save configuration.joblib + summary
    cfg_path = save_configuration(
        outdir=args.outdir,
        label2id=label2id,
        id2label=id2label,
        vectorizer=vec,
        seed=args.seed,
        extras=None
    )

    print(f"[OK] Wrote {cfg_path}")
    print(f"[OK] Labels: {sorted(label2id.keys())}")
    print(f"[OK] Vectorizer vocab size: {len(vec.vocabulary_)}")


if __name__ == "__main__":
    main()
