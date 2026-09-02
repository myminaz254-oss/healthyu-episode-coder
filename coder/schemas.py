from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class Finding(BaseModel):
    note_index: int
    finding: str
    status: Literal["active", "ruled_out", "superseded", "pending_confirmation", "confirmed"]
    evidence_quote: str


class IgnoredContent(BaseModel):
    note_index: int
    quote: str
    reason: str


class ExtractionOutput(BaseModel):
    findings: List[Finding]
    ignored_content: List[IgnoredContent] = []


class QuoteEvidence(BaseModel):
    note_index: int
    text: str


class SelectedCode(BaseModel):
    code: str
    quotes: List[QuoteEvidence]
    rationale: str


class SelectionOutput(BaseModel):
    codes: List[SelectedCode]
    confidence_self_report: Literal["high", "medium", "low"]
    notes_contributing: List[int]
    flags: List[str] = []


class ValidationError(BaseModel):
    error_type: str
    message: str
    code: Optional[str] = None
    quote: Optional[str] = None
    note_index: Optional[int] = None


class AuditTrail(BaseModel):
    notes_contributing: List[int]
    disregarded: List[IgnoredContent]
    summary: str


class EpisodeResult(BaseModel):
    episode_id: str
    final_codes: List[str]
    confidence: Literal["high", "medium", "low", "none"]
    evidence: List[dict]
    audit_trail: str
    calls_used: int
    status: Literal["success", "llm_unreachable", "validation_failed", "no_confident_match"] = "success"
    
    class Config:
        extra = "allow"