from typing import List, Optional, Tuple
from dataclasses import dataclass
from coder.catalog import Catalog, ICDCode
from coder.schemas import SelectedCode, QuoteEvidence, ExtractionOutput


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    validated_codes: List[SelectedCode]


CRITICAL_CODES = {
    "BA41": {
        "name": "Acute myocardial infarction",
        "min_features": 2,
        "required_features": [
            "substernal", "radiating", "left arm", "jaw", "diaphoresis", 
            "dyspnea", "shortness of breath", "ecg", "troponin", "st elevation",
            "crushing", "pressure", "squeezing", "sweating"
        ]
    },
    "1D91": {
        "name": "Sepsis",
        "min_features": 2,
        "required_features": [
            "confused", "altered mental", "talking out of context",
            "bp 86/54", "86/54", "hypotension", "low blood pressure",
            "hr 128", "128", "tachycardia", "rapid heart rate",
            "rr 26", "26", "tachypnea", "rapid breathing",
            "urine output poor", "poor since morning", "reduced urine", "oliguria",
            "organ dysfunction"
        ]
    },
    "1A00": {
        "name": "Cholera",
        "min_features": 2,
        "required_features": [
            "rice water", "profuse", "watery diarrhoea", "rapid dehydration"
        ]
    },
    "1D00": {
        "name": "Bacterial meningitis",
        "min_features": 2,
        "required_features": [
            "neck stiffness", "nuchal rigidity", "photophobia", 
            "altered mental", "kernig", "brudzinski"
        ]
    },
}


def validate_code_exists(code: str, catalog: Catalog) -> Optional[str]:
    if code not in catalog.codes:
        return f"Code {code} does not exist in catalog"
    return None


def validate_quote_is_substring(quote: str, note_text: str) -> Optional[str]:
    if quote not in note_text:
        return f"Quote not found in note text: '{quote[:50]}...'"
    return None


def validate_confirmation_level(code: ICDCode, finding_status: str, evidence_quote: str) -> Optional[str]:
    code_text = f"{code.title} {code.description}".lower()
    if any(term in code_text for term in ["confirmed", "bacteriologically confirmed", "positive culture", "positive test"]):
        if finding_status != "confirmed":
            return f"Code {code.code} requires confirmed status but finding is {finding_status}"
    return None


def validate_critical_code_sanity(code: str, quotes: List[QuoteEvidence], original_notes: List[dict]) -> Optional[str]:
    if code not in CRITICAL_CODES:
        return None
    
    rule = CRITICAL_CODES[code]
    combined_evidence = " ".join([q.text.lower() for q in quotes])
    
    matched_features = 0
    for feature in rule["required_features"]:
        if feature.lower() in combined_evidence:
            matched_features += 1
    
    if matched_features < rule["min_features"]:
        return f"Critical code {code} ({rule['name']}) requires at least {rule['min_features']} matching features from evidence, found {matched_features}"
    
    return None


def validate_selection(
    selection_codes: List[SelectedCode],
    extraction: ExtractionOutput,
    catalog: Catalog,
    original_notes: List[dict]
) -> ValidationResult:
    errors = []
    validated = []
    
    finding_by_note = {}
    for f in extraction.findings:
        if f.note_index not in finding_by_note:
            finding_by_note[f.note_index] = []
        finding_by_note[f.note_index].append(f)
    
    for sc in selection_codes:
        code_errors = []
        
        err = validate_code_exists(sc.code, catalog)
        if err:
            code_errors.append(err)
        
        icd_code = catalog.codes.get(sc.code)
        
        for quote_ev in sc.quotes:
            if quote_ev.note_index >= len(original_notes):
                code_errors.append(f"Quote references invalid note index {quote_ev.note_index}")
                continue
            note_text = original_notes[quote_ev.note_index]["text"]
            err = validate_quote_is_substring(quote_ev.text, note_text)
            if err:
                code_errors.append(f"Code {sc.code}: {err}")
        
        if icd_code:
            for quote_ev in sc.quotes:
                relevant_findings = finding_by_note.get(quote_ev.note_index, [])
                for f in relevant_findings:
                    if f.evidence_quote in quote_ev.text or quote_ev.text in f.evidence_quote:
                        err = validate_confirmation_level(icd_code, f.status, quote_ev.text)
                        if err:
                            code_errors.append(f"Code {sc.code}: {err}")
        
        err = validate_critical_code_sanity(sc.code, sc.quotes, original_notes)
        if err:
            code_errors.append(err)
        
        if not code_errors:
            validated.append(sc)
        else:
            errors.extend(code_errors)
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        validated_codes=validated
    )