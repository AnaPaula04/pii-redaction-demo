"""
PII Detection Web Interface
Uses the functions from pii_redact_v3.py with a Streamlit UI
"""

import streamlit as st
import sys
from pathlib import Path

# Add the ner directory to Python path so I can import pii_redact_v3
sys.path.insert(0, str(Path(__file__).parent / "ner"))

# Import the alredy existent functions from pii_redact_v3.py
from pii_redact_v3 import (
    preprocess_text,
    mask_regex,
    clean_and_filter_ents,
    mask_ner_multi,
    should_filter_location
)
from transformers import pipeline
from collections import Counter

# Page configuration
st.set_page_config(
    page_title="PII Detection Assistant",
    page_icon="🔒",
    layout="wide"
)

# Title
st.title("🔒 PII Detection Assistant")
st.caption("Powered by Hugging Face BERT-NER (dslim/bert-base-NER)")
st.caption("Web interface for pii_redact_v3.py")

# Sidebar for settings
st.sidebar.header("⚙️ Configuration")
st.sidebar.markdown("*These match your CLI flags*")

min_score = st.sidebar.slider(
    "Confidence Threshold (--min-score)", 
    min_value=0.70, 
    max_value=0.95, 
    value=0.80, 
    step=0.05,
    help="Minimum confidence score for entity detection"
)

mask_org = st.sidebar.checkbox(
    "Mask Organizations (--mask-org)", 
    value=False,
    help="Detect and mask company/organization names"
)

mask_zip = st.sidebar.checkbox(
    "Mask ZIP Codes (--mask-zip)", 
    value=False,
    help="Detect and mask 5-digit ZIP codes"
)

# FIXED: Changed to match actual behavior
filter_streets = st.sidebar.checkbox(
    "Filter Street Names (--filter-streets)", 
    value=False,  # Default to NOT filtering (mask everything)
    help="When CHECKED: keeps street names visible (e.g., 'State St'). When UNCHECKED: masks all locations including streets."
)

st.sidebar.markdown("---")
st.sidebar.markdown("**CLI Equivalent:**")
cli_command = f"python pii_redact_v3.py input.txt --min-score {min_score}"
if mask_org:
    cli_command += " --mask-org"
if mask_zip:
    cli_command += " --mask-zip"
if filter_streets:  # Only add flag when checked (means filter OUT streets)
    cli_command += " --filter-streets"
st.sidebar.code(cli_command, language="bash")

# Load model (cached so it only loads once)
@st.cache_resource
def load_model():
    """Load the NER model - same as in my pii_redact_v3.py"""
    return pipeline("ner", model="dslim/bert-base-NER", aggregation_strategy="simple")

# Initialize session state
if 'user_text' not in st.session_state:
    st.session_state.user_text = ''

# Main content area
col1, col2 = st.columns(2)

with col1:
    st.subheader("📝 Input Text")
    
    # Example button
    if st.button("📄 Load Example"):
        st.session_state.user_text = """My name is Ana McCullagh and my phone number is (312) 555-0199.
Please email me at ana.mccullagh@example.com by Friday.
I work at Google in Chicago, IL 60601.
My SSN is 123-45-6789.
Meet me at 1200 N State St, Chicago, IL."""
        st.rerun()
    
    # Text input
    user_text = st.text_area(
        "Enter or paste your text below:",
        value=st.session_state.user_text,
        height=300,
        placeholder="Type or paste text here to detect PII...",
        key="text_input"
    )
    
    # Update session state
    st.session_state.user_text = user_text

with col2:
    st.subheader("🔒 Masked Output")
    
    if user_text.strip():
        with st.spinner("🔍 Detecting PII..."):
            try:
                # Load model
                nlp = load_model()
                
                # Step 1: Preprocess text (existent functions)
                processed_text = preprocess_text(user_text)
                
                # Step 2: Run NER (same as in my code)
                ents = nlp(processed_text)
                
                # Step 3: Filter by confidence (existent functions)
                ents_filtered = clean_and_filter_ents(ents, min_score)
                
                # Step 4: NER masking (my code functions with the same logic)
                groups = {"PER": "[PERSON_REDACTED]", "LOC": "[LOC_REDACTED]"}
                if mask_org:
                    groups["ORG"] = "[ORG_REDACTED]"
                
                # FIXED: Pass filter_streets directly (no inversion needed)
                masked_text, ner_counts, filtered_counts = mask_ner_multi(
                    processed_text, 
                    ents_filtered, 
                    groups, 
                    filter_streets  # When True, filters OUT streets (doesn't mask them)
                )
                
                # Step 5: Regex masking (existent functions)
                masked_text, rx_counts = mask_regex(masked_text, use_zip=mask_zip)
                
                # Combine counts (matching your v3 logic)
                totals = Counter()
                totals["PERSON"] += ner_counts.get("PER", 0)
                totals["LOC"]    += ner_counts.get("LOC", 0)
                totals["ORG"]    += ner_counts.get("ORG", 0)
                totals.update(rx_counts)
                
                # Display masked text
                st.text_area(
                    "Masked text:",
                    value=masked_text,
                    height=300,
                    disabled=True
                )
                
                # Statistics
                st.subheader("📊 Statistics")
                
                total_entities = sum(totals.values())
                
                if total_entities > 0:
                    st.success(f"✅ **Total Entities Detected:** {total_entities}")
                    
                    # Show breakdown (matching my v3 output order)
                    st.markdown("**Summary (masked counts):**")
                    for entity_type in ("PERSON", "LOC", "ORG", "EMAIL", "PHONE", "SSN", "ZIP"):
                        if totals[entity_type]:
                            st.metric(label=entity_type, value=totals[entity_type])
                    
                    # Show filtered items (if street filtering enabled)
                    if filter_streets and filtered_counts.get("LOC", 0) > 0:
                        st.markdown("---")
                        st.info(f"🚦 **Filtered (not masked):** {filtered_counts['LOC']} street name(s)")
                    
                    # Show confidence info
                    if ents_filtered:
                        avg_confidence = sum(e['score'] for e in ents_filtered) / len(ents_filtered)
                        max_confidence = max(e['score'] for e in ents_filtered)
                        min_confidence = min(e['score'] for e in ents_filtered)
                        
                        st.markdown("---")
                        st.markdown("### 📈 Confidence Scores")
                        conf_col1, conf_col2, conf_col3 = st.columns(3)
                        with conf_col1:
                            st.metric("Average", f"{avg_confidence:.3f}")
                        with conf_col2:
                            st.metric("Maximum", f"{max_confidence:.3f}")
                        with conf_col3:
                            st.metric("Minimum", f"{min_confidence:.3f}")
                else:
                    st.warning("⚠️ No PII detected in the text.")
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.info("Please check your input and try again.")
                st.exception(e)  # Show full error for debugging
    else:
        st.info("👈 Enter text on the left to see masked output here")
        st.markdown("""
        **Try these steps:**
        1. Click the "Load Example" button, or
        2. Type/paste your own text in the box
        3. Adjust settings in the sidebar
        4. See PII detection happen in real-time!
        
       
        """)

# Footer
st.markdown("---")
st.markdown("""
### 📚 About This Tool

This web interface uses **my pii_redact_v3.py functions** with an interactive Streamlit UI.

**Core Functions Used:**
- preprocess_text() - Text normalization
- mask_ner_multi()\ - NER-based masking with street filtering
- mask_regex() - Pattern-based detection (EMAIL, PHONE, SSN, ZIP)
- clean_and_filter_ents() - Confidence threshold filtering

**Detected Entity Types:**
- 👤 **PERSON**: Names of individuals (from NER)
- 📍 **LOCATION**: Cities, states, countries (from NER, optionally filter street names)
- 📧 **EMAIL**: Email addresses (from regex)
- 📞 **PHONE**: US phone numbers in various formats (from regex)
- 🔢 **SSN**: Social Security Numbers (from regex)
- 🏢 **ORGANIZATIONS** (optional): Company and organization names (from NER with --mask-org)
- 📮 **ZIP CODES** (optional): US postal codes (from regex with --mask-zip)

**Model:** dslim/bert-base-NER (BERT fine-tuned on CoNLL-2003)

**Created by:** Ana McCullagh | **Course:** CS314 Individualized Study | **Professor:** Manar Mohaisen
""")
