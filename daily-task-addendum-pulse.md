# Task addendum — Pulse and social monitoring (added 2026-09-17)

The GitHub Action now also runs `fetch_social.py`, which pulls recent posts from
Bluesky accounts and RSS from newsletters listed in `longevity_social_accounts`
(active=true), extracts DOIs and links, and drops them into `longevity_candidates`
with `source='social'` and `social_handle` set. Everything else about triage and
filing in the candidate-queue addendum applies to these too.

## The Pulse

Each run, after filing articles and reviewing the candidate queue, write a Pulse.
Insert one row into `longevity_pulse` with:

- `pulse_date` = today
- `period_start` / `period_end` = the window this run covers
- `pulse` = a JSON object with five sections:

```json
{
  "talked_about": [
    { "topic": "...", "summary": "one paragraph, own words",
      "site_grade": "proven|likely|unproven|null|n/a",
      "handles": ["who discussed it"], "refs": ["reference keys if any"] }
  ],
  "studies_surfaced": [
    { "title": "...", "doi": "...", "surfaced_by": ["handles"],
      "filed": true|false, "article_id": N|null,
      "note": "why it matters or why it was skipped" }
  ],
  "hype_watch": [
    { "claim": "...", "source": "handle or outlet",
      "site_grade": "unproven|null",
      "reality": "one sentence" }
  ],
  "source_suggestions": [
    { "handle_or_url": "...", "platform": "bluesky|newsletter",
      "why": "what signal it produces that the current list misses" }
  ],
  "envelope_pushers": [
    { "figure": "...", "what_happened": "...",
      "changes_entry": true|false }
  ]
}
```

Rules:
1. `talked_about`: 3–5 threads maximum, ranked by how many tracked accounts
   discussed them and how much the site's users would care. Grade each against
   the site's evidence system; hype gets labeled, not amplified.
2. `studies_surfaced`: every paper or trial link from social candidates this
   run that was either filed or worth noting. If a paper was already in the
   queue from PubMed, note it was also socially discussed (that's a relevance
   signal).
3. `hype_watch`: claims that circulated widely with thin evidence. Name the
   claim, the source, and the site's grade. Do not grade the person, grade
   the claim.
4. `source_suggestions`: accounts or feeds the task noticed producing signal
   the current list doesn't capture. Status `draft`; Richie approves from
   the admin page before they're added to the fetch list.
5. `envelope_pushers`: anything a profiled figure said or launched that
   changes their entry. If `changes_entry` is true, update the figure row
   and cite the post.

## Social candidates in triage

Social-sourced candidates (`source='social'`) follow the same triage rules as
everything else, with one addition: the `social_handle` and the account's `role`
inform relevance but never grade. A paper linked by a signal account is not
automatically better than one from PubMed; a paper linked by a hype_watch account
is not automatically worse. Grade the paper.

When two or more tracked accounts link the same paper, that is a relevance signal:
raise `relevance_score` by 1 in the filed article, capped at 10.

## Admin

The admin page has an "Add social account" card for Richie to add accounts.
The task may suggest accounts in `source_suggestions`; it never adds them itself.
