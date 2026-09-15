/* Longevity News — glossary.js
   Loads glossary terms, annotates first occurrences in rendered content with hover/tap
   tooltips, and links each to glossary.html#slug (new tab). Include with:
     <script src="glossary.js" defer></script>
*/
(function () {
  "use strict";
  var SUPABASE_URL = "https://acxdvzcohjayvmqdaoke.supabase.co";
  var ANON_KEY = "sb_publishable_2n567u9zKgZ-L-M_yGRf5Q_HEV_p1-f";
  if (/glossary\.html$/i.test(location.pathname)) return;   // never annotate the glossary itself

  // Containers whose text we annotate; never inside these ancestors.
  var TARGET_SEL = "p, li, td, dd, .axis, .scope-note, .fig-tag, .entry-summary, .sos-item, .analysis-section";
  var SKIP_SEL = "a, button, label, select, option, input, textarea, h1, h2, h3, h4, .badge, .sp, .v-badge, .gloss-tip, .site-nav, .masthead, .filter-bar, .scope-toggle, code, .mono, .fn, sup";
  var terms = [], bySlug = {}, regex = null, tip = null, activeLink = null, touchMode = false;

  function esc(s){ return String(s == null ? "" : s).replace(/[&<>"']/g, function(c){ return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]; }); }
  function reEsc(s){ return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }

  function injectStyles(){
    var css = ""
      + ".gloss{color:inherit;text-decoration:none;border-bottom:1px dotted var(--accent,#0f7b6c);cursor:help;}"
      + ".gloss:hover,.gloss:focus-visible{border-bottom-style:solid;background:var(--accent-wash,rgba(15,123,108,.08));outline:none;border-radius:2px;}"
      + ".gloss-tip{position:absolute;z-index:60;max-width:320px;background:var(--surface,#fff);color:var(--ink,#1a1a1a);border:1px solid var(--border-strong,rgba(26,26,26,.22));border-radius:8px;padding:10px 12px;box-shadow:var(--shadow-2,0 8px 24px rgba(0,0,0,.12));font:13px/1.45 Inter,system-ui,sans-serif;text-decoration:none;display:none;}"
      + ".gloss-tip.is-open{display:block;}"
      + ".gloss-tip .gt-term{font-weight:700;font-size:13.5px;margin-bottom:3px;display:flex;justify-content:space-between;gap:10px;align-items:baseline;}"
      + ".gloss-tip .gt-cat{font-size:10px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted,#8a8a8a);font-weight:600;}"
      + ".gloss-tip .gt-range{margin-top:6px;font-size:12px;color:var(--ink-secondary,#4d4d4d);border-left:2px solid var(--ok,#1f8a4c);padding-left:8px;}"
      + ".gloss-tip .gt-more{display:block;margin-top:8px;font-size:12px;font-weight:600;color:var(--link,#0b6357);}"
      + "@media (hover:none){.gloss{cursor:pointer;}}";
    var s = document.createElement("style"); s.textContent = css; document.head.appendChild(s);
  }

  function buildRegex(){
    var alts = [];
    terms.forEach(function(t){
      [t.term].concat(t.aliases || []).forEach(function(a){
        a = (a || "").trim(); if (a.length < 2) return;
        alts.push({ s: a, slug: t.slug });
      });
    });
    alts.sort(function(a,b){ return b.s.length - a.s.length; });   // longest match wins
    var seen = {}; var parts = [];
    var exact = {};
    alts.forEach(function(a){ var k = a.s.toLowerCase(); if (seen[k]) return; seen[k] = a.slug; parts.push(reEsc(a.s));
      if (a.s.length <= 4 && a.s === a.s.toUpperCase()) exact[k] = a.s; });   // short acronyms (RCT, HR, CI, MR) must match case
    regex = new RegExp("(^|[^A-Za-z0-9+])(" + parts.join("|") + ")(?![A-Za-z0-9])", "gi");
    regex.lookup = seen; regex.exact = exact;
  }

  function cardOf(node){
    var el = node.nodeType === 1 ? node : node.parentElement;
    return (el && el.closest(".entry, .card, .fig-card, .tier, .analysis-section, article, li")) || document.body;
  }

  function annotate(root){
    if (!regex) return;
    var targets = root.matches && root.matches(TARGET_SEL) ? [root] : [];
    targets = targets.concat(Array.prototype.slice.call(root.querySelectorAll ? root.querySelectorAll(TARGET_SEL) : []));
    targets.forEach(function(el){
      if (el.dataset.glossed === "1" || el.closest(SKIP_SEL)) return;
      var walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, {
        acceptNode: function(n){
          if (!n.nodeValue || !/[A-Za-z]{3}/.test(n.nodeValue)) return NodeFilter.FILTER_REJECT;
          if (n.parentElement.closest(SKIP_SEL)) return NodeFilter.FILTER_REJECT;
          return NodeFilter.FILTER_ACCEPT;
        }
      });
      var nodes = []; while (walker.nextNode()) nodes.push(walker.currentNode);
      nodes.forEach(function(n){
        var card = cardOf(n); card._gloss = card._gloss || {};
        var text = n.nodeValue, last = 0, frag = null, m;
        regex.lastIndex = 0;
        while ((m = regex.exec(text))) {
          var key = m[2].toLowerCase(), slug = regex.lookup[key];
          if (!slug || card._gloss[slug]) continue;
          if (regex.exact[key] && regex.exact[key] !== m[2]) continue;           // first occurrence per card only
          card._gloss[slug] = 1;
          frag = frag || document.createDocumentFragment();
          var start = m.index + m[1].length;
          frag.appendChild(document.createTextNode(text.slice(last, start)));
          var a = document.createElement("a");
          a.className = "gloss"; a.href = "glossary.html#" + slug; a.target = "_blank"; a.rel = "noopener";
          a.dataset.slug = slug; a.textContent = m[2]; a.setAttribute("aria-describedby", "gloss-tip");
          frag.appendChild(a); last = start + m[2].length;
        }
        if (frag) { frag.appendChild(document.createTextNode(text.slice(last))); n.parentNode.replaceChild(frag, n); }
      });
      el.dataset.glossed = "1";
    });
  }

  function showTip(link){
    var t = bySlug[link.dataset.slug]; if (!t) return;
    activeLink = link;
    tip.innerHTML = '<div class="gt-term"><span>' + esc(t.term) + '</span><span class="gt-cat">' + esc(t.category) + '</span></div>'
      + '<div>' + esc(t.short_def) + '</div>'
      + (t.reference_range ? '<div class="gt-range">' + esc(t.reference_range) + '</div>' : '')
      + '<span class="gt-more">Full definition in the glossary ↗</span>';
    tip.href = link.href; tip.classList.add("is-open");
    var r = link.getBoundingClientRect(), tw = Math.min(320, window.innerWidth - 24);
    tip.style.maxWidth = tw + "px";
    var left = Math.max(12, Math.min(r.left + window.scrollX, window.scrollX + window.innerWidth - tw - 12));
    var top = r.bottom + window.scrollY + 6;
    tip.style.left = left + "px"; tip.style.top = top + "px";
    var th = tip.offsetHeight;
    if (r.bottom + th + 12 > window.innerHeight && r.top - th - 6 > 0) tip.style.top = (r.top + window.scrollY - th - 6) + "px";
  }
  function hideTip(){ tip.classList.remove("is-open"); activeLink = null; }

  function wireEvents(){
    tip = document.createElement("a"); tip.id = "gloss-tip"; tip.className = "gloss-tip"; tip.target = "_blank"; tip.rel = "noopener"; tip.setAttribute("role","tooltip");
    document.body.appendChild(tip);
    var hideTimer;
    document.addEventListener("mouseover", function(e){ var l = e.target.closest && e.target.closest("a.gloss"); if (l && !touchMode){ clearTimeout(hideTimer); showTip(l); } });
    document.addEventListener("mouseout", function(e){ var l = e.target.closest && e.target.closest("a.gloss"); if (l && !touchMode){ hideTimer = setTimeout(function(){ if (!tip.matches(":hover")) hideTip(); }, 150); } });
    tip.addEventListener("mouseleave", function(){ if (!touchMode) hideTip(); });
    document.addEventListener("focusin", function(e){ var l = e.target.closest && e.target.closest("a.gloss"); if (l) showTip(l); else if (!e.target.closest || !e.target.closest("#gloss-tip")) hideTip(); });
    document.addEventListener("keydown", function(e){ if (e.key === "Escape") hideTip(); });
    document.addEventListener("touchstart", function(){ touchMode = true; }, { passive: true });
    // Touch: first tap shows the tip, second tap (or tapping the tip) opens the glossary.
    document.addEventListener("click", function(e){
      var l = e.target.closest && e.target.closest("a.gloss");
      if (l && touchMode && activeLink !== l){ e.preventDefault(); showTip(l); return; }
      if (!l && !(e.target.closest && e.target.closest("#gloss-tip"))) hideTip();
    });
    window.addEventListener("scroll", function(){ if (touchMode) hideTip(); }, { passive: true });
  }

  function observe(){
    var main = document.querySelector("main") || document.body;
    annotate(main);
    var pending = false;
    new MutationObserver(function(muts){
      if (pending) return; pending = true;
      requestAnimationFrame(function(){ pending = false; muts.forEach(function(m){ m.addedNodes.forEach(function(n){ if (n.nodeType === 1) annotate(n); }); }); });
    }).observe(main, { childList: true, subtree: true });
  }

  function load(){
    fetch(SUPABASE_URL + "/rest/v1/longevity_glossary?select=slug,term,aliases,category,short_def,reference_range&status=eq.published",
          { headers: { apikey: ANON_KEY, Authorization: "Bearer " + ANON_KEY } })
      .then(function(r){ return r.ok ? r.json() : []; })
      .then(function(rows){
        if (!rows.length) return;
        terms = rows; rows.forEach(function(t){ bySlug[t.slug] = t; });
        buildRegex(); injectStyles(); wireEvents(); observe();
      })
      .catch(function(){ /* glossary is an enhancement; page works without it */ });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", load); else load();
})();
