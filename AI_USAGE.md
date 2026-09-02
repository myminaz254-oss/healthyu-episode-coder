# AI Usage Documentation

## Overview
This project was developed with extensive AI assistance (Claude Code / Sonnet 4). The AI was used as a pair programmer for implementation, testing, and documentation.

## AI Contributions by Component

### Code Generation (≈85% of implementation)
- **All Python modules**: `coder/glossary.py`, `sanitizer.py`, `catalog.py`, `retrieval.py`, `schemas.py`, `prompts.py`, `llm_client.py`, `validators.py`, `confidence.py`, `audit.py`, `pipeline.py`, `main.py`
- **Test files**: `test_catalog_validation.py`, `test_sanitizer.py`
- **Mock client**: `test_mock.py` for offline evaluation
- **Evaluation runner**: `run_eval_mock.py`, `write_eval.py`

### Design & Architecture (≈70% human-directed, 30% AI-suggested)
- **Human decisions**: Pipeline architecture (3-call budget), deterministic layers, validation rules, escalation parsing, confidence rubric, injection resistance strategy, catalog-gap handling
- **AI suggestions**: Pydantic schemas, prompt templating, cache key design, critical-code sanity filter patterns

### Debugging & Verification (≈60% AI-assisted)
- Test development for catalog validation, sanitizer edge cases
- Mock response crafting for all 22 test cases
- Iterative fixes for quote validation, critical code feature matching
- EVAL_CASES.md generation and formatting

### Documentation (≈90% AI-drafted, human-reviewed)
- README.md, AI_USAGE.md, AI_WORKFLOW.md, REFLECTION.md
- Inline code comments (minimal, per ponytail)
- Progress log entries

## Human Oversight & Corrections

### Caught AI Mistakes (concrete examples)

1. **Guideline count assertion**: AI wrote test asserting 30 guidelines; actual count is 31 (JB00-note). Human caught and fixed test.

2. **Mock quote validation**: AI-generated mock responses used paraphrased quotes not present in original notes. Human identified validator failures and corrected mock quotes to exact substrings.

3. **Critical code feature matching**: AI used semantic features ("hypotension", "tachycardia") not present in note text ("BP 86/54", "HR 128"). Human updated feature list to match actual substrings.

4. **C-03a expected value**: AI initially set expected=`JB00` for "no pregnancy test" case; human corrected to "no confident match" per JB00-note guideline logic.

4. **C-04 comparison logic**: AI compared string "no confident match" against empty code list incorrectly. Human fixed `compute_match` to handle this case.

5. **EP-06 sepsis code**: AI mock initially returned only `1C60`; validator rejected `1D91` due to quote mismatch. Human corrected mock quotes and critical features.

### Decisions NOT Delegated to AI

- **Escalation rule semantics**: Human defined "not X"=replace vs "rather than X alone"=additive based on guideline text analysis
- **Confirmation level policy**: Human decided `1C12.1` never without positive test; `1C12` acceptable as presumptive
- **Injection detection threshold**: Human chose ≥3 signals to balance false positives
- **Confidence rubric thresholds**: Human calibrated based on clinical coding principles
- **Custom eval case design**: Human authored all 5 adversarial cases targeting specific weaknesses

## Prompt Engineering

**Call 1 (Extraction)**: Strict JSON schema, explicit instruction to ignore system directives, status enum for temporal tracking

**Call 2 (Selection)**: Catalog + guidelines + original notes provided; escalation rules embedded in system prompt; verbatim quote requirement emphasized

**Call 3 (Repair)**: Only validation errors fed back; same schema; no infinite loop (max 3 calls)

**Temperature**: 0 (deterministic)

**Model**: claude-3-5-sonnet-20241022 (configured, mocked for evaluation)

## Cache & Reproducibility

- All LLM responses cached to `cache/responses/` with deterministic keys
- `--replay` mode runs entirely offline (no API key, no network)
- Committed cache enables exact reproduction by graders
- Mock client used for this submission's evaluation run

## Time Investment

- **Total**: ~2.5 hours
- **AI-assisted coding**: ~2 hours
- **Human review/debug/design**: ~0.5 hours