# SEC answer-quality evaluation: local before/after

This is a **draft, source-span-verified benchmark**, not an independently
adjudicated factual-accuracy study. It uses the same 50 questions (40 intended
to be answerable, 10 intentionally unsupported) against 4,224 indexed SEC
chunks. The set spans multiple companies and 10-K, 10-Q, and 8-K earnings
release filings. The baseline used the original vector-only research path;
the after run used hybrid retrieval and quote/number validation. Both used
the local Qwen 2.5 7B model and the same indexed corpus. Saved predictions
are in [results_before.json](results_before.json) and
[results_final.json](results_final.json).
The original-path predictions were captured before the implementation change;
its unsupported-refusal score was rescored from those saved answers after
fixing the refusal detector. The after run was generated with the code on this
branch.

| Automatic measure | Before | After | Interpretation |
| --- | ---: | ---: | --- |
| Labeled chunk in top 5, 40 intended-answerable questions | 34/40 (85%) | 39/40 (97.5%) | Strict exact-chunk hit; another useful chunk still counts as a miss. |
| Simple keyword search, same 40 questions | 37/40 (92.5%) | 37/40 (92.5%) | Fixed comparison baseline. |
| Expected short answer appears in response | 33/40 (82.5%) | 26/40 (65%) | String-based proxy, **not factual accuracy**; conservative refusal hurts coverage. |
| Labeled chunk appears among cited chunks | 24/40 (60%) | 24/40 (60%) | Provenance proxy, **not citation correctness**. |
| Unsupported question declined | 9/10 (90%) | 10/10 (100%) | Phrase-based proxy; baseline invented a confidential Meta roadmap answer. |

The retrieval gain is the clearest measured improvement: vector-only fell
below a basic keyword baseline, and reciprocal-rank fusion passed it on this
small set. The answer layer has a real trade-off. It withheld answers when
the model could not supply a sufficiently matching quote or introduced a
number absent from the evidence. For example, it withheld a Netflix interest
expense answer after the model changed the table value into a larger amount
without a unit-bearing quote. But this cut expected-answer inclusion by seven
questions. It should not be presented as a net answer-quality gain.

The validator checks quotation provenance and number presence, **not
semantic entailment**. Manual spot checks found remaining problems: one
answer cites a passage about ExxonMobil's lower-emissions strategy without
supporting its additional policy/technology claim (S12); one Disney answer
attributes a franchise streaming figure to an individual film (S41); and a
Disney depreciation question has two different valid scopes in the same
filing (S30). Another response (S34) expands a short Superfund Act quote into
several uncited liability claims. The Apple "most recent period" question
(S29) is ambiguous because a later filing is also indexed. Other draft
questions use a relative period or omit a reporting scope (S07, S14, S26).
These make the automatic answer and
citation proxies unsuitable for résumé claims about factual or citation
accuracy. The [audit sheet](audit_final.md) contains every prediction and
actual cited excerpt, but its verdict boxes are deliberately blank pending
independent review and question revision.

No production deployment was changed by this evaluation. The code and
results live on a separate local branch until reviewed. A defensible public
claim would require freezing corrected, unambiguous questions, independently
reviewing each label and citation, then rerunning both versions on that same
set. Do not claim an X-to-Y improvement in factual/citation accuracy from
these proxy figures.
