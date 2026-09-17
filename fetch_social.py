#!/usr/bin/env python3
"""
Longevity News — Bluesky + newsletter fetcher.

Reads the longevity_social_accounts table, pulls recent posts/articles,
extracts links and DOIs, and lands them in longevity_candidates with
source='social'. Designed to run from the same GitHub Action as the
main fetcher, on the same schedule.

Env: same as fetch_candidates.py (SUPABASE_URL, SUPABASE_SERVICE_KEY, LOOKBACK_DAYS)
"""
import os, re, json, time, html, logging, datetime as dt
import requests
import feedparser

log = logging.getLogger("social")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
LOOKBACK = int(os.environ.get("LOOKBACK_DAYS", "5"))
CONTACT = os.environ.get("CONTACT_EMAIL", "longevity-news-fetcher")
UA = {"User-Agent": f"LongevityNewsFetcher/1.0 ({CONTACT})"}

TODAY = dt.date.today()
SINCE = TODAY - dt.timedelta(days=LOOKBACK)
SINCE_ISO = f"{SINCE}T00:00:00.000Z"

SB = {"apikey": SERVICE_KEY, "Authorization": f"Bearer {SERVICE_KEY}",
      "Content-Type": "application/json"}

DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"<>\]]+", re.I)
URL_RE = re.compile(r"https?://[^\s<>\")\]]+")
SKIP_DOMAINS = {"bsky.app", "bsky.social", "twitter.com", "x.com", "youtube.com",
                "youtu.be", "instagram.com", "facebook.com", "tiktok.com",
                "linkedin.com", "reddit.com", "tenor.com", "giphy.com"}

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
            log.error("upsert %s failed %s: %s", table, r.status_code, r.text[:300])
            continue
        n += len(chunk)
    return n

def sb_patch(table, match, payload):
    requests.patch(f"{SUPABASE_URL}/rest/v1/{table}", headers=dict(SB, Prefer="return=minimal"),
                   params=match, data=json.dumps(payload), timeout=30)

def norm_doi(s):
    if not s: return None
    m = DOI_RE.search(s)
    return m.group(0).rstrip(".;,)").lower() if m else None

def extract_links(text):
    """Return (dois, urls) from text, filtering out social-media links."""
    dois = {norm_doi(m) for m in DOI_RE.findall(text)} - {None}
    urls = set()
    for u in URL_RE.findall(text):
        u = u.rstrip(".,;:!?)")
        try:
            from urllib.parse import urlparse
            domain = urlparse(u).netloc.lower().lstrip("www.")
            if domain not in SKIP_DOMAINS:
                urls.add(u)
        except Exception:
            pass
    return dois, urls

# ---------------------------------------------------------------- Bluesky
BSKY_API = "https://public.api.bsky.app"

def fetch_bluesky(accounts):
    out = []
    bsky = [a for a in accounts if a["platform"] == "bluesky" and a.get("active")]
    for acct in bsky:
        handle = acct["handle"]
        try:
            # Resolve DID
            r = requests.get(f"{BSKY_API}/xrpc/com.atproto.identity.resolveHandle",
                             params={"handle": handle}, headers=UA, timeout=15)
            if r.status_code != 200:
                log.warning("bsky resolve %s: %s", handle, r.status_code); continue
            did = r.json().get("did")
            if not did: continue

            # Get recent feed
            params = {"actor": did, "limit": 50}
            r = requests.get(f"{BSKY_API}/xrpc/app.bsky.feed.getAuthorFeed",
                             params=params, headers=UA, timeout=30)
            if r.status_code != 200:
                log.warning("bsky feed %s: %s", handle, r.status_code); continue
            feed = r.json().get("feed", [])
        except Exception as e:
            log.warning("bsky %s: %s", handle, e); continue

        for item in feed:
            post = item.get("post", {})
            record = post.get("record", {})
            created = record.get("createdAt", "")
            if created < SINCE_ISO:
                continue

            text = record.get("text", "")
            # Also check embedded links
            embed = post.get("embed", {})
            external_uri = ""
            if embed.get("$type") == "app.bsky.embed.external#view":
                ext = embed.get("external", {})
                external_uri = ext.get("uri", "")
                text += " " + external_uri + " " + ext.get("title", "") + " " + ext.get("description", "")
            elif embed.get("$type") == "app.bsky.embed.record#view":
                rec = embed.get("record", {})
                if isinstance(rec, dict):
                    text += " " + (rec.get("value", {}) or {}).get("text", "")

            # Extract facet links too
            for facet in record.get("facets", []):
                for feat in facet.get("features", []):
                    if feat.get("$type") == "app.bsky.richtext.facet#link":
                        text += " " + feat.get("uri", "")

            dois, urls = extract_links(text)

            for doi in dois:
                link = f"https://doi.org/{doi}"
                out.append(dict(
                    doi=doi, link=link, title=f"[via @{handle}] {text[:120]}".strip(),
                    abstract=text[:2000], source="social", source_name="Bluesky",
                    social_handle=handle, search_term=acct.get("role"),
                    pub_date=created[:10], found_date=TODAY.isoformat(),
                    study_hint="other", recirculated=False
                ))

            if external_uri and not any(external_uri.startswith("https://doi.org") for _ in [1]):
                doi_in_url = norm_doi(external_uri)
                if doi_in_url and doi_in_url not in dois:
                    out.append(dict(
                        doi=doi_in_url, link=f"https://doi.org/{doi_in_url}",
                        title=f"[via @{handle}] {text[:120]}".strip(),
                        abstract=text[:2000], source="social", source_name="Bluesky",
                        social_handle=handle, search_term=acct.get("role"),
                        pub_date=created[:10], found_date=TODAY.isoformat(),
                        study_hint="other", recirculated=False
                    ))
                elif external_uri not in {f"https://doi.org/{d}" for d in dois}:
                    from urllib.parse import urlparse
                    domain = urlparse(external_uri).netloc.lower().lstrip("www.")
                    if domain not in SKIP_DOMAINS:
                        out.append(dict(
                            link=external_uri, title=f"[via @{handle}] {text[:120]}".strip(),
                            abstract=text[:2000], source="social", source_name="Bluesky",
                            social_handle=handle, search_term=acct.get("role"),
                            pub_date=created[:10], found_date=TODAY.isoformat(),
                            study_hint="other", recirculated=False
                        ))

        sb_patch("longevity_social_accounts", {"handle": f"eq.{handle}"},
                 {"last_fetched": dt.datetime.utcnow().isoformat() + "Z"})
        time.sleep(0.5)

    log.info("bluesky: %d raw links from %d accounts", len(out), len(bsky))
    return out

# ---------------------------------------------------------------- Newsletters / RSS
def fetch_newsletters(accounts):
    out = []
    nl = [a for a in accounts if a["platform"] in ("newsletter", "substack") and a.get("active") and a.get("feed_url")]
    for acct in nl:
        handle = acct["handle"]
        url = acct["feed_url"]
        try:
            f = feedparser.parse(url, request_headers=UA)
        except Exception as e:
            log.warning("newsletter %s: %s", handle, e); continue

        for entry in f.entries[:30]:
            d = entry.get("published_parsed") or entry.get("updated_parsed")
            if d and dt.date(*d[:3]) < SINCE:
                continue

            title = html.unescape(entry.get("title", "")).strip()
            summary = re.sub(r"<[^>]+>", " ", entry.get("summary", "") or "")[:3000]
            link = entry.get("link", "")
            if not link: continue

            doi = norm_doi(link) or norm_doi(summary)
            text = f"{title} {summary}"
            dois_in_text, _ = extract_links(text)

            # The main entry link
            out.append(dict(
                doi=doi, link=link, title=f"[via {acct.get('display_name', handle)}] {title}",
                abstract=summary[:2000], source="social", source_name=acct.get("display_name", handle),
                social_handle=handle, search_term=acct.get("role"),
                pub_date=dt.date(*d[:3]).isoformat() if d else TODAY.isoformat(),
                found_date=TODAY.isoformat(), study_hint="other", recirculated=False
            ))

            # Any DOIs mentioned in the body that aren't the entry link
            for extra_doi in dois_in_text:
                if extra_doi != doi:
                    out.append(dict(
                        doi=extra_doi, link=f"https://doi.org/{extra_doi}",
                        title=f"[via {acct.get('display_name', handle)}] cited in: {title[:100]}",
                        abstract=f"DOI extracted from newsletter entry: {title}", source="social",
                        source_name=acct.get("display_name", handle), social_handle=handle,
                        search_term=acct.get("role"), pub_date=dt.date(*d[:3]).isoformat() if d else TODAY.isoformat(),
                        found_date=TODAY.isoformat(), study_hint="other", recirculated=False
                    ))

        sb_patch("longevity_social_accounts", {"handle": f"eq.{handle}"},
                 {"last_fetched": dt.datetime.utcnow().isoformat() + "Z"})
        time.sleep(0.3)

    log.info("newsletters: %d raw links from %d feeds", len(out), len(nl))
    return out

# ---------------------------------------------------------------- main
def main():
    accounts = sb_get("longevity_social_accounts", {"select": "*", "active": "eq.true"})
    log.info("social fetch: %d active accounts, window %s..%s", len(accounts), SINCE, TODAY)

    raw = fetch_bluesky(accounts) + fetch_newsletters(accounts)

    # De-dup by DOI then link
    seen, merged = set(), []
    for c in raw:
        k = c.get("doi") or c["link"]
        if k in seen: continue
        seen.add(k); merged.append(c)

    # Skip already known
    existing = {r["link"] for r in sb_get("longevity_candidates", {"select": "link"})}
    existing |= {(r["doi"] or "").lower() for r in sb_get("longevity_candidates", {"select": "doi"}) if r.get("doi")}
    existing |= {r["link"] for r in sb_get("longevity_articles", {"select": "link"})}
    fresh = [c for c in merged if c["link"] not in existing and (c.get("doi") or "") not in existing]

    for c in fresh:
        c.setdefault("recirculated", False)
        c["found_date"] = TODAY.isoformat()

    n = sb_upsert("longevity_candidates", fresh, "link")
    log.info("social: inserted %d new candidates (%d raw, %d merged, %d already known)",
             n, len(raw), len(merged), len(merged) - len(fresh))

if __name__ == "__main__":
    try: main()
    except Exception as e:
        log.exception("social fetcher failed: %s", e); import sys; sys.exit(1)
