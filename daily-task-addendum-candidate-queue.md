# Task addendum — review from the candidate queue (added 2026-09-14)

This replaces the task's own web searching for new research. A GitHub Actions
fetcher now lands date-bounded results from PubMed, medRxiv/bioRxiv, the journal
and curator feeds, and the trial watchlist into `longevity_candidates`. Your job is
judgment, not discovery. Run every 3–4 days.

## Each run

1. **Read the queue.** `select * from longevity_candidates where status='unreviewed'
   order by pub_date desc`. If it is empty, note that in the run log and do not fall
   back to web search — an empty queue means the fetcher didn't run; say so.

2. **Triage in this order**, stopping when you have filed 8 articles:
   - `study_hint` in (`rct`, `meta`) with human subjects → read the abstract, fetch the
     paper if the abstract is thin, file as tier 1–2.
   - `trial_update` rows → check the trial page; if results are posted, that is a
     tier-1 item and may change an intervention verdict. File it and reset
     `changed_since_review = false` on the watchlist row.
   - `cohort` → file if the outcome is all-cause mortality, healthspan, or an
     intervention already on the site; tier 3.
   - `preprint` → hold unless it is a human RCT or a lifespan result for a listed
     intervention; tier 4, mark `content_type = 'Preprint'`.
   - `animal`, `review`, `other` → file only if it touches an intervention on the site
     or a State of the Science item; otherwise `status = 'skipped'` with a two-word reason.

3. **Filing a candidate:** insert into `longevity_articles` as usual (own-words
   summary, bullets, practical takeaway, scope tag, related interventions), then set
   the candidate's `status = 'filed'`, `article_id`, `reviewed_at`. Use `pub_date` from
   the candidate as `source_publish_date` — it is the Crossref date, not the feed date.

4. **Recirculated items** (`recirculated = true`): if the paper is already on the site,
   skip with reason "already filed"; if not, file it with the true date and add a
   bullet noting when and where it re-surfaced.

5. **Held items** stay `held` with a one-line reason and are re-considered next run.
   Anything held for three runs becomes `skipped`.

6. **Never** file a candidate without a DOI or registry ID unless it comes from a
   tier-1 journal feed.

## Intervention and State of the Science changes

A filed candidate can change an intervention row only if it is a human RCT,
meta-analysis, or completed trial readout. Cite the candidate's DOI in
`evidence_refs`, update `efficacy_summary` / `mortality_evidence` / `scope_note`,
and log the change. State of the Science revises only under the existing policy.

## Synthesis

Rewrite `longevity_synthesis` each run over the trailing six weeks of filed
articles. The `hype_watch` section should draw on skipped and recirculated
candidates — that is where the marketing lives.

## Run log

`longevity_pipeline_runs` gets one row per run. In the run notes: queue size at start,
filed / held / skipped counts, any intervention changed, any trial with
`changed_since_review`, and any NOT_FOUND trial IDs for Richie to fix.
