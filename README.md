# Longevity News — setup

Backend is already live in the `surety-article-tracker` Supabase project (tables `longevity_*`, edge function `longevity-queue-submit`, 38 interventions + 22 sources + 20 researchers seeded). Three things left, all yours:

1. **Commit these seven HTML files to the root of `Richiebuchanan/LongevityNews`** (main branch). Enable GitHub Pages: Settings → Pages → Deploy from branch → main / root. Site will be at `https://richiebuchanan.github.io/LongevityNews/`.
2. **Create the scheduled task** in the Claude app using `SCHEDULED_TASK_PROMPT.md`. Suggested 10:30 UTC so it doesn't overlap the surety run. Fire it once manually to populate Research Watch, Podcasts & Video, and the synthesis card — until then those pages show empty states (Interventions is populated already).
3. **Open `admin.html`** and confirm the password unlocks it.

Files:
- `baseline.html` — State of the Science: the living baseline + instruction manual (versioned, populated now)
- `index.html` — Research Watch (papers/preprints/news, evidence tier + relevance, 6-week synthesis card)
- `interventions.html` — the two-axis verdict table
- `media.html` — podcasts and YouTube
- All three of the above render footnote numbers and a Sources list from `longevity_references`
- `figures.html` — Envelope Pushers: profiles of Kurzweil, Johnson, Attia, Sinclair, de Grey, Kaeberlein, Huberman, Patrick, Longo, Altos, Retro, Hevolution (populated now)
- `admin.html` — intake forms (queue link, add intervention, add researcher, add source, add episode link)
- `overview.html` — about page with live counts
