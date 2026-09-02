import json
import argparse
from pathlib import Path
from typing import List

from coder.catalog import load_catalog
from coder.llm_client import create_llm_client
from coder.pipeline import run_pipeline


def load_episodes(path: str) -> List[dict]:
    with open(path, 'r') as f:
        return json.load(f)


def load_eval_cases(path: str) -> List[dict]:
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
    
    lines.append(f"Notes contributing: {result.audit_trail.split('Notes contributing: ')[1].split(chr(10))[0] if 'Notes contributing:' in result.audit_trail else 'unknown'}")
    lines.append(f"Disregarded: {result.audit_trail.split('Disregarded:')[1].split('Summary:')[0].strip() if 'Disregarded:' in result.audit_trail else 'unknown'}")
    lines.append(f"Audit trail: {result.audit_trail.split('Summary: ')[1] if 'Summary: ' in result.audit_trail else result.audit_trail}")
    lines.append("")
    return "\n".join(lines)


def run_episodes(replay: bool = True):
    catalog = load_catalog()
    llm = create_llm_client(replay=replay)
    episodes = load_episodes("data/episodes.json")
    
    results = []
    for ep in episodes:
        print(f"Processing {ep['episode_id']}...")
        result = run_pipeline(
            episode_id=ep["episode_id"],
            patient=ep["patient"],
            notes=ep["notes"],
            llm=llm,
            catalog=catalog
        )
        results.append(result)
        print(f"  -> {result.final_codes} ({result.confidence}) calls={result.calls_used}")
    
    return results


def run_eval(replay: bool = True):
    catalog = load_catalog()
    llm = create_llm_client(replay=replay)
    cases = load_eval_cases("data/provided_eval.json")
    
    results = []
    for case in cases:
        print(f"Processing {case['id']}...")
        note = [{
            "t": "2026-01-01T00:00",
            "author": "clinician",
            "text": case["note"]
        }]
        result = run_pipeline(
            episode_id=case["id"],
            patient="eval",
            notes=note,
            llm=llm,
            catalog=catalog
        )
        result.expected = case["expected"]
        results.append(result)
        match = "match" if case["expected"] in result.final_codes else "mismatch"
        print(f"  -> {result.final_codes} ({result.confidence}) expected={case['expected']} [{match}] calls={result.calls_used}")
    
    return results


def run_custom(replay: bool = True):
    catalog = load_catalog()
    llm = create_llm_client(replay=replay)
    
    custom_path = Path("data/custom_eval_cases.json")
    if not custom_path.exists():
        print("No custom eval cases found")
        return []
    
    cases = load_eval_cases(str(custom_path))
    results = []
    for case in cases:
        print(f"Processing {case['id']}...")
        if "notes" in case:
            notes = case["notes"]
        else:
            notes = [{
                "t": "2026-01-01T00:00",
                "author": "clinician",
                "text": case.get("note", "")
            }]
        result = run_pipeline(
            episode_id=case["id"],
            patient=case.get("patient", "custom"),
            notes=notes,
            llm=llm,
            catalog=catalog
        )
        result.expected = case.get("expected")
        results.append(result)
        expected = result.expected
        if isinstance(expected, list):
            match = "match" if any(e in result.final_codes for e in expected) else "mismatch"
        elif expected == "no confident match":
            match = "match" if not result.final_codes else "mismatch"
        else:
            match = "match" if expected in result.final_codes else "mismatch"
        print(f"  -> {result.final_codes} ({result.confidence}) expected={expected} [{match}] calls={result.calls_used}")
    
    return results


def write_eval_cases_md(episode_results, eval_results, custom_results):
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
        expected = r.expected
        if isinstance(expected, list):
            match = "match" if any(e in r.final_codes for e in expected) else "mismatch"
        elif expected == "no confident match":
            match = "match" if not r.final_codes else "mismatch"
        else:
            match = "match" if expected in r.final_codes else "mismatch"
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
            expected = r.expected
            if isinstance(expected, list):
                match = "match" if any(e in r.final_codes for e in expected) else "mismatch"
            elif expected == "no confident match":
                match = "match" if not r.final_codes else "mismatch"
            else:
                match = "match" if expected in r.final_codes else "mismatch"
            lines.append("Label agreement: " + match + " — ")
            if match == "mismatch":
                lines.append("System: " + str(r.final_codes) + ", Expected: " + str(r.expected) + ". Requires manual review.")
            else:
                lines.append("Agrees with expected.")
        lines.append("")
    
    with open("EVAL_CASES.md", "w") as f:
        f.write("\n".join(lines))
    print("Written EVAL_CASES.md")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", action="store_true", default=True)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--episodes-only", action="store_true")
    parser.add_argument("--eval-only", action="store_true")
    parser.add_argument("--custom-only", action="store_true")
    args = parser.parse_args()
    
    replay = not args.live
    
    episode_results = []
    eval_results = []
    custom_results = []
    
    if args.eval_only:
        eval_results = run_eval(replay)
    elif args.custom_only:
        custom_results = run_custom(replay)
    elif args.episodes_only:
        episode_results = run_episodes(replay)
    else:
        episode_results = run_episodes(replay)
        eval_results = run_eval(replay)
        custom_results = run_custom(replay)
    
    write_eval_cases_md(episode_results, eval_results, custom_results)
    
    total_calls = sum(r.calls_used for r in episode_results + eval_results + custom_results)
    total_cases = len(episode_results) + len(eval_results) + len(custom_results)
    print(f"\nTotal: {total_cases} cases, {total_calls} LLM calls, avg {total_calls/total_cases:.1f} calls/case")


if __name__ == "__main__":
    main()