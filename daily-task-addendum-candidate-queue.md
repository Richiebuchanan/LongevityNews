
## Landmark studies (added 2026-09-17)
`longevity_articles.landmark = true` marks the studies the site's verdicts rest on; `reference_key` links the row to its footnote in `longevity_references`. Research Watch shows them under "Landmark studies". Rules:
1. Every intervention's `evidence_refs` of tier 1–2 human evidence (RCT, meta-analysis, large cohort) and the defining animal study for any animal-only intervention must exist as a landmark article. Each run, check up to 5 interventions for missing ones and backfill: own-words summary, three bullets with the key numbers, one-line takeaway, `landmark = true`, `reference_key` set, `date_found = today`, `source_publish_date` = the paper's date, `topic_tags` applied.
2. A landmark article is filed once; a new study that supersedes it (longer follow-up, larger meta-analysis) is filed as a new landmark and the old one keeps its flag with a bullet noting the update.
3. Never mark news coverage, editorials, or company announcements as landmark.
4. When a topic page is created, the studies cited in its document are landmark candidates.
