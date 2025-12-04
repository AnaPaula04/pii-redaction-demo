#!/usr/bin/env python3
"""
PII Redaction Demo v3: NER (Hugging Face) + Regex masks + Street filtering
Usage:
  python -W ignore ner/pii_redact_v3.py data/sample_sentences.txt [--min-score 0.85] [--mask-org] [--mask-zip] [--filter-streets]

What's new in v3 (Week 8):
- Street name filtering: add --filter-streets to avoid over-masking common street components
- Improved logging to show what was filtered
- Better documentation
"""

import sys, re, json, pathlib, unicodedata, argparse
from collections import Counter
from transformers import pipeline

# ---------------- Regex patterns ----------------
EMAIL_RE = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')
SSN_RE   = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
PHONE_RE = re.compile(r'(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]*)\d{3}[\s.-]?\d{4}(?!\d)')
SSN_BARE_RE = re.compile(r'(?<!\d)\d{9}(?!\d)')
ZIP_RE = re.compile(r'\b\d{5}(?:-\d{4})?\b')

# ---------------- Street filtering ----------------
COMMON_STREET_WORDS = {
    'street', 'st', 'st.', 
    'avenue', 'ave', 'ave.',
    'road', 'rd', 'rd.',
    'boulevard', 'blvd', 'blvd.',
    'lane', 'ln', 'ln.',
    'drive', 'dr', 'dr.',
    'way', 'court', 'ct', 'ct.',
    'place', 'pl', 'pl.',
    'circle', 'cir', 'cir.',
    'parkway', 'pkwy', 'pkwy.',
    'highway', 'hwy', 'hwy.'
}

def should_filter_location(entity_text, filter_streets):
    """Return True if this location should be filtered (not masked)"""
    if not filter_streets:
        return False
    
    text_lower = entity_text.lower().strip()
    
    # Check if it's just a street word
    if text_lower in COMMON_STREET_WORDS:
        return True
    
    # Check if it ends with a street word (e.g., "State St", "Main Street")
    words = text_lower.split()
    if len(words) >= 2 and words[-1] in COMMON_STREET_WORDS:
        return True
    
    return False



# ---------------- Title detection ----------------
COMMON_TITLES = {
    'dr', 'dr.', 'doctor',
    'mr', 'mr.', 'mister',
    'ms', 'ms.', 
    'mrs', 'mrs.', 'missus',
    'miss',
    'prof', 'prof.', 'professor',
    'rev', 'rev.', 'reverend',
    'hon', 'hon.', 'honorable',
    'sen', 'sen.', 'senator',
    'rep', 'rep.', 'representative',
    'capt', 'capt.', 'captain',
    'lt', 'lt.', 'lieutenant',
    'sgt', 'sgt.', 'sergeant',
    'gen', 'gen.', 'general'
}

def detect_titles_and_names(text: str, ents: list) -> list:
    """
    Find patterns like 'Dr. Washington' and add them as PERSON entities
    if they weren't already detected by NER.
    Returns enhanced entity list with title-based detections.
    """
    import re
    
    # Pattern: Title followed by capitalized word(s)
    title_pattern = r'\b(' + '|'.join(re.escape(t) for t in COMMON_TITLES) + r')\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b'
    
    enhanced_ents = list(ents)  # Copy existing entities
    
    for match in re.finditer(title_pattern, text, re.IGNORECASE):
        name_start = match.start(2)  # Start of the name (after title)
        name_end = match.end(2)      # End of the name
        
        # Check if this span is already detected as PERSON
        already_detected = False
        for e in ents:
            if e.get('entity_group') == 'PER':
                e_start, e_end = e.get('start', -1), e.get('end', -1)
                # If there's overlap with existing PERSON entity, skip
                if not (name_end <= e_start or name_start >= e_end):
                    already_detected = True
                    break
        
        if not already_detected:
            # Add new entity for the name part (not the title)
            enhanced_ents.append({
                'entity_group': 'PER',
                'start': name_start,
                'end': name_end,
                'word': text[name_start:name_end],
                'score': 0.95  # High confidence for title-based detection
            })
    
    return enhanced_ents

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
    if re.search(r'(?i)\bSSN\b', text):
        text, c = SSN_BARE_RE.subn("[SSN_REDACTED]", text); counts["SSN"] += c
    if use_zip:
        text, c = ZIP_RE.subn("[ZIP_REDACTED]", text); counts["ZIP"] += c
    return text, counts

def clean_and_filter_ents(ents, min_score: float):
    """Cast to plain Python types and FILTER by score >= min_score."""
    cleaned = []
    for e in ents:
        e2 = dict(e)
        sc = e2.get("score", 0.0)
        try:
            sc = float(sc)
        except:
            sc = 0.0
        e2["score"] = sc
        for k in ("start","end"):
            if k in e2:
                try: e2[k] = int(e2[k])
                except: pass
        if "entity_group" in e2 and not isinstance(e2["entity_group"], str):
            e2["entity_group"] = str(e2["entity_group"])
        if sc >= min_score:
            cleaned.append(e2)
    return cleaned

def mask_ner_multi(text: str, ents, group_to_token: dict, filter_streets: bool = False):
    """
    Replace requested NER groups in a single right->left pass on the ORIGINAL text.
    Example group_to_token: {"PER": "[PERSON_REDACTED]", "LOC": "[LOC_REDACTED]", "ORG": "[ORG_REDACTED]"}
    Returns (masked_text, counts_counter, filtered_counter)
    """
    counts = Counter()
    filtered_counts = Counter()
    sel = [e for e in ents if e.get("entity_group") in group_to_token]
    
    # Filter out street names if requested
    if filter_streets:
        filtered_sel = []
        for e in sel:
            entity_text = text[e["start"]:e["end"]]
            if e["entity_group"] == "LOC" and should_filter_location(entity_text, filter_streets):
                filtered_counts[e["entity_group"]] += 1
                continue
            filtered_sel.append(e)
        sel = filtered_sel
    
    for e in sorted(sel, key=lambda x: x["start"], reverse=True):
        start, end = int(e["start"]), int(e["end"])
        token = group_to_token[e["entity_group"]]
        text = text[:start] + token + text[end:]
        counts[e["entity_group"]] += 1
    
    return text, counts, filtered_counts

# ---------------- Main ----------------
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_file", help="Path to input .txt (one sentence per line)")
    ap.add_argument("--min-score", type=float, default=0.80, help="Minimum NER confidence to mask (default: 0.80)")
    ap.add_argument("--mask-org", action="store_true", help="Also mask organizations (ORG)")
    ap.add_argument("--mask-zip", action="store_true", help="Also mask U.S. ZIP codes")
    ap.add_argument("--filter-streets", action="store_true", help="Filter out common street name components")
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
    if args.filter_streets:
        print("Street name filtering: ENABLED")
    nlp = pipeline("ner", model="dslim/bert-base-NER", aggregation_strategy="simple")

    totals = Counter()
    filtered_totals = Counter()
    redacted_lines = []

    with open(infile, encoding="utf-8") as fin, open(out_entities, "w", encoding="utf-8") as rep:
        for line in fin:
            s = line.strip()
            if not s:
                continue

            s = preprocess_text(s)
            ents = nlp(s)
            ents = detect_titles_and_names(s, ents)
            ents_f = clean_and_filter_ents(ents, args.min_score)
            rep.write(json.dumps({"text": s, "entities": ents_f}, ensure_ascii=False) + "\n")

            # 1) NER masking in one pass (PER, LOC, optionally ORG)
            groups = {"PER": "[PERSON_REDACTED]", "LOC": "[LOC_REDACTED]"}
            if args.mask_org:
                groups["ORG"] = "[ORG_REDACTED]"
            masked, ner_counts, filtered_counts = mask_ner_multi(s, ents_f, groups, args.filter_streets)
            
            # Map PER -> PERSON in totals
            totals["PERSON"] += ner_counts.get("PER", 0)
            totals["LOC"]    += ner_counts.get("LOC", 0)
            totals["ORG"]    += ner_counts.get("ORG", 0)
            
            # Track filtered items
            filtered_totals["LOC"] += filtered_counts.get("LOC", 0)

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
    
    if args.filter_streets and filtered_totals["LOC"]:
        print(f"\nFiltered (not masked):")
        print(f"  Streets: {filtered_totals['LOC']}")

if __name__ == "__main__":
    main()
