import json
from typing import List, Dict, Optional
from dataclasses import dataclass

from coder.catalog import load_catalog, Catalog
from coder.glossary import normalize_episode_text
from coder.sanitizer import sanitize_episode, DisregardedSpan
from coder.retrieval import build_retrieval_context, CandidateCode
from coder.schemas import (
    ExtractionOutput, SelectionOutput, SelectedCode, QuoteEvidence,
    EpisodeResult, Finding, IgnoredContent
)
from coder.prompts import (
    CALL1_SYSTEM_PROMPT, CALL1_USER_TEMPLATE,
    CALL2_SYSTEM_PROMPT, CALL2_USER_TEMPLATE,
    CALL3_SYSTEM_PROMPT, CALL3_USER_TEMPLATE,
    format_candidates_text, format_guidelines_text, format_original_notes
)
from coder.llm_client import LLMClient, CacheMissError
from coder.validators import validate_selection, ValidationResult
from coder.confidence import compute_confidence
from coder.audit import build_audit_trail, format_evidence_for_output


@dataclass
class PipelineContext:
    episode_id: str
    patient: str
    original_notes: List[dict]
    sanitized_notes: List[dict]
    sanitizer_disregarded: List[DisregardedSpan]
    extraction: Optional[ExtractionOutput] = None
    candidates: List[CandidateCode] = None
    guidelines: List = None
    selection: Optional[SelectionOutput] = None
    validation: Optional[ValidationResult] = None
    calls_used: int = 0
    status: str = "success"


def call_extraction(ctx: PipelineContext, llm: LLMClient) -> ExtractionOutput:
    notes_text = "\n".join([
        f"Note {i} [{n['author']}, {n['t']}]: {n['text']}"
        for i, n in enumerate(ctx.sanitized_notes)
    ])
    
    user_prompt = CALL1_USER_TEMPLATE.format(
        episode_id=ctx.episode_id,
        patient=ctx.patient,
        notes_text=notes_text,
        schema=ExtractionOutput.model_json_schema()
    )
    
    messages = [{"role": "user", "content": user_prompt}]
    response = llm.call(ctx.episode_id, 1, messages, CALL1_SYSTEM_PROMPT)
    
    try:
        data = json.loads(response)
        extraction = ExtractionOutput(**data)
    except Exception as e:
        raise ValueError(f"Failed to parse Call 1 response: {e}\nResponse: {response[:500]}")
    
    ctx.extraction = extraction
    ctx.calls_used += 1
    return extraction


def call_selection(ctx: PipelineContext, llm: LLMClient) -> SelectionOutput:
    candidates_text = format_candidates_text(ctx.candidates)
    guidelines_text = format_guidelines_text(ctx.guidelines)
    original_notes_text = format_original_notes(ctx.original_notes)
    extraction_json = ctx.extraction.model_dump_json(indent=2)
    
    user_prompt = CALL2_USER_TEMPLATE.format(
        episode_id=ctx.episode_id,
        patient=ctx.patient,
        extraction_json=extraction_json,
        candidates_text=candidates_text,
        guidelines_text=guidelines_text,
        original_notes_text=original_notes_text,
        schema=SelectionOutput.model_json_schema()
    )
    
    messages = [{"role": "user", "content": user_prompt}]
    response = llm.call(ctx.episode_id, 2, messages, CALL2_SYSTEM_PROMPT)
    
    try:
        data = json.loads(response)
        selection = SelectionOutput(**data)
    except Exception as e:
        raise ValueError(f"Failed to parse Call 2 response: {e}\nResponse: {response[:500]}")
    
    ctx.selection = selection
    ctx.calls_used += 1
    return selection


def call_repair(ctx: PipelineContext, llm: LLMClient) -> SelectionOutput:
    candidates_text = format_candidates_text(ctx.candidates)
    guidelines_text = format_guidelines_text(ctx.guidelines)
    original_notes_text = format_original_notes(ctx.original_notes)
    extraction_json = ctx.extraction.model_dump_json(indent=2)
    
    validation_errors_text = "\n".join(ctx.validation.errors)
    
    user_prompt = CALL3_USER_TEMPLATE.format(
        episode_id=ctx.episode_id,
        patient=ctx.patient,
        extraction_json=extraction_json,
        candidates_text=candidates_text,
        guidelines_text=guidelines_text,
        original_notes_text=original_notes_text,
        validation_errors=validation_errors_text,
        schema=SelectionOutput.model_json_schema()
    )
    
    messages = [{"role": "user", "content": user_prompt}]
    response = llm.call(ctx.episode_id, 3, messages, CALL3_SYSTEM_PROMPT)
    
    try:
        data = json.loads(response)
        selection = SelectionOutput(**data)
    except Exception as e:
        raise ValueError(f"Failed to parse Call 3 response: {e}\nResponse: {response[:500]}")
    
    ctx.selection = selection
    ctx.calls_used += 1
    return selection


def run_pipeline(
    episode_id: str,
    patient: str,
    notes: List[dict],
    llm: LLMClient,
    catalog: Catalog
) -> EpisodeResult:
    normalized_notes = normalize_episode_text(notes)
    sanitized_notes, sanitizer_disregarded = sanitize_episode(normalized_notes)
    
    ctx = PipelineContext(
        episode_id=episode_id,
        patient=patient,
        original_notes=notes,
        sanitized_notes=sanitized_notes,
        sanitizer_disregarded=sanitizer_disregarded
    )
    
    retrieval_ctx = build_retrieval_context(catalog, sanitized_notes)
    ctx.candidates = retrieval_ctx["candidates"]
    ctx.guidelines = retrieval_ctx["guidelines"]
    
    try:
        call_extraction(ctx, llm)
    except CacheMissError:
        ctx.status = "llm_unreachable"
        return EpisodeResult(
            episode_id=episode_id,
            final_codes=[],
            confidence="none",
            evidence=[],
            audit_trail=f"Call 1 failed: LLM unreachable in replay mode; no clinical extraction performed, no code emitted.",
            calls_used=0,
            status="llm_unreachable"
        )
    except Exception as e:
        ctx.status = "llm_unreachable"
        return EpisodeResult(
            episode_id=episode_id,
            final_codes=[],
            confidence="none",
            evidence=[],
            audit_trail=f"Call 1 failed: {str(e)}; no clinical extraction performed, no code emitted.",
            calls_used=0,
            status="llm_unreachable"
        )
    
    try:
        call_selection(ctx, llm)
    except CacheMissError:
        ctx.status = "llm_unreachable"
        return EpisodeResult(
            episode_id=episode_id,
            final_codes=[],
            confidence="none",
            evidence=[],
            audit_trail=f"Call 2 failed: LLM unreachable in replay mode.",
            calls_used=ctx.calls_used,
            status="llm_unreachable"
        )
    except Exception as e:
        ctx.status = "llm_unreachable"
        return EpisodeResult(
            episode_id=episode_id,
            final_codes=[],
            confidence="none",
            evidence=[],
            audit_trail=f"Call 2 failed: {str(e)}.",
            calls_used=ctx.calls_used,
            status="llm_unreachable"
        )
    
    ctx.validation = validate_selection(
        ctx.selection.codes,
        ctx.extraction,
        catalog,
        ctx.original_notes
    )
    
    if not ctx.validation.is_valid and ctx.calls_used < 3:
        try:
            call_repair(ctx, llm)
            ctx.validation = validate_selection(
                ctx.selection.codes,
                ctx.extraction,
                catalog,
                ctx.original_notes
            )
        except CacheMissError:
            pass
        except Exception:
            pass
    
    final_codes = [sc.code for sc in ctx.validation.validated_codes]
    confidence = compute_confidence(
        ctx.validation.validated_codes,
        ctx.extraction,
        catalog.get_all_codes(),
        ctx.validation
    )
    
    if not final_codes:
        confidence = "none"
        ctx.status = "no_confident_match"
    
    evidence = format_evidence_for_output(ctx.validation.validated_codes)
    audit_trail = build_audit_trail(
        episode_id,
        ctx.extraction,
        ctx.validation.validated_codes,
        ctx.sanitizer_disregarded,
        ctx.validation.errors if not ctx.validation.is_valid else None
    )
    
    return EpisodeResult(
        episode_id=episode_id,
        final_codes=final_codes,
        confidence=confidence,
        evidence=evidence,
        audit_trail=audit_trail,
        calls_used=ctx.calls_used,
        status=ctx.status
    )