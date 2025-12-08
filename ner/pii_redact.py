#!/usr/bin/env python3
"""
PII Redaction Demo v2: NER (Hugging Face) + Regex masks + Filtering logic
Usage:
  python -W ignore ner/pii_redact.py data/sample_sentences.txt [--min-score 0.85] [--mask-org] [--mask-zip]

What’s new in v2 (Week 6):
- Confidence filtering: ignore NER entities below --min-score (default: 0.80)
- Optional ORG masking: add --mask-org to redact organizations
- Optional ZIP masking: add --mask-zip to redact U.S. ZIP codes
"""

import sys, re, json, pathlib, unicodedata, argparse
from collections import Counter
from transformers import pipeline

# ---------------- Regex patterns ----------------
EMAIL_RE = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')
SSN_RE   = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
# Phones like: (312) 555-0199, 312-555-0199, 312 555 0199, +1 312 555 0199, 312.555.0199
PHONE_RE = re.compile(r'(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]*)\d{3}[\s.-]?\d{4}(?!\d)')
# Bare 9-digit SSN (only applied when the line mentions "SSN")
SSN_BARE_RE = re.compile(r'(?<!\d)\d{9}(?!\d)')
# U.S. ZIP: 02139 or 02139-4307 (optional, via --mask-zip)
ZIP_RE = re.compile(r'\b\d{5}(?:-\d{4})?\b')

# ---------------- Helpers ----------------
def preprocess_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\u2018", "'").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    text = " ".join(text.split())
    return text

def mask_regex(text: str, use_zip: bool):
    counts = Counter()
    text, c = EMAIL_RE.subn("[EMAIL_REDACTED]", text); counts["EMAIL"] += c
    text, c = SSN_RE.subn("[SSN_REDACTED]", text);     counts["SSN"]   += c
    text, c = PHONE_RE.subn("[PHONE_REDACTED]", text); counts["PHONE"] += c
    # Bare SSN only if the line says "SSN"
    if re.search(r'(?i)\bSSN\b', text):
        text, c = SSN_BARE_RE.subn("[SSN_REDACTED]", text); counts["SSN"] += c
    # Optional ZIP
    if use_zip:
        text, c = ZIP_RE.subn("[ZIP_REDACTED]", text); counts["ZIP"] += c
    return text, counts

def clean_and_filter_ents(ents, min_score: float):
    """Cast to plain Python types and FILTER by score >= min_score."""
    cleaned = []
    for e in ents:
        e2 = dict(e)
        # score
        sc = e2.get("score", 0.0)
        try:
            sc = float(sc)
        except:
            sc = 0.0
        e2["score"] = sc
        # spans
        for k in ("start","end"):
            if k in e2:
                try: e2[k] = int(e2[k])
                except: pass
        # group => str
        if "entity_group" in e2 and not isinstance(e2["entity_group"], str):
            e2["entity_group"] = str(e2["entity_group"])
        # filter by confidence
        if sc >= min_score:
            cleaned.append(e2)
    return cleaned

def mask_ner_multi(text: str, ents, group_to_token: dict):
    """
    Replace requested NER groups in a single right->left pass on the ORIGINAL text.
    Example group_to_token: {"PER": "[PERSON_REDACTED]", "LOC": "[LOC_REDACTED]", "ORG": "[ORG_REDACTED]"}
    Returns (masked_text, counts_counter)
    """
    counts = Counter()
    sel = [e for e in ents if e.get("entity_group") in group_to_token]
    for e in sorted(sel, key=lambda x: x["start"], reverse=True):  # right->left
        start, end = int(e["start"]), int(e["end"])
        token = group_to_token[e["entity_group"]]
        text = text[:start] + token + text[end:]
        counts[e["entity_group"]] += 1
    return text, counts

# ---------------- Main ----------------
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_file", help="Path to input .txt (one sentence per line)")
    ap.add_argument("--min-score", type=float, default=0.80, help="Minimum NER confidence to mask (default: 0.80)")
    ap.add_argument("--mask-org", action="store_true", help="Also mask organizations (ORG)")
    ap.add_argument("--mask-zip", action="store_true", help="Also mask U.S. ZIP codes")
    return ap.parse_args()

def main():
    args = parse_args()
    infile = pathlib.Path(args.input_file)
    if not infile.exists():
        print(f"Input file not found: {infile}")
        sys.exit(1)

    out_redacted = infile.parent / "redacted_output.txt"
    out_entities = infile.parent / "entities_report.jsonl"

    print(f"Loading NER model (dslim/bert-base-NER) with min-score={args.min_score}...")
    nlp = pipeline("ner", model="dslim/bert-base-NER", aggregation_strategy="simple")

    totals = Counter()
    redacted_lines = []

    with open(infile, encoding="utf-8") as fin, open(out_entities, "w", encoding="utf-8") as rep:
        for line in fin:
            s = line.strip()
            if not s:
                continue

            s = preprocess_text(s)
            ents = nlp(s)
            ents_f = clean_and_filter_ents(ents, args.min_score)
            rep.write(json.dumps({"text": s, "entities": ents_f}, ensure_ascii=False) + "\n")

            # 1) NER masking in one pass (PER, LOC, optionally ORG)
            groups = {"PER": "[PERSON_REDACTED]", "LOC": "[LOC_REDACTED]"}
            if args.mask_org:
                groups["ORG"] = "[ORG_REDACTED]"
            masked, ner_counts = mask_ner_multi(s, ents_f, groups)
            # Map PER -> PERSON in totals
            totals["PERSON"] += ner_counts.get("PER", 0)
            totals["LOC"]    += ner_counts.get("LOC", 0)
            totals["ORG"]    += ner_counts.get("ORG", 0)

            # 2) Regex masks afterward (EMAIL/PHONE/SSN and optional ZIP)
            masked, rx_counts = mask_regex(masked, use_zip=args.mask_zip)
            totals.update(rx_counts)

            redacted_lines.append(masked)

    with open(out_redacted, "w", encoding="utf-8") as fout:
        fout.write("\n".join(redacted_lines))

    print("\n=== Done ===")
    print(f"- Entities report: {out_entities}")
    print(f"- Redacted text : {out_redacted}")
    print("\nSummary (masked counts):")
    for k in ("PERSON","LOC","ORG","EMAIL","PHONE","SSN","ZIP"):
        if totals[k]:
            print(f"  {k:7s}: {totals[k]}")
    if not any(totals.values()):
        print("  (no masks applied)")

if __name__ == "__main__":
    main()
