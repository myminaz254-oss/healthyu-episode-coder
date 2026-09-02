from typing import List
from coder.catalog import ICDCode
from coder.schemas import SelectedCode, ExtractionOutput
from coder.validators import ValidationResult


def compute_confidence(
    selected_codes: List[SelectedCode],
    extraction: ExtractionOutput,
    catalog_codes: List[ICDCode],
    validation: ValidationResult,
    retrieval_margin: float = 0.0
) -> str:
    if not selected_codes:
        return "none"
    
    if not validation.is_valid:
        return "low"
    
    high_confidence_count = 0
    medium_confidence_count = 0
    
    for sc in selected_codes:
        code_obj = next((c for c in catalog_codes if c.code == sc.code), None)
        if not code_obj:
            medium_confidence_count += 1
            continue
        
        evidence_text = " ".join([q.text.lower() for q in sc.quotes])
        
        code_keywords = set((code_obj.title + " " + code_obj.description).lower().split())
        evidence_keywords = set(evidence_text.split())
        overlap = code_keywords & evidence_keywords
        meaningful_overlap = {w for w in overlap if len(w) > 4}
        
        cardinal_features_present = len(meaningful_overlap) >= 3
        
        has_conflicting = any(
            f.status in ["ruled_out", "superseded"] and any(kw in f.finding.lower() for kw in meaningful_overlap)
            for f in extraction.findings
        )
        
        has_pending_confirmation = any(
            f.status == "pending_confirmation" and any(kw in f.finding.lower() for kw in meaningful_overlap)
            for f in extraction.findings
        )
        
        code_text = f"{code_obj.title} {code_obj.description}".lower()
        requires_confirmation = any(term in code_text for term in ["confirmed", "bacteriologically confirmed"])
        confirmation_matches = not (requires_confirmation and has_pending_confirmation)
        
        if cardinal_features_present and not has_conflicting and confirmation_matches and retrieval_margin > 0.15:
            high_confidence_count += 1
        elif cardinal_features_present or (meaningful_overlap and not has_conflicting):
            medium_confidence_count += 1
        else:
            medium_confidence_count += 1
    
    if high_confidence_count == len(selected_codes) and high_confidence_count > 0:
        return "high"
    elif medium_confidence_count > 0:
        return "medium"
    else:
        return "low"