# How Field Detection Works

This document explains the field detection system in AI E-Sign and how to improve its accuracy.

## Overview

The field detection system uses a **hybrid approach** combining multiple strategies to identify form fields in PDF documents. This provides better coverage than any single method alone.

## Detection Strategies

### 1. Underline Detection

**What it finds:** Horizontal lines that indicate fill-in blanks

**How it works:**
1. Extract vector graphics (drawings) from PDF
2. Find horizontal line segments (y-values within 2px)
3. Filter by minimum width (>50px)
4. Look for nearby text labels above/left of the line
5. Classify based on label keywords

**Confidence factors:**
- Higher if nearby label found
- Higher if label contains recognizable keyword
- Lower for orphan underlines

**Example patterns detected:**
- `Name: ________________`
- `Signature: ____________`
- Lines under "Date:" labels

### 2. Checkbox Detection

**What it finds:** Small square shapes and checkbox characters

**How it works:**
1. Check for PDF form widgets (AcroForm checkboxes)
2. Find small rectangular drawings (8-25px squares)
3. Search for Unicode checkbox characters (☐ ☑ ☒ □)
4. Position field at checkbox location

**Confidence factors:**
- Highest for PDF form widgets (0.95)
- High for checkbox characters (0.90)
- Medium for square drawings (0.70)

### 3. Keyword-Based Detection

**What it finds:** Fields based on label text

**How it works:**
1. Extract all text lines with bounding boxes
2. Search for keyword patterns
3. Position field adjacent to keyword
4. Classify and assign owner based on context

**Keyword categories:**

| Field Type | Keywords |
|------------|----------|
| SIGNATURE | signature, sign here, authorized signature |
| DATE_SIGNED | date, dated, date signed, effective date |
| NAME | name, print name, full name |
| EMAIL | email, e-mail, email address |
| INITIALS | initials, initial here |

### 4. Anchor Tag Detection

**What it finds:** Explicit field markers in format `[type|role]`

**How it works:**
1. Search text for pattern `\[(\w+)\|(\w+)\]`
2. Parse field type and role from groups
3. Position field at tag location
4. Remove tag text (optional in final render)

**Supported tags:**
- `[sig|signer1]` - Signature for Signer 1
- `[date|signer2]` - Date for Signer 2
- `[name|sender]` - Name (sender-filled)
- `[email|signer1]` - Email for Signer 1
- `[check|signer1]` - Checkbox for Signer 1
- `[init|signer2]` - Initials for Signer 2

### 5. Sender Variable Detection

**What it finds:** Merge field placeholders `{{variable_name}}`

**How it works:**
1. Search for pattern `\{\{(\w+)\}\}`
2. Create TEXT field owned by SENDER
3. Variable key stored for send-time merge

## Owner Inference

Determining which party should fill a field is challenging. The system uses contextual keywords:

**Signer 1 indicators:**
- client, employee, contractor, tenant, buyer
- recipient, party a, first party, borrower

**Signer 2 indicators:**
- company, employer, landlord, seller
- provider, party b, second party, lender

**Default:** If no indicator found, defaults to SIGNER_1

## Confidence Scores

Each detected field includes three confidence scores (0.0 - 1.0):

1. **detection_confidence:** Likelihood this is actually a field
   - Based on detection method reliability
   - Affected by pattern clarity

2. **classification_confidence:** Likelihood the type is correct
   - Based on keyword match strength
   - Higher for exact matches

3. **owner_confidence:** Likelihood the owner assignment is correct
   - Based on contextual keyword proximity
   - Lower when context is ambiguous

## Improving Accuracy

### For Document Creators

1. **Use anchor tags** for highest accuracy: `[sig|signer1]`
2. **Clear labels** near fields: "Client Signature:" not just a line
3. **Consistent terminology** throughout document
4. **Standard checkbox characters** (☐) instead of brackets []

### For System Improvements

1. **Add keywords** to detection categories:
   ```python
   # In detector.py
   SIGNATURE_KEYWORDS = [
       "signature", "sign here", ...
       # Add new patterns
       "your signature", "autograph"
   ]
   ```

2. **Adjust confidence thresholds** in config:
   ```python
   detection_confidence_threshold: float = 0.5  # Lower = more fields
   ```

3. **Improve owner inference** with document structure:
   - Detect signature blocks by layout
   - Use page position (top = party 1, bottom = party 2)

4. **Add ML/LLM classification** (future):
   - Send uncertain fields to LLM for classification
   - Train custom model on labeled documents

## Evaluation

Run the evaluation script to measure accuracy:

```bash
cd scripts
python evaluate_field_detection.py
```

This computes:
- **Detection recall:** % of actual fields found
- **Type accuracy:** % correctly classified
- **Owner accuracy:** % correctly assigned

### Acceptance Criteria

| Metric | Target | Description |
|--------|--------|-------------|
| Detection Recall | ≥80% | Find most obvious fields |
| Type Accuracy | ≥80% | Correctly classify found fields |
| Owner Accuracy | ≥70% | Correctly assign owner (harder) |

## Troubleshooting

### Field Not Detected

1. Check if PDF has vector underlines (some use images)
2. Verify label text is extractable (not scanned image)
3. Try adding anchor tag explicitly

### Wrong Classification

1. Check nearby text for conflicting keywords
2. Review evidence string for why it chose that type
3. Consider adding more specific keywords

### Wrong Owner

1. Add party-specific language near field
2. Use anchor tags for explicit assignment
3. Check if document uses non-standard terminology

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    PDF Document                      │
└─────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│                 Detection Pipeline                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │Underline │ │Checkbox  │ │ Keyword  │ │ Anchor │ │
│  │ Detector │ │ Detector │ │ Detector │ │Detector│ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └───┬────┘ │
│       │            │            │            │      │
│       └────────────┴────────────┴────────────┘      │
│                          │                          │
│                          ▼                          │
│              ┌─────────────────────┐                │
│              │   Deduplication     │                │
│              │   & Filtering       │                │
│              └─────────────────────┘                │
└─────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌─────────────────────┐
              │  Detected Fields    │
              │  with Confidence    │
              └─────────────────────┘
```
