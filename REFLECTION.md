# Reflection

## What changes at 50,000 codes?

### Retrieval Architecture
**Current**: Flat lexical scan over 288 codes (O(n) token overlap + fuzzy match) — sufficient and fully offline.
**At 50k**: Flat scan becomes latency bottleneck (~100-500ms per episode). Would need:
- **Embedding-based ANN index** (FAISS, HNSW) for sub-10ms candidate retrieval
- **Hierarchical catalog navigation**: Chapter → Block → Code (ICD-10 structure) to narrow search space
- **Two-stage retrieval**: Coarse embedding filter → fine lexical re-rank
- **Offline constraint tension**: Embeddings require model + index artifacts; still offline-reproducible but larger commit size

### Guideline Coverage & Maintenance
**Current**: 30 guidelines for 288 codes (10% coverage), manually cross-validated at load time.
**At 50k**: 
- Guideline density drops → most codes lack explicit guidance
- **Automated guideline generation** from code descriptions + clinical literature becomes necessary
- **Conflict detection** scales quadratically — need automated consistency checking (embedding similarity between guideline text and linked code descriptions)
- **Versioning**: Guidelines must be versioned with catalog releases; breaking changes tracked

### Critical-Code Sanity Filter
**Current**: 4 hardcoded codes (BA41, 1D91, 1A00, 1D00) with manual feature lists.
**At 50k**:
- **Impossible to hand-curate** — thousands of high-stakes codes (MI, stroke, sepsis, aortic dissection, etc.)
- **Solution**: Derive minimum evidence rules from code descriptions + guideline text automatically
  - Parse "requires X, Y, Z" patterns from descriptions
  - Use LLM to generate evidence checklists per code at catalog build time
  - Store as structured rules (not hardcoded Python)

### Confirmation Level Logic
**Current**: String matching for "confirmed"/"bacteriologically confirmed" in title/description.
**At 50k**:
- **Standardized metadata field** in catalog: `confirmation_required: true/false`, `confirmatory_tests: ["GeneXpert", "culture", "PCR"]`
- **Structured validation**: Look up required test types per code, verify documented positive result in findings

### Escalation Rule Engine
**Current**: Two hardcoded patterns ("not X" = replace, "rather than X alone" = additive).
**At 50k**:
- **Formal escalation ontology**: `replaces: [code]`, `additive_with: [code]`, `excludes: [code]` as catalog metadata
- **Guideline parser** extracts these relations automatically
- **Conflict resolution**: When multiple guidelines apply, use specificity hierarchy

### Call Budget Pressure
**Current**: 2-3 calls sufficient with 288 codes (retrieval narrows candidates well).
**At 50k**: 
- Retrieval returns more candidates → longer context for Call 2
- May need **Call 2a (candidate pruning)** + **Call 2b (final selection)** → risks exceeding budget
- **Mitigation**: Better retrieval precision (embeddings + re-ranking) keeps candidate set small; structured candidate format (code + score + matched features) reduces token count

---

## What changes when notes are handwritten/photographed?

### OCR Error Profile Dominates
**Current**: Typos/misspellings (travelld, kikohozi) handled by fuzzy match + glossary.
**Handwritten**: 
- **Character-level errors**: "38.9" → "38.3" (temp), "BA41" → "BA11" (code-like artifacts)
- **Line segmentation errors**: Multi-column layouts read in wrong order
- **Missing text**: Faded ink, fold lines, coffee stains
- **Glossary failure**: "homa" handwritten may not OCR to any recognizable token

**Implications**:
- **Confidence scores per OCR span**: Each extracted text segment needs confidence (Tesseract/Google Vision provide this)
- **Downstream weighting**: Low-confidence OCR spans contribute less to retrieval/matching
- **Span-level audit**: Track which quotes came from low-confidence OCR regions

### Injection Resistance Harder
**Current**: Injection detected via linguistic patterns in clean text.
**Handwritten**: 
- **OCR mangles injection text**: "NOTE TO CODING SYSTEM" → "NOTE TO CODING SYS TEM" — pattern matching degrades
- **Visual injection**: Handwritten "CODE AS MI" in margin — not in OCR text stream but visible to multimodal model
- **Adversarial handwriting**: Deliberately ambiguous characters that OCR reads as directive

**Implications**:
- **Multimodal input required**: Feed image + OCR text to LLM; let model reason about visual context
- **Sanitizer becomes probabilistic**: Flag low-confidence OCR spans that *could* be directives
- **Human-in-the-loop**: High-stakes codes (BA41, 1D91) from photographed notes require clinician verification

### Evidence Quoting Contract Breaks
**Current**: Quote must be exact substring of note text (deterministic validation).
**Handwritten**: 
- **No ground truth string**: OCR output is best-effort; "exact substring" is meaningless
- **Validation changes**: Quote must be *consistent with* OCR span (allowing OCR error tolerance) + traceable to image region
- **Audit trail**: Must reference image coordinates (page, x, y, w, h) not just note index

### New Pipeline Stages Needed
1. **OCR + Layout Analysis** (deterministic, offline): Textract/Google Vision/Tesseract → structured blocks with confidence
2. **Visual Sanitizer** (multimodal LLM): Detect marginalia, circled text, arrows, "CODE AS X" annotations
3. **Span Confidence Propagation**: OCR confidence → retrieval weight → final code confidence
4. **Image-Evidence Linking**: Final codes reference image regions for human review

### Offline Replay Complication
**Current**: Cache stores (prompt, response) pairs; fully deterministic.
**Handwritten**: 
- **OCR is non-deterministic** across versions (engine updates change output)
- **Must commit OCR output** as part of cache (not just LLM responses)
- **Multimodal cache keys**: Include image hash + OCR version
- **Reproducibility**: Requires pinning OCR engine version + model version

---

## Summary

| Dimension | 288 codes, typed notes | 50,000 codes, photographed notes |
|-----------|------------------------|----------------------------------|
| Retrieval | Lexical scan (fast enough) | Embedding ANN + hierarchical |
| Guidelines | Manual cross-validation | Auto-generated + versioned |
| Safety filters | Hand-curated (4 codes) | Auto-derived from metadata |
| Confirmation | String search | Structured metadata field |
| Escalation | 2 hardcoded patterns | Ontology in catalog |
| OCR | N/A | Core pipeline stage |
| Quote validation | Exact substring | Confidence-weighted + image trace |
| Cache | Prompt+response | Image+OCR+prompt+response |
| Human review | Audit trail only | Required for high-stakes codes |

The core architecture (deterministic layers + bounded LLM calls + validation + audit) remains sound, but every component needs to scale from "hand-coded for 288" to "metadata-driven for 50k" and from "text-only" to "multimodal with uncertainty propagation."