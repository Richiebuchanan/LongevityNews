
## Landmark studies (added 2026-09-17)
`longevity_articles.landmark = true` marks the studies the site's verdicts rest on; `reference_key` links the row to its footnote in `longevity_references`. Research Watch shows them under "Landmark studies". Rules:
1. Every intervention's `evidence_refs` of tier 1–2 human evidence (RCT, meta-analysis, large cohort) and the defining animal study for any animal-only intervention must exist as a landmark article. Each run, check up to 5 interventions for missing ones and backfill: own-words summary, three bullets with the key numbers, one-line takeaway, `landmark = true`, `reference_key` set, `date_found = today`, `source_publish_date` = the paper's date, `topic_tags` applied.
2. A landmark article is filed once; a new study that supersedes it (longer follow-up, larger meta-analysis) is filed as a new landmark and the old one keeps its flag with a bullet noting the update.
3. Never mark news coverage, editorials, or company announcements as landmark.
4. When a topic page is created, the studies cited in its document are landmark candidates.

## Evidence Pipelines (added 2026-09-18)
`longevity_pipelines` tracks the full evidence chain for interventions actively moving through research. Each row has an `intervention`, `slug`, `current_stage` (one of: discovery, animal_proof, animal_replication, first_in_human, human_biomarker, human_outcome, proven), a `milestones` JSON array, and a `next_expected` object.

Each run:
1. When an article is filed that advances an existing pipeline (a trial reports, a replication publishes, a new trial registers), **add a milestone** to the `milestones` array: `{stage, date, label, result, ref_key}`. Update `current_stage` if the new milestone is further right than the current one.
2. When a trial on the watchlist changes status and it's the `next_expected` for a pipeline, update `next_expected` (new expected date, or replace with the next future milestone).
3. When a new intervention is added to the site that has an active research trajectory (at least one animal study and one planned or running human trial), create a pipeline row. Interventions with settled evidence (creatine, statins) or no forward trajectory do not need one.
4. `topic_tags` must match the intervention's topic tags so it appears on the right topic pages.
5. Milestones are append-only and chronological. Never remove a milestone; if a result is superseded, add the new one and note "supersedes [date]" in the result field.
6. Log pipeline changes in the run log.
