from typing import List
from coder.schemas import ExtractionOutput, SelectedCode, IgnoredContent
from coder.sanitizer import DisregardedSpan


def build_audit_trail(
    episode_id: str,
    extraction: ExtractionOutput,
    selection_codes: List[SelectedCode],
    sanitizer_disregarded: List[DisregardedSpan],
    validation_errors: List[str] = None
) -> str:
    notes_contributing = set()
    for sc in selection_codes:
        for q in sc.quotes:
            notes_contributing.add(q.note_index)
    
    for f in extraction.findings:
        if f.status in ["active", "confirmed"]:
            notes_contributing.add(f.note_index)
    
    notes_contributing = sorted(notes_contributing)
    
    all_disregarded = []
    for d in sanitizer_disregarded:
        all_disregarded.append(IgnoredContent(
            note_index=d.note_index,
            quote=d.quote,
            reason=d.reason
        ))
    for d in extraction.ignored_content:
        all_disregarded.append(d)
    
    disregarded_lines = []
    for d in all_disregarded:
        disregarded_lines.append(f"  - Note {d.note_index}: \"{d.quote[:100]}\" — {d.reason}")
    
    disregarded_text = "\n".join(disregarded_lines) if disregarded_lines else "  none"
    
    summary_parts = []
    
    if selection_codes:
        code_str = ", ".join([f"{sc.code}" for sc in selection_codes])
        summary_parts.append(f"Final code(s): {code_str}")
    else:
        summary_parts.append("Final code(s): no confident match")
    
    if extraction.findings:
        active_findings = [f for f in extraction.findings if f.status in ["active", "confirmed"]]
        ruled_out = [f for f in extraction.findings if f.status == "ruled_out"]
        superseded = [f for f in extraction.findings if f.status == "superseded"]
        pending = [f for f in extraction.findings if f.status == "pending_confirmation"]
        
        if active_findings:
            summary_parts.append(f"Active findings: {len(active_findings)}")
        if ruled_out:
            summary_parts.append(f"Ruled out: {len(ruled_out)} (e.g., {ruled_out[0].finding[:60]})")
        if superseded:
            summary_parts.append(f"Superseded: {len(superseded)}")
        if pending:
            summary_parts.append(f"Pending confirmation: {len(pending)}")
    
    if validation_errors:
        summary_parts.append(f"Validation issues: {len(validation_errors)} (confidence downgraded)")
    
    summary = " — ".join(summary_parts)
    
    audit = f"Notes contributing: {notes_contributing}\nDisregarded:\n{disregarded_text}\nSummary: {summary}"
    return audit


def format_evidence_for_output(selection_codes: List[SelectedCode]) -> List[dict]:
    evidence = []
    for sc in selection_codes:
        for q in sc.quotes:
            evidence.append({
                "code": sc.code,
                "quote": q.text,
                "note_index": q.note_index,
                "rationale": sc.rationale
            })
    return evidence