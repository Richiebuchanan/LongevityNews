# Longevity News — candidate fetcher

Deterministic retrieval for the Longevity News pipeline. Runs on GitHub Actions daily,
pulls date-bounded results from PubMed, medRxiv/bioRxiv, the journal and curator RSS
feeds in `longevity_sources`, and the ClinicalTrials.gov watchlist, resolves true
publication dates through Crossref, and lands everything in `longevity_candidates`
with `status = 'unreviewed'`. It does not score, summarise, or file anything — the
Claude scheduled task does that every 3–4 days from the queue.

## Install (one time)

1. Copy the `fetcher/` folder into the `LongevityNews` repo root, so the layout is
   `fetcher/fetch_candidates.py`, `fetcher/requirements.txt`, and
   `.github/workflows/fetch.yml` at the repo root.
2. Repo → Settings → Secrets and variables → Actions → add:
   - `SUPABASE_URL` = `https://acxdvzcohjayvmqdaoke.supabase.co`
   - `SUPABASE_SERVICE_KEY` = the **service_role** key from Supabase → Project Settings → API.
     Never the anon key; never commit it. The workflow is the only place it's used.
   - `NCBI_API_KEY` (optional, free at ncbi.nlm.nih.gov/account) — lifts PubMed from 3 to 10 requests/sec.
   - `CONTACT_EMAIL` (optional) — goes in the User-Agent so Crossref/NCBI can reach you if the script misbehaves.
3. Actions tab → "Fetch longevity candidates" → Run workflow. First run uses a 5-day
   lookback; check the log, then the `longevity_candidates` table.

## Tables it touches

- `longevity_candidates` — insert only (upsert, ignore duplicates on `link` / `doi`).
- `longevity_trial_watch` — updates status, results-posted date, `changed_since_review`.
  Eight trials are seeded; six have NCT IDs entered from memory. The first run sets
  `last_status = 'NOT_FOUND'` on any that don't resolve — fix those by hand.
- Reads `longevity_search_terms` (active), `longevity_sources` (active, RSS, Journal
  or News/Magazine), `longevity_articles` (to skip links already filed).

## Tuning

- `LOOKBACK_DAYS` in the workflow env: 5 is right for a daily run (overlap catches
  outages). If you move the fetcher to every 3 days, set it to 7.
- PubMed volume is controlled by the query in `pubmed()`: each search term is ANDed
  with `humans OR RCT OR meta-analysis OR cohort OR clinical trial`. Loosen that if
  you want animal work; expect the queue to triple.
- `RX_KEYWORDS` gates the preprint servers and the RSS feeds. Add a term there when a
  new intervention joins the site.
- Journal feeds with `quality_tier = 1` are not keyword-filtered (everything they
  publish lands); tiers 2–3 are.

## What "recirculated" means

If a feed or PubMed entry is dated more than 30 days after the Crossref publication
date, `recirculated = true`. That's the Branyas case — a year-old paper re-run as news.
The task should file those with the true date and a note, or skip them if already on
the site.

## Failure modes

- A source's feed URL rots → that source is skipped with a warning; nothing else stops.
- Supabase rejects a row (bad date, constraint) → logged, the batch continues.
- Whole run fails → the Action shows red; the Claude task just sees a stale queue.
