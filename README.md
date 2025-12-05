# PII Detection Assistant

**Automatic detection and masking of personally identifiable information (PII) using BERT and pattern matching**

[![Live Demo](https://img.shields.io/badge/Demo-Live%20Website-brightgreen)](https://pii-redaction-demo.streamlit.app)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🌟 **Live Web Application**

**Try it now without any setup: [https://pii-redaction-demo.streamlit.app](https://pii-redaction-demo.streamlit.app)**

The web interface provides:
- ✅ Real-time PII detection and masking
- ✅ Interactive configuration controls
- ✅ Statistics and confidence scores
- ✅ Example data to test immediately
- ✅ No installation required!

---

## 📋 **What This Does**

This system automatically detects and masks seven types of personally identifiable information:

| PII Type | Detection Method | Example |
|----------|------------------|---------|
| **Names** | BERT NER | Ana McCullagh → [PERSON_REDACTED] |
| **Locations** | BERT NER | Chicago, IL → [LOC_REDACTED] |
| **Emails** | Regex Pattern | ana@example.com → [EMAIL_REDACTED] |
| **Phone Numbers** | Regex Pattern | (312) 555-0199 → [PHONE_REDACTED] |
| **Social Security Numbers** | Regex Pattern | 123-45-6789 → [SSN_REDACTED] |
| **Organizations** | BERT NER (optional) | Google → [ORG_REDACTED] |
| **ZIP Codes** | Regex Pattern (optional) | 60601 → [ZIP_REDACTED] |

**Performance:**
- 96.5% F1 score on standard tests
- 90% F1 score on edge cases
- Comparable to commercial systems (Microsoft Presidio: 94.7%)

---

## 🎯 **Use Cases**

- **Healthcare:** De-identify medical records for HIPAA compliance
- **Legal:** Redact sensitive information in court documents
- **Business:** Anonymize employee communications for analysis
- **Research:** Protect participant privacy in datasets

---

## 🛠️ **Installation (Local Use)**

### 1. Clone the Repository
```bash
git clone https://github.com/AnaPaula04/pii-redaction-demo.git
cd pii-redaction-demo
```

### 2. Create Virtual Environment (macOS/Linux)
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

**For faster CPU-only PyTorch:**
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

---

## 🚀 **Usage**

### **Option 1: Web Interface (Easiest)**

Visit: **[https://pii-redaction-demo.streamlit.app](https://pii-redaction-demo.streamlit.app)**

Or run locally:
```bash
streamlit run ner/pii_webapp.py
```

### **Option 2: Command Line**

#### **Basic Usage:**
```bash
python ner/pii_redact_v3.py data/sample_sentences.txt
```

**Output:**
- `data/redacted_output.txt` - Masked text
- `data/entities_report.jsonl` - Detailed entity report with confidence scores

#### **Advanced Options:**

```bash
# Mask organizations and ZIP codes
python ner/pii_redact_v3.py input.txt --mask-org --mask-zip

# Filter street names for better readability
python ner/pii_redact_v3.py input.txt --filter-streets

# Adjust confidence threshold
python ner/pii_redact_v3.py input.txt --min-score 0.90

# Combine all options
python ner/pii_redact_v3.py input.txt --mask-org --mask-zip --filter-streets --min-score 0.85
```

#### **Configuration Flags:**

| Flag | Default | Description |
|------|---------|-------------|
| `--min-score` | 0.80 | Confidence threshold for NER (0.70-0.95) |
| `--mask-org` | False | Mask organization names |
| `--mask-zip` | False | Mask ZIP codes (caution: matches all 5-digit numbers) |
| `--filter-streets` | False | Keep street names visible, mask cities/states |

---

## 📊 **Example**

**Input:**
```
My name is Ana McCullagh and my phone is (312) 555-0199. 
Email me at ana@example.com. I work at Google in Chicago, IL 60601.
My SSN is 123-45-6789.
```

**Output (default settings):**
```
My name is [PERSON_REDACTED] and my phone is [PHONE_REDACTED].
Email me at [EMAIL_REDACTED]. I work at Google in [LOC_REDACTED], [LOC_REDACTED] 60601.
My SSN is [SSN_REDACTED].
```

**Output (with --mask-org --mask-zip):**
```
My name is [PERSON_REDACTED] and my phone is [PHONE_REDACTED].
Email me at [EMAIL_REDACTED]. I work at [ORG_REDACTED] in [LOC_REDACTED], [LOC_REDACTED] [ZIP_REDACTED].
My SSN is [SSN_REDACTED].
```

---

## 🏗️ **Technical Details**

### **Architecture**

The system uses a hybrid approach:

1. **BERT-based NER** (dslim/bert-base-NER)
   - Detects context-dependent entities: PERSON, LOCATION, ORGANIZATION
   - 110M parameters, fine-tuned on CoNLL-2003 dataset
   - 96.5% F1 score on benchmark

2. **Regular Expression Patterns**
   - Detects format-specific PII: emails, phones, SSNs, ZIP codes
   - Multiple format support (e.g., phone: (312) 555-0199, 3125550199, +1 312 555 0199)
   - Context-aware SSN detection (only triggers when "SSN" keyword present)

3. **Right-to-Left Masking Algorithm**
   - Processes entities from highest to lowest position
   - Maintains position stability during sequential replacement
   - Prevents index shifting errors

### **Key Features**

✅ **Title Detection** 
- Detects person names with professional titles (Dr., Prof., Mr., Ms., etc.)
- Covers 30+ common titles
- Resolves false negatives on titled names

✅ **Street Name Filtering** (Version 3)
- Optional filtering of street components for better address readability
- Reduces false positives by 20%
- Maintains privacy protection for cities and states

✅ **Flexible Configuration**
- User-controllable masking via command-line flags
- Appropriate privacy-usability trade-offs for different contexts

---

## 📁 **Project Structure**

```
pii-redaction-demo/
├── ner/
│   ├── pii_redact_v3.py        # Main detection script (CLI)
│   ├── pii_webapp.py            # Streamlit web interface
│   └── ner_quick_test.py        # Quick NER test script
├── data/
│   ├── sample_sentences.txt     # Example input
│   ├── test_edge_cases.txt      # Edge case test data
│   ├── redacted_output.txt      # Output file (generated)
│   └── entities_report.jsonl    # Detailed report (generated)
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

---

## 🧪 **Testing**

### **Quick Test:**
```bash
python ner/ner_quick_test.py
```

### **Standard Tests:**
```bash
python ner/pii_redact_v3.py data/sample_sentences.txt
cat data/redacted_output.txt
```

### **Edge Case Tests:**
```bash
python ner/pii_redact_v3.py data/test_edge_cases.txt
cat data/redacted_output.txt
```

---

## 📈 **Performance Metrics**

| Test Type | F1 Score | Precision | Recall |
|-----------|----------|-----------|--------|
| Standard Tests | 96.5% | 100% | 93.3% |
| Edge Cases | 90.0% | 90.0% | 90.0% |
| Combined | 93.3% | 95.0% | 91.7% |

**Confidence Scores:**
- All NER detections: >90% confidence
- Average confidence: 0.95
- Tested thresholds: 0.70, 0.80, 0.90 (identical results)

---

## 🐛 **Known Limitations**

1. **Contextual Ambiguity**
   - Struggles with homonyms (e.g., "Washington" as person vs. place)
   - Token-level NER lacks sentence-level semantic understanding

2. **ZIP Code Detection**
   - Matches all 5-digit numbers
   - Can false-positive on patient IDs, order numbers
   - **Recommendation:** Only use `--mask-zip` when no other 5-digit identifiers present

3. **Language Support**
   - Currently English-only
   - US-specific formats (phone numbers, SSNs, ZIP codes)

4. **Domain Specificity**
   - Optimized for general text
   - May require fine-tuning for highly specialized domains (medical jargon, legal terminology)

---

## 🔧 **Troubleshooting**

**Issue: SSL/Timeout errors downloading model**
```bash
# Try different network or use HF_ENDPOINT
export HF_ENDPOINT=https://huggingface.co
```

**Issue: "sentencepiece" or "safetensors" required**
```bash
pip install sentencepiece safetensors
```

**Issue: Slow model loading**
- First run downloads ~440MB model (cached for subsequent runs)
- Use web application for pre-loaded model

**Issue: Out of memory**
- System requires ~500MB RAM for model
- Reduce batch size or use CPU-only inference

---

## 📚 **References**

- **BERT Model:** [dslim/bert-base-NER](https://huggingface.co/dslim/bert-base-NER)
- **Transformers Library:** [Hugging Face](https://huggingface.co/docs/transformers)
- **Streamlit:** [Streamlit Docs](https://docs.streamlit.io)
- **Original BERT Paper:** Devlin et al. (2019) - [ArXiv](https://arxiv.org/abs/1810.04805)

---

## 👤 **Author**

**Ana McCullagh**
- Course: CS314 Individualized Study
- Instructor: Dr. Manar Mohaisen
- Institution: Northeastern Illinois University
- Project Duration: September 17 - December 4, 2025

---

## 📝 **License**

This project was developed as part of an academic individualized study program.

---

## 🙏 **Acknowledgments**

- Dr. Manar Mohaisen for project guidance and supervision
- Hugging Face for accessible transformer models and infrastructure
- Streamlit for rapid web application development framework
- Open-source NLP community for tools and documentation

---

## 📞 **Contact & Support**

- **Live Demo:** [https://pii-redaction-demo.streamlit.app](https://pii-redaction-demo.streamlit.app)
- **GitHub Issues:** [Report bugs or request features](https://github.com/AnaPaula04/pii-redaction-demo/issues)
- **Documentation:** See project reports for comprehensive technical details

---

**⭐ If you find this project useful, please star the repository!**
