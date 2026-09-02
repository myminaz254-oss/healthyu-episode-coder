import json
from dataclasses import dataclass
from typing import List, Dict, Optional, Set
from pathlib import Path


@dataclass
class ICDCode:
    code: str
    title: str
    chapter: str
    description: str


@dataclass
class Guideline:
    id: str
    linked_codes: List[str]
    text: str
    flagged_inconsistent: bool = False
    inconsistency_reason: str = ""


class Catalog:
    def __init__(self, catalog_path: str, guidelines_path: str):
        self.codes: Dict[str, ICDCode] = {}
        self.guidelines: Dict[str, Guideline] = {}
        self.code_to_guidelines: Dict[str, List[str]] = {}
        self._load_catalog(catalog_path)
        self._load_guidelines(guidelines_path)
        self._validate_guideline_code_consistency()

    def _load_catalog(self, path: str):
        with open(path, 'r') as f:
            data = json.load(f)
        for item in data:
            code = ICDCode(
                code=item['code'],
                title=item['title'],
                chapter=item['chapter'],
                description=item['description']
            )
            self.codes[code.code] = code

    def _load_guidelines(self, path: str):
        with open(path, 'r') as f:
            data = json.load(f)
        for item in data:
            guideline = Guideline(
                id=item['id'],
                linked_codes=item['linked_codes'],
                text=item['text']
            )
            self.guidelines[guideline.id] = guideline
            for code in guideline.linked_codes:
                if code not in self.code_to_guidelines:
                    self.code_to_guidelines[code] = []
                self.code_to_guidelines[code].append(guideline.id)

    def _validate_guideline_code_consistency(self):
        for guideline in self.guidelines.values():
            for code in guideline.linked_codes:
                if code not in self.codes:
                    guideline.flagged_inconsistent = True
                    guideline.inconsistency_reason = f"Code {code} not found in catalog"
                    continue
                icd_code = self.codes[code]
                guideline_text_lower = guideline.text.lower()
                code_title_lower = icd_code.title.lower()
                code_desc_lower = icd_code.description.lower()
                code_keywords = set(code_title_lower.split() + code_desc_lower.split())
                guideline_keywords = set(guideline_text_lower.split())
                overlap = code_keywords & guideline_keywords
                meaningful_overlap = {w for w in overlap if len(w) > 4}
                if not meaningful_overlap:
                    guideline.flagged_inconsistent = True
                    guideline.inconsistency_reason = (
                        f"Code {code} ({icd_code.title}) has no topical keyword overlap with guideline text"
                    )

    def get_code(self, code: str) -> Optional[ICDCode]:
        return self.codes.get(code)

    def get_guideline(self, guideline_id: str) -> Optional[Guideline]:
        return self.guidelines.get(guideline_id)

    def get_guidelines_for_code(self, code: str) -> List[Guideline]:
        guideline_ids = self.code_to_guidelines.get(code, [])
        return [self.guidelines[gid] for gid in guideline_ids if gid in self.guidelines]

    def get_all_codes(self) -> List[ICDCode]:
        return list(self.codes.values())

    def get_all_guidelines(self) -> List[Guideline]:
        return list(self.guidelines.values())

    def get_flagged_guidelines(self) -> List[Guideline]:
        return [g for g in self.guidelines.values() if g.flagged_inconsistent]


def load_catalog(catalog_path: str = "data/icd_catalog.json", guidelines_path: str = "data/guideline_snippets.json") -> Catalog:
    return Catalog(catalog_path, guidelines_path)