#!/usr/bin/env python3
"""
PII Redaction Demo: NER (Hugging Face) + Regex masks
Usage:
    python -W ignore ner/pii_redact.py data/sample_sentences.txt

Outputs:
    - data/redacted_output.txt
    - data/entities_report.jsonl
"""
import sys, re, json, pathlib, unicodedata
from collections import Counter
from transformers import pipeline

# ---------------- Regex patterns ----------------
# Email: support plus signs and subdomains
EMAIL_RE = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')
# SSN with dashes: 123-45-6789
SSN_RE   = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
# US phone: (312) 555-0199, 312-555-0199, 312 555 0199, +1 312 555 0199, 312.555.0199
PHONE_RE = re.compile(r'(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]*)\d{3}[\s.-]?\d{4}(?!\d)')
# Bare 9-digit SSN (we’ll use this only if the line mentions "SSN")
SSN_BARE_RE = re.compile(r'(?<!\d)\d{9}(?!\d)')


# ---------------- Helpers ----------------
def preprocess_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\u2018", "'").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    text = " ".join(text.split())
    return text

from collections import Counter

def mask_regex(text: str):
    counts = Counter()

    # Email
    text, c = EMAIL_RE.subn("[EMAIL_REDACTED]", text); counts["EMAIL"] += c # SSN with dashes
    text, c = SSN_RE.subn("[SSN_REDACTED]", text);     counts["SSN"]   += c # Phone
    text, c = PHONE_RE.subn("[PHONE_REDACTED]", text); counts["PHONE"] += c # Bare 9-digit SSN — apply only if the line hints it's an SSN (reduces false positives vs. any 9-digit number)
    
    if re.search(r'(?i)\bSSN\b', text):
        text, c = SSN_BARE_RE.subn("[SSN_REDACTED]", text); counts["SSN"] += c

    return text, counts


def clean_ents_for_json(ents):
    cleaned = []
    for e in ents:
        e2 = dict(e)
        if "score" in e2:
            try: e2["score"] = float(e2["score"])
            except: pass
        for k in ("start","end"):
            if k in e2:
                try: e2[k] = int(e2[k])
                except: pass
        if "entity_group" in e2 and not isinstance(e2["entity_group"], str):
            try: e2["entity_group"] = str(e2["entity_group"])
            except: pass
        cleaned.append(e2)
    return cleaned

def mask_ner_multi(text: str, ents, group_to_token: dict):
    """
    Replace all requested NER groups in a single right->left pass on the ORIGINAL text.
    Example: {"PER": "[PERSON_REDACTED]", "LOC": "[LOC_REDACTED]"}
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
def main():
    if len(sys.argv) < 2:
        print("Usage: python -W ignore ner/pii_redact.py data/sample_sentences.txt")
        sys.exit(1)

    infile = pathlib.Path(sys.argv[1])
    if not infile.exists():
        print(f"Input file not found: {infile}")
        sys.exit(1)

    out_redacted = infile.parent / "redacted_output.txt"
    out_entities = infile.parent / "entities_report.jsonl"

    print("Loading NER model (dslim/bert-base-NER)...")
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
            ents_clean = clean_ents_for_json(ents)
            rep.write(json.dumps({"text": s, "entities": ents_clean}, ensure_ascii=False) + "\n")

            # 1) NER masking for PERSON + LOC in one pass on ORIGINAL s
            masked, ner_counts = mask_ner_multi(s, ents_clean, {"PER": "[PERSON_REDACTED]", "LOC": "[LOC_REDACTED]"})
            totals["PERSON"] += ner_counts.get("PER", 0)
            totals["LOC"]    += ner_counts.get("LOC", 0)

            # 2) Regex masking afterward
            masked, rx_counts = mask_regex(masked)
            totals.update(rx_counts)

            redacted_lines.append(masked)

    with open(out_redacted, "w", encoding="utf-8") as fout:
        fout.write("\n".join(redacted_lines))

    print("\n=== Done ===")
    print(f"- Entities report: {out_entities}")
    print(f"- Redacted text : {out_redacted}")
    print("\nSummary (masked counts):")
    for k in ("PERSON","LOC","EMAIL","PHONE","SSN"):
        if totals[k]:
            print(f"  {k:7s}: {totals[k]}")
    if not any(totals.values()):
        print("  (no masks applied)")

if __name__ == "__main__":
    main()

