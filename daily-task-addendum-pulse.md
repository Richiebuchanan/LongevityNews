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

## Voices maintenance (added 2026-09-17)

`longevity_voices` profiles the science communicators, YouTubers and podcast hosts the site's readers encounter. Each carries a `signal_quality` grade (generally reliable / mixed / treat with caution), a `signal_note` and a `watch_for`.

Each run, after filing media episodes:
1. If the episode's host or guest is in `longevity_voices`, check the episode content against that voice's `signal_quality` and `watch_for`. If the episode contains a factual error, an undisclosed conflict, or a claim that contradicts the site's graded evidence, note it in the media row's `evidence_quality_note` and flag the voice for review in the run log.
2. If a pattern emerges across three or more episodes (persistent overclaiming, new undisclosed sponsorship, a correction or public stance change), update the voice's `signal_note`, `watch_for`, or `signal_quality` with a `last_reviewed` date and note the change in the run log.
3. Never downgrade a voice on a single episode; never upgrade without at least three consistent data points.
4. When the Pulse's `studies_surfaced` section includes a study a voice discussed, note in the Pulse whether the voice's framing matched the site's grade or diverged, and in which direction.
5. New voices: when a media entry names a host or guest not in the table and the host has a recurring show with >50k subscribers/followers, draft a row with `signal_quality` based on the episodes reviewed so far; note it in the run log for Richie to approve. Never publish a draft voice entry without approval.
6. Platform links (`youtube_url`, `spotify_url`, `apple_url`, `x_url`, `instagram_url`, `bluesky_url`, `website_url`, `newsletter_url`, `tiktok_url`): fill any that are null when you encounter the voice's content on that platform. These are factual and do not need approval.

## Quarterly and Annual Evidence Reviews (added 2026-09-17)

`longevity_reviews` holds two living documents — a quarterly and an annual — that are **updated every run** when something warrants it, not frozen until the period ends.

### Update rules (every run):

**Check whether this run produced any of these triggers:**
- A verdict changed on an intervention
- A new intervention was added
- A trial on the watchlist reported results or changed status
- State of the Science published a new version
- A topic page published a new version
- A landmark study was filed
- A new Envelope Pusher or Voice was added

**If any trigger fired → update the current quarterly:**
1. Read the current quarterly (`review_type='quarterly'`, latest `period_label`).
2. Edit the relevant section of the `document` JSON in place (add to `verdict_changes`, append to `interventions_added`, update `trials_reported`, etc.).
3. Rewrite `summary` to reflect the quarter so far, not just this run.
4. Update `the_one_thing` only if this run's trigger is more consequential than the current one.
5. Update `watch_next` if a watched item reported or a new one appeared.
6. Set `last_updated` to now; increment `version` only if the change is structural (new section, rewritten summary), not for an append.

**If the quarterly changed → check whether the annual needs it too:**
- A verdict change, a State of the Science revision, or a topic page v2+ always propagates to the annual.
- A new intervention or landmark does not, unless it is consequential enough to change `what_changed_for_a_reader`.
- Rewrite `summary` and `where_things_stand` only when the picture genuinely shifted, not on every append.

### Period transitions:
- **New quarter:** On the first run after the quarter boundary (Jan 1, Apr 1, Jul 1, Oct 1), create a new quarterly row with a fresh `period_label` (e.g. 'Q4 2026'), `period_start/end`, and an initial `document` seeded from the just-ended quarter's `watch_next`. The old quarterly stays as an archive.
- **New year:** On the first run after Jan 1, archive the current annual (set `published=false` or keep for history) and create a fresh one seeded from the last quarterly's summary and the prior annual's `what_to_watch`.

### If no trigger fired:
Do nothing to the reviews. A run that only filed articles and wrote a Pulse does not touch them. "Nothing changed" is a valid state.

### The old `longevity_synthesis` table:
Deprecated. Do not write to it. The Pulse replaces its weekly function; the quarterly replaces its synthesis function.
