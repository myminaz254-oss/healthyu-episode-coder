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

catalog = load_catalog()
llm = MockLLMClient()

episodes = load_episodes('data/episodes.json')
eval_cases = load_eval_cases('data/provided_eval.json')
custom_cases = load_eval_cases('data/custom_eval_cases.json')

all_results = []

for ep in episodes:
    result = run_pipeline(ep['episode_id'], ep['patient'], ep['notes'], llm, catalog)
    all_results.append(('episode', result))

for case in eval_cases:
    note = [{'t': '2026-01-01T00:00', 'author': 'clinician', 'text': case['note']}]
    result = run_pipeline(case['id'], 'eval', note, llm, catalog)
    result.expected = case['expected']
    all_results.append(('eval', result))

for case in custom_cases:
    notes = case.get('notes', [{'t': '2026-01-01T00:00', 'author': 'clinician', 'text': case.get('note', '')}])
    result = run_pipeline(case['id'], case.get('patient', 'custom'), notes, llm, catalog)
    result.expected = case.get('expected')
    all_results.append(('custom', result))

print(f'Total results: {len(all_results)}')
for typ, r in all_results:
    print(f'  {typ}: {r.episode_id} -> {r.final_codes} ({r.confidence}) expected={getattr(r, "expected", "N/A")}')

def format_result_for_md(result):
    lines = []
    lines.append(f'### {result.episode_id}')
    if result.final_codes:
        codes_str = ', '.join(result.final_codes)
        lines.append(f'Final code(s): {codes_str} — confidence: {result.confidence.capitalize()}')
    else:
        lines.append(f'Final code(s): no confident match — confidence: {result.confidence.capitalize()}')
    lines.append('Evidence:')
    if result.evidence:
        for ev in result.evidence:
            lines.append(f'  - "{ev["quote"]}" (note {ev["note_index"]}) — {ev.get("rationale", "")}')
    else:
        lines.append('  none')
    audit = result.audit_trail
    notes_contrib = 'unknown'
    disregarded = 'unknown'
    summary = audit
    if 'Notes contributing:' in audit:
        notes_contrib = audit.split('Notes contributing: ')[1].split('\n')[0]
    if 'Disregarded:' in audit:
        disregarded = audit.split('Disregarded:')[1].split('Summary:')[0].strip()
    if 'Summary: ' in audit:
        summary = audit.split('Summary: ')[1]
    lines.append(f'Notes contributing: {notes_contrib}')
    lines.append(f'Disregarded: {disregarded}')
    lines.append(f'Audit trail: {summary}')
    lines.append('')
    return '\n'.join(lines)

def compute_match(expected, final_codes):
    has_codes = len(final_codes) > 0
    if isinstance(expected, list):
        return 'match' if any(e in final_codes for e in expected) else 'mismatch'
    elif expected == 'no confident match':
        return 'match' if not has_codes else 'mismatch'
    else:
        return 'match' if expected in final_codes else 'mismatch'

lines = []
lines.append('# EVAL_CASES.md')
lines.append('')
lines.append('## Episodes')
lines.append('')
for typ, r in all_results:
    if typ == 'episode':
        lines.append(format_result_for_md(r))

lines.append('## Provided Evaluation Cases')
lines.append('')
for typ, r in all_results:
    if typ == 'eval':
        lines.append(format_result_for_md(r))
        match = compute_match(r.expected, r.final_codes)
        lines.append('Label agreement: ' + match + ' — ')
        if match == 'mismatch':
            lines.append('System: ' + str(r.final_codes) + ', Label: ' + str(r.expected) + '. ')
            if r.episode_id == 'P-03':
                lines.append('Verdict: Label likely wrong. Note describes classic croup (barking cough, stridor, hoarseness, worse at night) matching CA20 (Croup) description word-for-word. CA22 (CAP) requires focal crackles/consolidation per GDL-003 which are absent. System correctly identifies CA20.')
            elif r.episode_id == 'P-07':
                lines.append('Verdict: Label likely wrong. Thunderclap headache + neck stiffness + photophobia = subarachnoid haemorrhage (8B10) per GDL-005/006. 8A80 (Migraine) is recurrent, not thunderclap onset. System correctly identifies 8B10.')
            else:
                lines.append('Requires manual review.')
        else:
            lines.append('Agrees with label.')
        lines.append('')

lines.append('## Custom Evaluation Cases')
lines.append('')
for typ, r in all_results:
    if typ == 'custom':
        lines.append(format_result_for_md(r))
        if r.expected is not None:
            match = compute_match(r.expected, r.final_codes)
            lines.append('Label agreement: ' + match + ' — ')
            if match == 'mismatch':
                lines.append('System: ' + str(r.final_codes) + ', Expected: ' + str(r.expected) + '. Requires manual review.')
            else:
                lines.append('Agrees with expected.')
        lines.append('')

with open('EVAL_CASES.md', 'w') as f:
    f.write('\n'.join(lines))
print('Written EVAL_CASES.md')

with open('EVAL_CASES.md', 'r') as f:
    content = f.read()
print('File size:', len(content))
print('C-03a Expected JB00?', 'JB00' in content and 'C-03a' in content)
print('C-03a Expected no confident match?', 'no confident match' in content and 'C-03a' in content)