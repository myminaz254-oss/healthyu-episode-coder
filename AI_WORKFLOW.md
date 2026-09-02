# AI Workflow Documentation

## 1. Context Management

**How did you manage context across the session?**

- **Single-session development**: All work done in one continuous session with incremental commits
- **Explicit context files**: `CLAUDE.md` (agent instructions), `BUILD_PLAN.md` (detailed spec), `PROGRESS_LOG.md` (timestamped steps) served as persistent context anchors
- **Modular file structure**: Each module (`coder/*.py`) is self-contained with clear interfaces, reducing cross-file context needs
- **Test-driven verification**: Tests (`coder/tests/*.py`) encode expected behavior, allowing AI to verify changes without re-reading full spec
- **Data-first approach**: AI was instructed to read all 4 JSON data files first (catalog, guidelines, episodes, eval) before any coding — this grounded all subsequent work in actual data, not assumptions

**Key practice**: After every meaningful step, AI appended to `PROGRESS_LOG.md`, creating a linear history that both human and AI could reference.

## 2. Planning Before Code

**Did you plan before writing code? How?**

Yes, extensively. The `BUILD_PLAN.md` (provided in brief) served as the master plan with:
- 10 numbered build steps with explicit commit points
- Data inspection findings (§1) that drove design decisions
- Explicit non-goals to prevent over-engineering
- Schema definitions for LLM I/O
- Exact prompt templates

**Planning artifacts created before code**:
1. `CLAUDE.md` + `PROGRESS_LOG.md` (agent setup)
2. Repository scaffold + data copy
3. `requirements.txt`
4. All test files written *before* implementation (test_catalog_validation.py, test_sanitizer.py)
5. Schemas (`schemas.py`) and prompts (`prompts.py`) defined before pipeline

**AI's role**: AI executed the plan step-by-step, but the plan itself was human-authored (from BUILD_PLAN.md). AI did not "plan" in the strategic sense — it implemented a pre-specified architecture.

## 3. Verification

**How did you verify the AI's work? What's one concrete mistake you caught?**

**Verification methods**:
- **Unit tests**: 7 tests passing (catalog validation, sanitizer, etc.)
- **Mock evaluation run**: 22 cases executed end-to-end with deterministic mock LLM
- **Output inspection**: `EVAL_CASES.md` manually reviewed for clinical correctness
- **Regression checks**: Re-running after each fix to ensure no regressions

**Concrete caught mistake**: 
> **Critical code sanity filter feature mismatch** (validators.py)
> 
> The AI initially implemented `CRITICAL_CODES["1D91"].required_features` with semantic terms like `"hypotension"`, `"tachycardia"`, `"reduced urine"`, `"oliguria"`. However, the actual episode notes contain `"BP 86/54"`, `"HR 128"`, `"urine output poor since morning"` — the validator does substring matching on verbatim quotes, so semantic terms never matched.
> 
> **Result**: `1D91` (Sepsis) was incorrectly rejected on EP-06 and C-02 despite strong clinical evidence.
> 
> **Fix**: Human updated `required_features` to include the actual substrings from notes: `"bp 86/54"`, `"86/54"`, `"hr 128"`, `"128"`, `"urine output poor"`, `"poor since morning"`. This is a case where AI's "semantic" thinking diverged from the system's "exact substring" validation contract.

## 4. Tool & Model Routing

**How did you route tasks between tools/models?**

| Task | Tool/Model | Rationale |
|------|------------|-----------|
| Data inspection (catalog, guidelines, episodes) | Human + AI (read) | Required human judgment on clinical nuances |
| Architecture design | Human (BUILD_PLAN.md) | Strategic decisions need human ownership |
| Module implementation | AI (Claude Code / Sonnet 4) | Well-scoped, testable units |
| Prompt engineering | Human + AI iterative | Human defined constraints; AI drafted templates |
| Mock response crafting | AI (with human correction) | 22 cases × 2-3 calls = 44+ responses; AI efficient but needed clinical accuracy checks |
| Test writing | AI (test-first) | AI excels at boilerplate test structure |
| Documentation | AI (draft) + Human (review) | AI fast at formatting; human verifies accuracy |
| Git commits | Human | Explicit commit control per brief |

**Model choice**: Single model (Sonnet 4) for all coding tasks. No routing between models — the task scope fit one strong model. Temperature=0 for reproducibility.

## 5. Deliberate Non-Delegation

**What did you deliberately NOT delegate to AI?**

1. **Clinical escalation rule interpretation** — The distinction between GDL-007 ("not simple cystitis" = replace) and GDL-017 ("rather than localized infection code alone" = additive) required reading guideline text in clinical context. AI tends to flatten nuances.

2. **Confirmation level policy** — Deciding that `1C12.1` (bacteriologically confirmed TB) requires positive GeneXpert while `1C12` (clinical TB) is acceptable as presumptive was a clinical judgment call with grading implications.

3. **Injection detection threshold** — Choosing ≥3 signals (system pattern + imperative + addressed-to-system) balanced false positives on patient speech (C-01) vs true injections (EP-03). AI proposed simpler keyword matching which would over-flag.

4. **Custom adversarial cases** — All 5 cases (C-01 to C-05) were human-designed to target specific known weaknesses: injection false positive, escalation generalization, ectopic exclusion, catalog gap, noisy vitals.

5. **Label disagreement verdicts** — P-03 (Croup vs CAP) and P-07 (SAH vs Migraine) required human clinical reasoning to defend against provided labels.

6. **Repository structure & commit discipline** — Following BUILD_PLAN.md's numbered steps, incremental commits, no squash/rebase per brief requirements.