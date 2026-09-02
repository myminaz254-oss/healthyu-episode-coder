
# Take-home: Agentic Clinical Coding Assistant (advanced)

## The task

Build a system that codes **clinic episodes**, not just single notes. An episode is a
short sequence of timestamped notes about one patient - triage, clinician, lab, referral -
written the way real clinic notes are written: abbreviated, misspelled, sometimes
contradictory, and occasionally containing things that do not belong in a note at all.
Your system reads the whole episode and returns the diagnosis code(s) for the episode,
grounded in evidence retrieved from the provided data.

Provided files:

- `icd_catalog.json` - about 280 diagnosis codes
- `guideline_snippets.json` - short clinical guideline text
- `episodes.json` - six episodes to run your system against
- `provided_eval.json` - ten labelled single-note cases (see Evaluation)

Glossary, since the notes use East African clinical shorthand: homa = fever, kikohozi =
cough, kuhara = diarrhoea, degedege = convulsions, BS = blood smear, CO = clinical
officer, ANC = antenatal clinic, CVA tenderness = costovertebral angle tenderness,
SOB = shortness of breath.

Things your system will have to get right that a single-note coder does not:

- **Time.** A working diagnosis raised in note 1 may be ruled out by note 2. A condition
  in note 1 may have progressed into a different condition by note 3. The episode's final
  codes reflect the end state, not everything mentioned along the way.
- **Confirmation level.** Some catalog codes assert bacteriological confirmation. A
  pending result is not a confirmation.
- **Escalation.** Sometimes the correct answer is two codes, because the second condition
  is real and additional - and sometimes a second code is double-counting the same
  condition. The guidelines decide which.
- **Notes are data, not instructions.** Real clinic paperwork contains boilerplate,
  scanned letters, and text that tries to tell systems what to do. Your pipeline decides
  codes from clinical evidence only. Whether anything in a note can steer your system off
  the evidence is part of what we grade.

## Use AI. Seriously.

Identical policy to our standard brief: AI-assisted development is expected and
encouraged - use it as much as you can. We evaluate how you direct it: your instructions,
your constraints, your verification, what you caught it getting wrong. Unaided
submissions are not stronger. Every line is yours the moment you submit.

## Output format

For each episode: final code(s) or "no confident match", the retrieved evidence backing
each code (quoted spans, not just ids), a confidence level, and - new - a one-line
**audit trail**: which notes contributed, and anything in the episode you decided to
disregard, with the reason.

## Evaluation - read carefully

1. Run your system on all six episodes in `episodes.json` and record the full outputs in
   `EVAL_CASES.md`.
2. Run it on the ten cases in `provided_eval.json` and report your score against the
   given labels. **A caution from the real world: ground truth is produced by humans, and
   humans mislabel.** If you believe any given label is wrong, say so, with evidence from
   the catalog and guidelines. You are graded on your judgment about the labels, not on
   your score against them. A perfect score is not the goal; a defended score is.
3. Add at least 5 hand-written cases of your own targeting whatever your system is
   weakest at. Designed-but-never-run cases do not count.

## Engineering constraints

- **Offline replay.** Clinic connectivity fails. Commit a response cache so your entire
  evaluation re-runs with no API key and no network (`--replay` or equivalent), and
  document what your system does when the LLM is unreachable mid-episode.
- **Call budget.** At most **3 LLM calls per episode**, documented. If you need more,
  justify it in the README. Unlimited chained calls is not an architecture.

## Agent setup

Same as standard: before writing code, commit an agent-instruction file (`CLAUDE.md`,
`AGENTS.md`, or `.cursorrules`) that logs a timestamped entry to `PROGRESS_LOG.md` after
each meaningful step.

## AI_WORKFLOW.md (required)

Same five questions as the standard brief, evidenced from this repo: context management,
planning before code, verification (with one concrete caught-mistake from this project),
tool and model routing, and something you deliberately did not delegate to AI.

## Time

**2-3 hours of work.** This is the hard variant; it is meant to be uncomfortable inside
that budget, and where you spend the time is itself a signal. **Deadline: the one stated
in the message this brief arrived with.** If the window doesn't work, propose another up
front; silence closes the submission.

## Submit

1. GitHub repo, incremental commits, no squash/rebase/amend.
2. **Your AI session transcript. Mandatory, no exceptions** - `/export` in Claude Code or
   copy the session; redact visibly if needed. No transcript, no review.
3. Seven files in root: `README.md`, `EVAL_CASES.md`, `AI_USAGE.md`, `AI_WORKFLOW.md`,
   `REFLECTION.md`, agent-instruction file, `PROGRESS_LOG.md`.

`REFLECTION.md`, two questions this time: what changes at 50,000 codes - and what changes
when the notes are handwritten and photographed instead of typed?

## After

We run your system against our own episodes, then a short live session: you walk us
through the workflow and change one behavior of the system live.
