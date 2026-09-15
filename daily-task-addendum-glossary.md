# Task addendum — glossary maintenance (added 2026-09-15)

`longevity_glossary` holds every technical term the site uses (slug, term, aliases, category, short_def for the tooltip, long_plain and long_technical for the glossary page, reference_range for biomarkers, related slugs, refs). Only rows with `status = 'published'` appear on the site.

Each run, after filing articles and interventions:

1. Scan the text you wrote for technical terms (biomarkers, study designs, mechanisms, drug classes, statistics) that are not in the glossary — check `term` and `aliases`, case-insensitive.
2. For each missing term, insert a row with `status = 'draft'`: one-sentence plain `short_def`, a 3–5 sentence `long_plain` a non-scientist can follow, a 2–3 sentence `long_technical`, `reference_range` if it is a measurable value, and `related` slugs. Category from the fixed list. Never publish a draft yourself; Richie approves.
3. If a filed article uses an alias the glossary lacks for an existing term (e.g. a new brand name for a drug class), append it to `aliases` — that one you may do directly.
4. Definitions must be your own words; cite a reference in `refs` when a reference range or statistic comes from a specific source.
5. Note the count of new drafts in the run log.
