import streamlit as st
from transformers import pipeline

# 🟢 IMPORTS: Connecting to your logic
from pii_redact_v3 import (
    preprocess_text, 
    mask_regex, 
    clean_and_filter_ents, 
    mask_ner_multi,
    detect_titles_and_names
)

# ============================================================================
# 1. PAGE CONFIGURATION
# ============================================================================
st.set_page_config(
    page_title="PII Detection Assistant",
    page_icon="🔒",
    layout="wide"
)

# Load the AI Model
@st.cache_resource
def load_ner_model():
    return pipeline("ner", model="dslim/bert-base-NER", aggregation_strategy="simple")

nlp = load_ner_model()

# ============================================================================
# 2. SIDEBAR - SETTINGS
# ============================================================================
st.sidebar.header("⚙️ Configuration")

min_score = st.sidebar.slider(
    "Confidence Threshold (--min-score)", 
    min_value=0.70, max_value=0.95, value=0.80, step=0.05
)

mask_org = st.sidebar.checkbox("Mask Organizations (--mask-org)", value=False)
mask_zip = st.sidebar.checkbox("Mask ZIP Codes (--mask-zip)", value=False)
filter_streets = st.sidebar.checkbox("Filter Street Names (--filter-streets)", value=False)

st.sidebar.markdown("---")
st.sidebar.caption("💻 CLI Equivalent:")
cli_cmd = f"python pii_redact_v3.py input.txt --min-score {min_score}"
if mask_org: cli_cmd += " --mask-org"
if mask_zip: cli_cmd += " --mask-zip"
if filter_streets: cli_cmd += " --filter-streets"
st.sidebar.code(cli_cmd, language="bash")

# ============================================================================
# 3. MAIN HEADER
# ============================================================================
st.title("🔒 PII Detection Assistant")
st.markdown("**Powered by Hugging Face BERT-NER** (`dslim/bert-base-NER`)")
st.caption("Web interface for `pii_redact_v3.py`")
st.markdown("---")

# ============================================================================
# 4. INPUT & OUTPUT AREA
# ============================================================================
col_input, col_output = st.columns(2)

# --- LEFT COLUMN: INPUT ---
with col_input:
    st.subheader("📝 Input Text")
    
    # Simple Text Area (No Keys, No State = No Bugs)
    user_input = st.text_area(
        "Enter or paste your text below:",
        height=250,
        placeholder="Paste text here..."
    )

# --- RIGHT COLUMN: OUTPUT & STATS ---
with col_output:
    st.subheader("🔒 Masked Output")

    if user_input:
        with st.spinner("🔍 Processing..."):
            # 1. Processing Logic
            clean_text = preprocess_text(user_input)
            raw_ents = nlp(clean_text)
            ents_with_titles = detect_titles_and_names(clean_text, raw_ents)
            filtered_entities = clean_and_filter_ents(ents_with_titles, min_score)
            
            groups = {"PER": "[PERSON_REDACTED]", "LOC": "[LOC_REDACTED]"}
            if mask_org: groups["ORG"] = "[ORG_REDACTED]"
            
            masked_step1, ner_counts, filtered_counts = mask_ner_multi(
                clean_text, filtered_entities, groups, filter_streets
            )
            final_text, regex_counts = mask_regex(masked_step1, use_zip=mask_zip)
            
            # 2. Display Result (Read-Only Box)
            st.text_area(
                label="Redacted Result:",
                value=final_text,
                height=250,
                disabled=True 
            )

            # 3. Statistics
            st.subheader("📊 Statistics")
            total_counts = ner_counts + regex_counts
            total_entities = sum(total_counts.values())

            if total_entities > 0:
                st.success(f"✅ Total Entities Detected: {total_entities}")
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Summary:**")
                    for key, val in total_counts.items():
                        if val > 0: st.write(f"- **{key}:** {val}")
                with c2:
                    if filtered_entities:
                        scores = [e['score'] for e in filtered_entities if 'score' in e]
                        if scores:
                            avg = sum(scores) / len(scores)
                            st.markdown("**Confidence:**")
                            st.write(f"- Avg: `{avg:.3f}`")
                            st.write(f"- Max: `{max(scores):.3f}`")
            else:
                st.warning("⚠️ No PII detected.")
    else:
        st.info("👈 Enter text on the left to see masked output here")

# ============================================================================
# 5. FOOTER
# ============================================================================
st.markdown("---")
st.markdown("""
### 📚 About This Tool

This web interface uses **pii_redact_v3.py functions** with an interactive Streamlit UI.

**Core Functions Used:**
- `preprocess_text()` - Text normalization
- `detect_titles_and_names()` - Title detection (Dr., Prof., etc.)
- `mask_ner_multi()` - NER-based masking with street filtering 
- `mask_regex()` - Pattern-based detection (EMAIL, PHONE, SSN, ZIP)
- `clean_and_filter_ents()` - Confidence threshold filtering

**Detected Entity Types:**
- 👤 **PERSON**: Names of individuals (from NER)
- 📍 **LOCATION**: Cities, states, countries (from NER, optionally filter street names)
- 📧 **EMAIL**: Email addresses (from regex)
- 📞 **PHONE**: US phone numbers in various formats (from regex)
- 🔢 **SSN**: Social Security Numbers (from regex)
- 🏢 **ORGANIZATIONS** (optional): Company and organization names (from NER with --mask-org)
- 📮 **ZIP CODES** (optional): US postal codes (from regex with --mask-zip)

**Model:** dslim/bert-base-NER (BERT fine-tuned on CoNLL-2003)

**Created by:** Ana McCullagh | **Course:** CS314 Individualized Study | **Professor:** Dr. Manar Mohaisen  
**Northeastern Illinois University** | December 2025
""")