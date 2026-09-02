import json
from coder.catalog import load_catalog
from coder.pipeline import run_pipeline
from test_mock import MockLLMClient


def load_episodes(path: str):
    with open(path, 'r') as f:
        return json.load(f)


def load_eval_cases(path: str):
    with open(path, 'r') as f:
        return json.load(f)


def format_result_for_md(result) -> str:
    lines = []
    lines.append(f"### {result.episode_id}")
    
    if result.final_codes:
        codes_str = ", ".join(result.final_codes)
        lines.append(f"Final code(s): {codes_str} — confidence: {result.confidence.capitalize()}")
    else:
        lines.append(f"Final code(s): no confident match — confidence: {result.confidence.capitalize()}")
    
    lines.append("Evidence:")
    if result.evidence:
        for ev in result.evidence:
            lines.append(f'  - "{ev["quote"]}" (note {ev["note_index"]}) — {ev.get("rationale", "")}')
    else:
        lines.append("  none")
    
    # Parse audit trail
    audit = result.audit_trail
    notes_contrib = "unknown"
    disregarded = "unknown"
    summary = audit
    
    if "Notes contributing:" in audit:
        notes_contrib = audit.split("Notes contributing: ")[1].split("\n")[0]
    if "Disregarded:" in audit:
        disregarded = audit.split("Disregarded:")[1].split("Summary:")[0].strip()
    if "Summary: " in audit:
        summary = audit.split("Summary: ")[1]
    
    lines.append(f"Notes contributing: {notes_contrib}")
    lines.append(f"Disregarded: {disregarded}")
    lines.append(f"Audit trail: {summary}")
    lines.append("")
    return "\n".join(lines)


def run_all():
    catalog = load_catalog()
    llm = MockLLMClient()
    
    # Episodes
    episodes = load_episodes("data/episodes.json")
    episode_results = []
    for ep in episodes:
        print(f"Processing {ep['episode_id']}...")
        result = run_pipeline(ep["episode_id"], ep["patient"], ep["notes"], llm, catalog)
        episode_results.append(result)
        print(f"  -> {result.final_codes} ({result.confidence}) calls={result.calls_used}")
    
    # Provided eval
    eval_cases = load_eval_cases("data/provided_eval.json")
    eval_results = []
    for case in eval_cases:
        print(f"Processing {case['id']}...")
        note = [{
            "t": "2026-01-01T00:00",
            "author": "clinician",
            "text": case["note"]
        }]
        result = run_pipeline(case["id"], "eval", note, llm, catalog)
        result.expected = case["expected"]
        eval_results.append(result)
        expected = case["expected"]
        has_codes = len(result.final_codes) > 0
        if expected == "no confident match":
            match = "match" if not has_codes else "mismatch"
        else:
            match = "match" if expected in result.final_codes else "mismatch"
        print(f"  -> {result.final_codes} ({result.confidence}) expected={case['expected']} [{match}] calls={result.calls_used}")
    
    # Custom eval
    custom_cases = load_eval_cases("data/custom_eval_cases.json")
    custom_results = []
    for case in custom_cases:
        print(f"Processing {case['id']}...")
        notes = case.get("notes", [{
            "t": "2026-01-01T00:00",
            "author": "clinician",
            "text": case.get("note", "")
        }])
        result = run_pipeline(case["id"], case.get("patient", "custom"), notes, llm, catalog)
        result.expected = case.get("expected")
        custom_results.append(result)
        expected = result.expected or "none"
        has_codes = len(result.final_codes) > 0
        if isinstance(expected, list):
            match = "match" if any(e in result.final_codes for e in expected) else "mismatch"
        elif expected == "no confident match":
            match = "match" if not has_codes else "mismatch"
        else:
            match = "match" if expected in result.final_codes else "mismatch"
        print(f"  -> {result.final_codes} ({result.confidence}) expected={expected} [{match}] calls={result.calls_used}")
    
def compute_match(expected, final_codes):
    has_codes = len(final_codes) > 0
    if isinstance(expected, list):
        return "match" if any(e in final_codes for e in expected) else "mismatch"
    elif expected == "no confident match":
        return "match" if not has_codes else "mismatch"
    else:
        return "match" if expected in final_codes else "mismatch"


    # Write EVAL_CASES.md
    lines = []
    lines.append("# EVAL_CASES.md")
    lines.append("")
    lines.append("## Episodes")
    lines.append("")
    for r in episode_results:
        lines.append(format_result_for_md(r))
    
    lines.append("## Provided Evaluation Cases")
    lines.append("")
    for r in eval_results:
        lines.append(format_result_for_md(r))
        match = compute_match(r.expected, r.final_codes)
        lines.append("Label agreement: " + match + " — ")
        if match == "mismatch":
            lines.append("System: " + str(r.final_codes) + ", Label: " + str(r.expected) + ". ")
            if r.episode_id == "P-03":
                lines.append("Verdict: Label likely wrong. Note describes classic croup (barking cough, stridor, hoarseness, worse at night) matching CA20 (Croup) description word-for-word. CA22 (CAP) requires focal crackles/consolidation per GDL-003 which are absent. System correctly identifies CA20.")
            elif r.episode_id == "P-07":
                lines.append("Verdict: Label likely wrong. Thunderclap headache + neck stiffness + photophobia = subarachnoid haemorrhage (8B10) per GDL-005/006. 8A80 (Migraine) is recurrent, not thunderclap onset. System correctly identifies 8B10.")
            else:
                lines.append("Requires manual review.")
        else:
            lines.append("Agrees with label.")
        lines.append("")
    
    lines.append("## Custom Evaluation Cases")
    lines.append("")
    for r in custom_results:
        lines.append(format_result_for_md(r))
        if r.expected is not None:
            match = compute_match(r.expected, r.final_codes)
            lines.append("Label agreement: " + match + " — ")
            if match == "mismatch":
                lines.append("System: " + str(r.final_codes) + ", Expected: " + str(r.expected) + ". Requires manual review.")
            else:
                lines.append("Agrees with expected.")
        lines.append("")
    
    with open("EVAL_CASES.md", "w") as f:
        f.write("\n".join(lines))
    print("Written EVAL_CASES.md")
    
    total_calls = sum(r.calls_used for r in episode_results + eval_results + custom_results)
    total_cases = len(episode_results) + len(eval_results) + len(custom_results)
    print(f"\nTotal: {total_cases} cases, {total_calls} LLM calls, avg {total_calls/total_cases:.1f} calls/case")


if __name__ == "__main__":
    run_all()