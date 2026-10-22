# Stratos SEC answer-quality evaluation

This is a local, source-anchored evaluation of the Stratos research-answer
path. The frozen set has **50 questions** about **17 companies**: 40 answerable
from indexed SEC filings (14 10-K, 12 10-Q, 14 8-K/earnings-release cases)
and 10 deliberately unsupported questions. The corpus held 4,224 chunks.
The original vector-only path and the improved hybrid/quote-checked path used
the same questions, corpus, and local Qwen 2.5 7B model. Ambiguous draft
questions were clarified and one mislabeled tax rate was corrected against
the source before the results below were reconciled. Changed questions were
rerun, not merely rescored. No production database or deployment was changed.

| Measure | Original path | Hybrid + quote check | Numeric-guard revision |
| --- | ---: | ---: | ---: |
| Labeled SEC chunk in top 5, answerable questions | **30/40 (75%)** | **36/40 (90%)** | **36/40 (90%)** |
| Simple keyword-search baseline, same questions | 36/40 (90%) | 36/40 (90%) | 36/40 (90%) |
| Factually correct answer to answerable question, reviewed | **31/40 (77.5%)** | **28/40 (70%)** | **32/40 (80%)** |
| Answerable questions refused despite available evidence | 3/40 | 11/40 | 6/40 |
| Intentionally unsupported questions declined | 9/10 (90%) | 10/10 (100%) | 10/10 (100%) |
| Printed citations whose **full indexed chunk** supports the answer | 30/44 (68.2%) | 31/33 (93.9%) | 35/38 (92.1%) |
| Printed citations whose **displayed quote** supports the answer | Not comparable: old path showed truncated retrieval previews | 26/33 (78.8%) | 27/38 (71.1%) |

The citation denominators cover only printed labels on substantive responses
to answerable questions. They exclude citations attached to refusals. For a
full-chunk citation to pass, that exact chunk—not an adjacent chunk or the
filing as a whole—must support the answer's company, period, scope, and value.
The higher citation precision is therefore **conditional on answering**;
the hybrid paths printed fewer citations than the original because they refused
more questions.
The displayed-quote check is stricter: a correct full chunk can still show an
incomplete quote. These manually reviewed judgments are recorded case by case
in [audit_verdicts.json](audit_verdicts.json), rendered in
[audit_before.md](audit_before.md) and [audit_final.md](audit_final.md), and
recounted by `python -m evaluation.score_audit`. The same evaluator who built
the benchmark performed the review; this is **not an independent blinded
study**. The questions were selected from available source spans and are not
a representative sample of all investor questions.

The numeric-guard revision permits the answer to repeat numbers already in the
question (for example, the requested fiscal year), while still requiring any
*new* number to occur in the cited quote. This recovered four previously
refused, factually correct answers (S06, S26, S30, S42). It also admitted a
wrong-period AMD answer (S23): the model quoted a real **$212 million**
prior-year figure and presented it as the requested **2026 $389 million**
figure. Neither quote provenance nor number matching proves period alignment.
The reviewed revision run is saved in
[results_candidate.json](results_candidate.json), with case-level verdicts in
[audit_verdicts_numeric_guard.json](audit_verdicts_numeric_guard.json). Recount
it with `python -m evaluation.score_audit --after evaluation/results_candidate.json
--single-verdicts evaluation/audit_verdicts_numeric_guard.json`. Because the
same 50 questions guided this revision, its 80% result is an **in-sample,
single-run result**, not evidence of out-of-sample generalization.

The retrieval change closes the gap to a simple keyword baseline on this
set, but does **not** beat it. The evidence checks reduce unsupported
citations and eliminate the one false answer to an intentionally unsupported
question, but they are too conservative: factual-answer coverage **fell**
from 31 to 28 of 40 before the guard revision. The original hybrid path also leaves seven of 33 displayed
quotes too narrow to substantiate every detail (often the date or units).
For example, its Microsoft response to S31 gives the wrong category even
though its selected quote mentions the correct one. This demonstrates that
quote provenance and number matching are **not semantic entailment**.

Automatic string checks are kept in the JSON files for reproducibility, not
as factual-accuracy claims: expected-answer inclusion is 30/40 before and
27/40 after, and citing the *labeled* chunk is 23/40 before and 24/40 after.
Both differ from the manually reviewed measures because a correct answer
may use equivalent wording or another supporting chunk, while a cited gold
chunk need not support the model's actual claim.

## How to reproduce and what remains

The frozen labels are in [sec_questions.json](sec_questions.json), saved
predictions in [results_before.json](results_before.json) and
[results_final.json](results_final.json), and the two answer paths in
[legacy_answer.py](legacy_answer.py) and
[../services/research_answer.py](../services/research_answer.py). Run
`python -m evaluation.score_audit` from `backend` to recompute the reviewed
counts without model or database access. `python -m pytest -q` runs the
code-level tests. A fresh model evaluation needs the configured SEC index and
local Ollama model described in the [project README](../../README.md).

The next engineering priority is to improve **answerable-question recall**
without admitting unsupported claims: repair missing date/unit context in
retrieved table chunks, then evaluate a claim-level evidence verifier on a
separate validation set before using it here. Freeze this 50-question set for
comparison; do not repeatedly tune to it. An independent reviewer should
also adjudicate the labels and citation judgments before treating these
figures as external research results. A responsible résumé claim today can say
that exact-chunk Recall@5 went **75% → 90% on 40 source-anchored SEC
questions**. The numeric-guard revision recovered answer accuracy from
**70% to 80% on this same set**, but decreased displayed-quote support and
admitted one wrong-period answer. Do **not** present this as a fully solved
citation-verification system or independent benchmark.
