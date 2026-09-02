import re
from difflib import SequenceMatcher
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass
from coder.catalog import Catalog, ICDCode, Guideline
from coder.glossary import normalize_text


@dataclass
class CandidateCode:
    code: ICDCode
    score: float
    matched_terms: List[str]


def tokenize(text: str) -> Set[str]:
    text = normalize_text(text).lower()
    tokens = re.findall(r'\b[a-z]{3,}\b', text)
    stopwords = {'the', 'and', 'for', 'with', 'from', 'this', 'that', 'was', 'were', 'have', 'has', 'had', 'not', 'but', 'are', 'you', 'your', 'can', 'will', 'just', 'been', 'into', 'over', 'under', 'after', 'before', 'during', 'patient', 'pt', 'note', 'notes', 'coder', 'system', 'coding', 'guidance', 'disregard', 'record', 'encounter', 'insurance', 'purposes'}
    return {t for t in tokens if t not in stopwords and len(t) > 2}


def fuzzy_match_score(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def score_code_against_text(code: ICDCode, episode_text: str) -> Tuple[float, List[str]]:
    code_text = f"{code.title} {code.description}".lower()
    episode_tokens = tokenize(episode_text)
    code_tokens = tokenize(code_text)

    exact_matches = episode_tokens & code_tokens
    fuzzy_matches = []
    for ep_token in episode_tokens:
        for code_token in code_tokens:
            if ep_token != code_token and fuzzy_match_score(ep_token, code_token) > 0.85:
                fuzzy_matches.append(ep_token)

    all_matches = list(exact_matches) + fuzzy_matches
    if not episode_tokens:
        return 0.0, []

    score = len(all_matches) / max(len(episode_tokens) * 0.3, 1)
    return min(score, 1.0), all_matches


def retrieve_candidate_codes(catalog: Catalog, episode_notes: List[Dict], top_k: int = 12) -> List[CandidateCode]:
    full_text = " ".join([n["text"] for n in episode_notes])
    candidates = []
    for code in catalog.get_all_codes():
        score, matched = score_code_against_text(code, full_text)
        if score > 0:
            candidates.append(CandidateCode(code=code, score=score, matched_terms=matched))

    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates[:top_k]


def retrieve_relevant_guidelines(catalog: Catalog, candidate_codes: List[CandidateCode], episode_notes: List[Dict]) -> List[Guideline]:
    candidate_code_set = {c.code.code for c in candidate_codes}
    full_text = " ".join([n["text"] for n in episode_notes])
    episode_tokens = tokenize(full_text)

    relevant_guidelines = []
    seen_ids = set()

    for candidate in candidate_codes:
        for guideline in catalog.get_guidelines_for_code(candidate.code.code):
            if guideline.id not in seen_ids and not guideline.flagged_inconsistent:
                relevant_guidelines.append(guideline)
                seen_ids.add(guideline.id)

    for guideline in catalog.get_all_guidelines():
        if guideline.id in seen_ids:
            continue
        guideline_tokens = tokenize(guideline.text)
        overlap = len(episode_tokens & guideline_tokens)
        if overlap >= 2:
            if not guideline.flagged_inconsistent:
                relevant_guidelines.append(guideline)
                seen_ids.add(guideline.id)

    return relevant_guidelines


def build_retrieval_context(catalog: Catalog, episode_notes: List[Dict]) -> Dict:
    candidates = retrieve_candidate_codes(catalog, episode_notes)
    guidelines = retrieve_relevant_guidelines(catalog, candidates, episode_notes)
    return {
        "candidates": candidates,
        "guidelines": guidelines
    }