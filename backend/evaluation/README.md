# SEC research evaluation

This is a reproducible **draft** benchmark for the indexed SEC research corpus,
not a claim that Stratos is reliable for investment decisions.

`sec_questions.json` contains 50 questions: 40 answerable from an indexed
chunk and 10 deliberately outside the indexed excerpts. Supported rows record
the ticker, filing type/date/section, SEC source URL, exact indexed chunk ID,
expected short answer, and a source excerpt containing that answer. The
questions began as locally generated drafts; ambiguous table labels were
removed or corrected after inspection. Independent semantic review of all 40
labels is still needed before reporting public answer-accuracy figures.

Run from `backend/` with a populated, gitignored `.env` and local Qwen model:

```bash
venv/bin/python -m evaluation.run_sec_eval \
  --labels evaluation/sec_questions.json \
  --retriever hybrid \
  --output evaluation/results_final.json
```

The runner evaluates retrieval separately from generation. It compares a
ticker-filtered vector search with a simple BM25 keyword baseline over the
same indexed chunks; the improved backend combines their top-five rankings
using reciprocal rank fusion. `gold_chunk_recall_at_5` is **strict exact-chunk
recall**: a different excerpt that also supports the answer is counted as a
miss. The answer checks are conservative automated proxies: expected-answer
text present, labeled chunk cited, and an unsupported-question refusal phrase.
They are not a substitute for reading every answer and cited source.

The answer path now requests a source quote, verifies that it matches the
retrieved excerpt closely, rejects unsupported numerical claims, and returns
only citations whose quote passed validation. This is a provenance and number
check, **not general semantic entailment**. A human should audit whether each
quote actually supports the whole claim. The guard may decline answerable
questions when a model quote is too imprecise; report that coverage trade-off.

Generate a review sheet with the actual cited chunks before calculating
factual or citation accuracy:

```bash
venv/bin/python -m evaluation.make_audit_sheet \
  --results evaluation/results_final.json \
  --output evaluation/audit_final.md
```

See [the measured before/after report](report.md). The review sheet is a
template: its boxes have not been independently adjudicated. Several questions
use relative periods (for example, "most recent") or omit a reporting scope;
they must be rewritten before this set can support a public factual-accuracy
claim.

For a résumé, use only stable results from a manually reviewed, frozen label
set, and describe the exact metric (for example, "labeled-chunk hit@5"). Do
not call the automatic answer or citation proxies factual/citation accuracy.
