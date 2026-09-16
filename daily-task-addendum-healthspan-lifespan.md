# Daily task addendum — Live Better / Live Longer (added 2026-09-09)

Paste this section into the Longevity News scheduled-task prompt, after the existing citation rules.

## The two questions

This site answers two distinct questions: **what helps me live better** (healthspan) and **what helps me live longer** (lifespan). Every write you make must classify which question the item speaks to. Never let healthspan evidence imply a lifespan benefit.

## Schema

`longevity_interventions` now has:
- `lifespan_scope` — `healthspan` | `lifespan` | `both` | `n/a` (diagnostics only). The question the intervention is *aimed at*.
- `mortality_evidence` — `human_rct` | `human_obs` | `human_null` | `animal_only` | `none`. What human **all-cause mortality** data actually shows. Disease-specific mortality (e.g. heart-failure trials) does not count as all-cause unless the population is general.
- `scope_note` — required, one sentence, states the basis for both fields (the trial or cohort, the population, and what was *not* shown).

`longevity_articles`, `longevity_media`, `longevity_figures` have `lifespan_scope` only (figures also get `scope_note`).

## Classification rules

1. Default to `healthspan`. Use `lifespan` or `both` only if the item makes or tests a claim about survival, all-cause mortality, or the rate of aging.
2. `mortality_evidence` is set by the strongest **human all-cause mortality** evidence you can cite:
   - Randomized trial or meta-analysis of RCTs with a mortality endpoint → `human_rct`
   - Prospective cohort or Mendelian randomization → `human_obs`
   - Tested in adequately powered human trials and no benefit found → `human_null`
   - Lifespan extension only in animals → `animal_only`
   - Nothing → `none`
3. Animal lifespan data never raises `mortality_evidence` above `animal_only`, no matter how many species.
4. Biomarker changes (epigenetic clocks, telomeres, NAD+, IGF-1) are never mortality evidence.
5. Population qualifiers are mandatory in `scope_note` when the mortality data comes from a sick or high-risk group (diabetics, obese, heart failure, CKD). Say plainly that nothing is known in healthy adults.
6. For articles and media: tag `lifespan` if the study's primary endpoint is survival or the discussion is about the rate of aging; `both` if it addresses function *and* survival; otherwise `healthspan`.
7. For figures: tag which question their program is actually trying to answer, and note in `scope_note` if their public claims are about lifespan while their evidence is healthspan.

## Interventions page

Three views exist; read them rather than recomputing:
- `longevity_live_better` — scope in (healthspan, both)
- `longevity_live_longer` — scope in (lifespan, both) AND mortality_evidence in (human_rct, human_obs); `evidence_rank` orders RCT first
- `longevity_lifespan_unproven` — lifespan claims resting on animals, mechanism, or null human data

An intervention may move into `longevity_live_longer` only when you can cite a primary source for human all-cause mortality. Log the change and the citation in the run notes.

## State of the Science

On the next revision that meets the existing policy, restructure the four-tier instruction manual so each tier (A non-negotiable / B strongly supported / C low-downside bets / D don't) is split into two lists: **Live Better** and **Live Longer**. Promotion into a Live Longer list requires human all-cause mortality data — biomarker, animal, or single-disease outcome data is not sufficient. Add to the changelog: "Healthspan/lifespan split applied across all tiers." Do not otherwise alter tier assignments in that revision; the split is a reorganization, not a re-grading.

## Existing rows

All 39 interventions were classified on 2026-09-09 by review. Do not reclassify an existing row unless a new tier-1 or tier-2 source changes the mortality picture; when you do, cite it and update `scope_note`.

## Topic pages (added 2026-09-16)
`longevity_topic_pages` holds versioned, append-only documents for topic pages (first: `glp1`). Structure: `framing`, `grade_key`, `sections[]` each with `items[]` (label, text, grade ∈ proven/likely/unproven/null, refs[]) or `dos[]`/`donts[]` (text, derived_from), and `revision_policy`. Pages also show live content by `topic_tags` on articles, interventions, media and trial watch.

Each run:
1. Tag every new article, media row or trial update that concerns a topic with its tag (`glp1`, `brain`, `cancer` when it exists). Tagging is what makes it appear on the topic page.
2. Revise a topic document only under its `revision_policy` — a hard-endpoint human RCT promotes an item to proven; a completed trial that misses moves it to null; new observational/animal data may add an item as unproven or likely, never promote. Publish as a new version (max(version)+1) with the full document, a changelog entry (date, change, reason, refs) and `revision_reason`. Never edit a published version.
3. Do's and don'ts derive from risk items; change them only when the risk item they cite changes, and keep `derived_from` accurate.
4. A trial on the watchlist with `changed_since_review = true` and a topic tag is the first thing to check for that topic.
