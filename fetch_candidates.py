#!/usr/bin/env python3
"""
Longevity News — deterministic candidate fetcher.

Pulls date-bounded results from PubMed, medRxiv/bioRxiv, journal RSS feeds and
ClinicalTrials.gov, resolves true publication dates via Crossref, de-duplicates by
DOI/link, and upserts into Supabase `longevity_candidates` (status='unreviewed') and
`longevity_trial_watch`. It never scores, summarises or files articles — that is the
Claude scheduled task's job.

Env:
  SUPABASE_URL          e.g. https://acxdvzcohjayvmqdaoke.supabase.co
  SUPABASE_SERVICE_KEY  service-role key (repo secret; never the anon key)
  LOOKBACK_DAYS         default 5 (overlap the cadence so nothing slips)
  NCBI_API_KEY          optional; raises PubMed rate limit
  CONTACT_EMAIL         optional; polite User-Agent for Crossref/NCBI
"""
import os, re, sys, json, time, html, logging, datetime as dt
from xml.etree import ElementTree as ET
import requests
import feedparser

log = logging.getLogger("fetch")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
LOOKBACK = int(os.environ.get("LOOKBACK_DAYS", "5"))
NCBI_KEY = os.environ.get("NCBI_API_KEY", "")
CONTACT = os.environ.get("CONTACT_EMAIL", "longevity-news-fetcher")
UA = {"User-Agent": f"LongevityNewsFetcher/1.0 ({CONTACT})"}

TODAY = dt.date.today()
SINCE = TODAY - dt.timedelta(days=LOOKBACK)

# ---------------------------------------------------------------- Supabase
SB = {"apikey": SERVICE_KEY, "Authorization": f"Bearer {SERVICE_KEY}",
      "Content-Type": "application/json"}

def sb_get(table, params):
    r = requests.get(f"{SUPABASE_URL}/rest/v1/{table}", headers=SB, params=params, timeout=30)
    r.raise_for_status(); return r.json()

def sb_upsert(table, rows, on_conflict):
    if not rows: return 0
    h = dict(SB, Prefer="resolution=ignore-duplicates,return=minimal")
    n = 0
    for i in range(0, len(rows), 50):
        chunk = rows[i:i+50]
        r = requests.post(f"{SUPABASE_URL}/rest/v1/{table}?on_conflict={on_conflict}",
                          headers=h, data=json.dumps(chunk), timeout=60)
        if r.status_code >= 300:
            log.error("upsert %s failed %s: %s", table, r.status_code, r.text[:300]); continue
        n += len(chunk)
    return n

def sb_patch(table, match, payload):
    r = requests.patch(f"{SUPABASE_URL}/rest/v1/{table}", headers=dict(SB, Prefer="return=minimal"),
                       params=match, data=json.dumps(payload), timeout=30)
    if r.status_code >= 300: log.error("patch %s failed: %s", table, r.text[:200])

# ---------------------------------------------------------------- helpers
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"<>]+", re.I)

def norm_doi(s):
    if not s: return None
    m = DOI_RE.search(s)
    return m.group(0).rstrip(".;,)") .lower() if m else None

def study_hint(pubtypes, title, source):
    t = (title or "").lower(); p = " ".join(pubtypes or []).lower()
    if source in ("medrxiv", "biorxiv"): return "preprint"
    if "meta-analysis" in p or "systematic review" in p or "meta-analysis" in t: return "meta"
    if "randomized controlled trial" in p or "clinical trial" in p or "randomi" in t: return "rct"
    if "cohort" in t or "prospective" in t or "biobank" in t: return "cohort"
    if re.search(r"\b(mice|mouse|murine|rat|rats|c\. elegans|drosophila|zebrafish)\b", t): return "animal"
    if "review" in p: return "review"
    return "other"

def crossref_date(doi):
    """Return (pub_date, journal) from Crossref, or (None, None)."""
    try:
        r = requests.get(f"https://api.crossref.org/works/{doi}", headers=UA, timeout=20)
        if r.status_code != 200: return None, None
        m = r.json()["message"]
        for k in ("published-online", "published-print", "issued", "created"):
            parts = m.get(k, {}).get("date-parts", [[None]])[0]
            if parts and parts[0]:
                y, mo, d = (parts + [1, 1])[:3]
                return dt.date(y, mo or 1, d or 1), (m.get("container-title") or [None])[0]
    except Exception as e:
        log.warning("crossref %s: %s", doi, e)
    return None, None

# ---------------------------------------------------------------- PubMed
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

def pubmed(terms):
    out = {}
    for term in terms:
        q = (f"({term}) AND (humans[MeSH] OR randomized controlled trial[pt] OR meta-analysis[pt] "
             f"OR cohort OR clinical trial[pt]) AND {SINCE:%Y/%m/%d}:{TODAY:%Y/%m/%d}[dp]")
        p = {"db": "pubmed", "term": q, "retmax": 40, "retmode": "json", "sort": "date"}
        if NCBI_KEY: p["api_key"] = NCBI_KEY
        try:
            ids = requests.get(f"{EUTILS}/esearch.fcgi", params=p, headers=UA, timeout=30).json()["esearchresult"]["idlist"]
        except Exception as e:
            log.warning("pubmed search '%s': %s", term, e); continue
        if not ids: continue
        p = {"db": "pubmed", "id": ",".join(ids), "retmode": "xml"}
        if NCBI_KEY: p["api_key"] = NCBI_KEY
        try:
            xml = requests.get(f"{EUTILS}/efetch.fcgi", params=p, headers=UA, timeout=60).text
        except Exception as e:
            log.warning("pubmed fetch: %s", e); continue
        for art in ET.fromstring(xml).iter("PubmedArticle"):
            pmid = art.findtext(".//PMID")
            title = "".join(art.find(".//ArticleTitle").itertext()) if art.find(".//ArticleTitle") is not None else ""
            abstract = " ".join("".join(a.itertext()) for a in art.findall(".//AbstractText"))
            journal = art.findtext(".//Journal/Title")
            doi = None
            for aid in art.findall(".//ArticleId"):
                if aid.get("IdType") == "doi": doi = norm_doi(aid.text)
            authors = ", ".join(f"{a.findtext('LastName','')} {a.findtext('Initials','')}".strip()
                                for a in art.findall(".//Author")[:6])
            ptypes = [pt.text for pt in art.findall(".//PublicationType")]
            d = art.find(".//ArticleDate") or art.find(".//PubDate")
            pub_date = None
            if d is not None and d.findtext("Year"):
                try: pub_date = dt.date(int(d.findtext("Year")), int(d.findtext("Month") or 1), int(d.findtext("Day") or 1))
                except ValueError: pass
            link = f"https://doi.org/{doi}" if doi else f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            key = doi or link
            if key in out: continue
            out[key] = dict(doi=doi, pmid=pmid, link=link, title=title.strip(), abstract=abstract[:6000],
                            authors=authors, journal=journal, source="pubmed", source_name="PubMed",
                            search_term=term, publication_type=ptypes, pub_date=pub_date.isoformat() if pub_date else None,
                            study_hint=study_hint(ptypes, title, "pubmed"))
        time.sleep(0.4 if NCBI_KEY else 1.0)
    log.info("pubmed: %d candidates", len(out)); return list(out.values())

# ---------------------------------------------------------------- medRxiv / bioRxiv
RX_CATS = {"medrxiv": {"geriatric medicine", "epidemiology", "nutrition", "endocrinology", "cardiovascular medicine",
                       "primary care research", "sports medicine"},
           "biorxiv": {"physiology", "molecular biology", "cell biology", "pharmacology and toxicology"}}
RX_KEYWORDS = re.compile(r"\b(aging|ageing|longevity|lifespan|healthspan|senescen|senolytic|geroscience|epigenetic (age|clock)|"
                         r"rapamycin|metformin|nad\+|nicotinamide|caloric restriction|frailty|sarcopenia|all-cause mortality|"
                         r"centenarian|biological age|reprogramming|glp-1|semaglutide|tirzepatide|VO2|resistance training)\b", re.I)

def rxiv(server):
    out, cursor = {}, 0
    while True:
        url = f"https://api.biorxiv.org/details/{server}/{SINCE:%Y-%m-%d}/{TODAY:%Y-%m-%d}/{cursor}"
        try:
            j = requests.get(url, headers=UA, timeout=30).json()
        except Exception as e:
            log.warning("%s: %s", server, e); break
        coll = j.get("collection", [])
        for it in coll:
            if it.get("version") not in ("1", 1): continue
            cat = (it.get("category") or "").lower()
            text = f"{it.get('title','')} {it.get('abstract','')}"
            if cat not in RX_CATS[server] and not RX_KEYWORDS.search(it.get("title", "")): continue
            if not RX_KEYWORDS.search(text): continue
            doi = norm_doi(it.get("doi"))
            if not doi or doi in out: continue
            out[doi] = dict(doi=doi, link=f"https://doi.org/{doi}", title=it.get("title", "").strip(),
                            abstract=(it.get("abstract") or "")[:6000], authors=(it.get("authors") or "")[:400],
                            journal=server, source=server, source_name=server, search_term=cat,
                            publication_type=["Preprint"], pub_date=it.get("date"), study_hint="preprint")
        total = int(j.get("messages", [{}])[0].get("total", 0) or 0)
        cursor += len(coll)
        if not coll or cursor >= total: break
    log.info("%s: %d candidates", server, len(out)); return list(out.values())

# ---------------------------------------------------------------- Journal / curator RSS
def rss(sources):
    out = {}
    for s in sources:
        url = s.get("url"); name = s.get("source_name")
        if not url or (s.get("access_method") or "").lower() != "rss": continue
        if (s.get("source_kind") or "") not in ("Journal", "News/Magazine"): continue   # podcasts go through the media pipeline
        try:
            f = feedparser.parse(url, request_headers=UA)
        except Exception as e:
            log.warning("rss %s: %s", name, e); continue
        for e in f.entries[:60]:
            d = e.get("published_parsed") or e.get("updated_parsed")
            if d and dt.date(*d[:3]) < SINCE: continue
            title = html.unescape(e.get("title", "")).strip()
            summary = re.sub(r"<[^>]+>", " ", e.get("summary", "") or "")
            if not RX_KEYWORDS.search(f"{title} {summary}") and (s.get("quality_tier") or 3) > 1: continue
            doi = norm_doi(e.get("dc_identifier") or e.get("id") or e.get("link") or summary)
            link = e.get("link") or (f"https://doi.org/{doi}" if doi else None)
            if not link or link in out: continue
            out[link] = dict(doi=doi, link=link, title=title, abstract=summary[:4000], journal=name,
                             source="rss", source_name=name, search_term=None, publication_type=[],
                             pub_date=dt.date(*d[:3]).isoformat() if d else None,
                             study_hint=study_hint([], title, "rss"))
    log.info("rss: %d candidates", len(out)); return list(out.values())

# ---------------------------------------------------------------- ClinicalTrials.gov watchlist
def trials(watch):
    for w in watch:
        nct = w["nct_id"]
        try:
            r = requests.get(f"https://clinicaltrials.gov/api/v2/studies/{nct}", headers=UA, timeout=30)
        except Exception as e:
            log.warning("ctgov %s: %s", nct, e); continue
        now = dt.datetime.utcnow().isoformat() + "Z"
        if r.status_code == 404:
            sb_patch("longevity_trial_watch", {"nct_id": f"eq.{nct}"}, {"last_status": "NOT_FOUND", "last_checked": now}); continue
        if r.status_code != 200: continue
        ps = r.json().get("protocolSection", {})
        st = ps.get("statusModule", {})
        status = st.get("overallStatus")
        results = st.get("resultsFirstPostDateStruct", {}).get("date")
        pcd = st.get("primaryCompletionDateStruct", {}).get("date")
        title = ps.get("identificationModule", {}).get("briefTitle")
        changed = (status != w.get("last_status")) or (results and results != w.get("results_first_posted"))
        payload = {"last_status": status, "results_first_posted": results, "last_checked": now,
                   "primary_completion_date": (pcd + "-01" if pcd and len(pcd) == 7 else pcd)}
        if changed:
            payload.update({"last_status_changed": TODAY.isoformat(), "changed_since_review": True})
            log.info("trial change %s: %s -> %s results=%s", nct, w.get("last_status"), status, results)
            sb_upsert("longevity_candidates", [dict(nct_id=nct, link=f"https://clinicaltrials.gov/study/{nct}",
                title=f"Trial update — {w['label']}: {title}", abstract=f"Status now {status}; results first posted {results or 'not yet'}.",
                source="clinicaltrials", source_name="ClinicalTrials.gov", search_term=w.get("related_intervention"),
                publication_type=["Trial Registry"], pub_date=TODAY.isoformat(), study_hint="trial_update")], "link")
        sb_patch("longevity_trial_watch", {"nct_id": f"eq.{nct}"}, payload)
        time.sleep(0.3)

# ---------------------------------------------------------------- main
def main():
    terms = [t["term"] for t in sb_get("longevity_search_terms", {"select": "term", "active": "eq.true"})]
    sources = sb_get("longevity_sources", {"select": "source_name,url,access_method,source_kind,quality_tier", "active": "eq.true"})
    watch = sb_get("longevity_trial_watch", {"select": "*", "active": "eq.true"})
    log.info("window %s..%s, %d terms, %d sources, %d trials", SINCE, TODAY, len(terms), len(sources), len(watch))

    cands = pubmed(terms) + rxiv("medrxiv") + rxiv("biorxiv") + rss(sources)

    # de-dup across sources by DOI then link
    seen, merged = set(), []
    for c in cands:
        k = c.get("doi") or c["link"]
        if k in seen: continue
        seen.add(k); merged.append(c)

    # skip anything already in candidates or already filed as an article
    existing = {r["link"] for r in sb_get("longevity_candidates", {"select": "link"})}
    existing |= {(r["doi"] or "").lower() for r in sb_get("longevity_candidates", {"select": "doi"}) if r.get("doi")}
    existing |= {r["link"] for r in sb_get("longevity_articles", {"select": "link"})}
    fresh = [c for c in merged if c["link"] not in existing and (c.get("doi") or "") not in existing]

    # Crossref: true publication date; flag re-circulated items (aggregator date >30d after pub)
    for c in fresh:
        if c.get("doi") and c["source"] in ("rss", "pubmed"):
            d, journal = crossref_date(c["doi"])
            if d:
                agg = dt.date.fromisoformat(c["pub_date"]) if c.get("pub_date") else TODAY
                c["recirculated"] = (agg - d).days > 30
                c["pub_date"] = d.isoformat()
                if journal and not c.get("journal"): c["journal"] = journal
            time.sleep(0.2)
        c.setdefault("recirculated", False)
        c["found_date"] = TODAY.isoformat()

    n = sb_upsert("longevity_candidates", fresh, "link")
    log.info("inserted %d new candidates (%d fetched, %d already known)", n, len(merged), len(merged) - len(fresh))
    trials(watch)

if __name__ == "__main__":
    try: main()
    except Exception as e:
        log.exception("fetcher failed: %s", e); sys.exit(1)
