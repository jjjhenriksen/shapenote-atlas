import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./docs.css";

const BASE_URL = import.meta.env.BASE_URL || "/";
const DOCS_ROOT = `${BASE_URL.replace(/\/?$/, "/")}docs/`;
const GUIDE_URL = "https://github.com/jjjhenriksen/shapenote-atlas/blob/main/docs/ATLAS_GUIDE.md";
const REPOSITORY_URL = "https://github.com/jjjhenriksen/shapenote-atlas";

const routes = {
  overview: DOCS_ROOT,
  gettingStarted: `${DOCS_ROOT}getting-started/`,
  reader: `${DOCS_ROOT}reader/`,
  evidence: `${DOCS_ROOT}evidence/`,
  maintainer: `${DOCS_ROOT}maintainer/`,
};

const pages = {
  overview: {
    label: "Overview",
    eyebrow: "Overview",
    title: "Shape-Note Atlas",
    lead: "A searchable, source-faithful reader and practice space for shape-note and Sacred Harp music.",
    sections: [["Browse docs", "browse-docs"], ["What the Atlas contains", "layers"]],
  },
  gettingStarted: {
    label: "Getting started",
    eyebrow: "Getting started",
    title: "Find your way around the Atlas",
    lead: "A short orientation to editions, search, and the detail pane before you start practicing.",
    sections: [["First visit", "first-visit"], ["Choose an edition", "choose-edition"], ["Find a tune", "find-tune"], ["Read the detail state", "detail-state"]],
  },
  reader: {
    label: "Reader",
    eyebrow: "Reader",
    title: "Read, practice, and transpose",
    lead: "Use the reader’s structured scores and controls while keeping the printed source in view.",
    sections: [["Reader workflow", "reader-workflow"], ["Practice and transpose", "practice"], ["Shapes and lyrics", "shapes"]],
  },
  evidence: {
    label: "Evidence",
    eyebrow: "Evidence",
    title: "Follow the evidence boundary",
    lead: "Understand what the Atlas knows, what it derives, and what remains open for human correction.",
    sections: [["Evidence states", "evidence-states"], ["Source policy", "source-policy"], ["Correct a published draft", "corrections"]],
  },
  maintainer: {
    label: "Maintainer reference",
    eyebrow: "Maintainer reference",
    title: "Maintain the corpus",
    lead: "Refresh generated artifacts and verify the browser bundle without collapsing source, review, and release claims.",
    sections: [["Data model", "data-model"], ["Data workflow", "data-workflow"], ["Verification", "verification"]],
  },
};

const navigation = [
  {
    label: "Overview",
    page: "overview",
    items: pages.overview.sections,
  },
  {
    label: "Getting started",
    page: "gettingStarted",
    items: pages.gettingStarted.sections,
  },
  {
    label: "Reader",
    page: "reader",
    items: pages.reader.sections,
  },
  {
    label: "Evidence",
    page: "evidence",
    items: pages.evidence.sections,
  },
  {
    label: "Maintainer reference",
    page: "maintainer",
    items: pages.maintainer.sections,
  },
];

function useStoredTheme() {
  const [theme, setTheme] = useState(() => {
    try {
      return window.localStorage.getItem("shape-note-atlas-docs-theme") || "dark";
    } catch {
      return "dark";
    }
  });

  function toggleTheme() {
    setTheme((current) => {
      const next = current === "dark" ? "light" : "dark";
      try {
        window.localStorage.setItem("shape-note-atlas-docs-theme", next);
      } catch {
        // The page remains usable when storage is unavailable.
      }
      return next;
    });
  }

  return [theme, toggleTheme];
}

function filteredNavigation(query) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return navigation;
  return navigation
    .map((group) => ({
      ...group,
      items: group.items.filter(([label]) => `${group.label} ${label}`.toLowerCase().includes(normalized)),
    }))
    .filter((group) => group.items.length);
}

function pageKeyFromPath() {
  const currentPath = window.location.pathname.replace(/\/+$/, "") || "/";
  const matches = Object.entries(routes).find(([, href]) => href.replace(/\/+$/, "") === currentPath);
  return matches ? matches[0] : "overview";
}

function Brand() {
  return <a className="docs-brand" href={BASE_URL} aria-label="Open the Shape-Note Atlas reader">
    <span className="docs-brand-mark" aria-hidden="true">◇</span>
    <span>Shape-Note Atlas</span>
    <span className="docs-badge">DOCS</span>
  </a>;
}

function Arrow() {
  return <span className="arrow" aria-hidden="true">↗</span>;
}

function Sidebar({ query, currentPage }) {
  const groups = filteredNavigation(query);
  return <aside className="docs-sidebar" aria-label="Documentation navigation">
    {groups.length ? groups.map((group) => <div className={`docs-nav-group${group.page === currentPage ? " current-group" : ""}`} key={group.label}>
      <div className="docs-nav-label">{group.label}</div>
      <nav>
        {group.items.map(([label, id]) => <a className={group.page === currentPage && id === pages[group.page].sections[0][1] ? "current" : ""} href={`${routes[group.page]}#${id}`} key={id}>{label}</a>)}
      </nav>
    </div>) : <p className="docs-nav-empty">No matching sections.</p>}
    <div className="docs-sidebar-spacer" />
    <a className="sidebar-guide-link" href={GUIDE_URL} target="_blank" rel="noreferrer noopener">Open the full maintainer guide <Arrow /></a>
  </aside>;
}

function FeatureCard({ eyebrow, title, description, href }) {
  return <a className="feature-card" href={href}>
    <span className="feature-icon" aria-hidden="true">{eyebrow}</span>
    <strong>{title}</strong>
    <span>{description}</span>
  </a>;
}

function Callout({ children, tone = "brass" }) {
  return <aside className={`docs-callout ${tone}`}><span className="callout-mark" aria-hidden="true">◇</span><div>{children}</div></aside>;
}

function CodeBlock({ children }) {
  return <pre className="docs-code"><code>{children}</code></pre>;
}

function OverviewContent() {
  return <>
    <Callout>
      <strong>The governing rule</strong>
      <p>A matching title is not proof of an edition match, and a playable draft is not a verified printed score.</p>
    </Callout>

    <section className="docs-section intro-section" id="browse-docs">
      <h2>Browse docs</h2>
      <p>Start with the page that matches your task. The documentation follows the same distinction the reader shows in its status labels.</p>
      <div className="feature-grid">
        <FeatureCard eyebrow="01" title="Getting started" description="Choose an edition, search the catalogue, and read a tune’s detail state." href={`${routes.gettingStarted}#first-visit`} />
        <FeatureCard eyebrow="02" title="Reader" description="Practice structured scores, transpose when the key is established, and read the shapes." href={`${routes.reader}#reader-workflow`} />
        <FeatureCard eyebrow="03" title="Evidence" description="Understand source identity, review drafts, correction paths, and certification." href={`${routes.evidence}#evidence-states`} />
        <FeatureCard eyebrow="04" title="Maintainer reference" description="Refresh generated artifacts and run the fail-closed verification lanes." href={`${routes.maintainer}#data-model`} />
      </div>
    </section>

    <section className="docs-section" id="layers">
      <h2>What the Atlas contains</h2>
      <p>The Atlas brings tune lookup, source links, structured MusicXML, four-shape rendering, and browser playback into one workspace. It keeps a catalogue record visible even when a tune does not yet have structured notation.</p>
      <div className="layer-list">
        <div><span className="layer-number">01</span><div><h3>Corpus metadata</h3><p>Tune numbers, titles, first lines, book membership, source links, edition relationships, and catalogue fields.</p></div></div>
        <div><span className="layer-number">02</span><div><h3>Structured notation</h3><p>MusicXML-derived parts and timing, loaded lazily when the selected edition has an admitted score asset.</p></div></div>
        <div><span className="layer-number">03</span><div><h3>Evidence and review work</h3><p>Source scans, recordings, OMR drafts, comparison candidates, correction packages, and validation ledgers.</p></div></div>
      </div>
      <p className="muted-note">The corpus currently represents eleven books and editions. Exact counts are generated data: inspect <code>public/corpus.json</code> and <code>public/source-coverage.json</code> when the current number matters.</p>
    </section>
  </>;
}

function GettingStartedContent() {
  return <>
    <section className="docs-section intro-section" id="first-visit">
      <h2>First visit</h2>
      <p>The Atlas is organized around editions rather than title strings alone. Open a book, select a tune, and treat the detail pane as the source of truth for what is currently usable.</p>
      <Callout tone="teal"><strong>Before you practice</strong><p>Confirm the selected book, page, first line, source links, and score or review status. Those fields tell you which evidence you are actually using.</p></Callout>
    </section>

    <section className="docs-section" id="choose-edition">
      <h2>Choose an edition</h2>
      <p>The same title or first line can occur in multiple books with different notation, lyrics, page numbers, or source history. Keep the edition selected in the reader while comparing evidence.</p>
      <div className="split-panel">
        <div><span className="panel-label">Book context</span><h3>Start with the printed witness</h3><p>Use the book and page relationship to identify the record you mean before opening a score.</p></div>
        <div><span className="panel-label">Record context</span><h3>Keep alternate witnesses labeled</h3><p>An alternate-edition score or recording can help, but it does not silently replace the selected edition.</p></div>
      </div>
    </section>

    <section className="docs-section" id="find-tune">
      <h2>Find a tune</h2>
      <p>Search by page, title, first line, or recorded source metadata. Narrow results by notation, key, mode, vocal part, transposability, or title/page order.</p>
      <ol className="docs-steps compact">
        <li><strong>Choose the search field.</strong> Begin with the value you know: title, first line, or page.</li>
        <li><strong>Apply filters only when useful.</strong> A missing filter value is not evidence that the tune lacks the attribute.</li>
        <li><strong>Open the detail pane.</strong> Review the record and its source state before using score controls.</li>
      </ol>
    </section>

    <section className="docs-section" id="detail-state">
      <h2>Read the detail state</h2>
      <p>Check the selected page, first line, source links, source health, and score or review status. A catalogue record can be useful even when structured notation is unavailable.</p>
      <Callout><p className="quote">The detail pane answers “what do I have?” before the practice controls answer “what can I do with it?”</p></Callout>
    </section>
  </>;
}

function ReaderContent() {
  return <>
    <section className="docs-section intro-section" id="reader-workflow">
      <h2>Reader workflow</h2>
      <ol className="docs-steps">
        <li><strong>Choose a book.</strong> The edition is part of a tune’s identity; the same title or first line can have different notation, lyrics, or page numbers elsewhere.</li>
        <li><strong>Find a tune.</strong> Search by page, title, first line, or recorded source metadata. Narrow results by notation, key, mode, vocal part, transposability, or title/page order.</li>
        <li><strong>Read the detail state.</strong> Check the selected page, first line, source links, source health, and score or review status before using practice controls.</li>
        <li><strong>Practice a structured score.</strong> Select parts and choose written order or an encoded repeat plan only when the score establishes safe repeat semantics.</li>
        <li><strong>Follow the evidence boundary.</strong> A source scan, alternate witness, or review draft can be useful without closing the selected edition’s mapping gap.</li>
      </ol>
    </section>

    <section className="docs-section" id="practice">
      <h2>Practice and transpose</h2>
      <p>For a structured score, choose the parts to hear, set a tempo between 40 and 220 BPM, and choose one to eight deliberate practice loops. Playback stops when selected parts, score version, source key, or target key changes.</p>
      <div className="split-panel">
        <div><span className="panel-label">Playback</span><h3>Written order is the safe fallback</h3><p>Encoded repeats are followed only when their semantics are explicitly supported. Unsupported navigation falls back to written order and is announced in the detail pane.</p></div>
        <div><span className="panel-label">Transposition</span><h3>Key evidence unlocks pitch changes</h3><p>If the source key is unknown, enter the key printed on the linked source page. That entry stays separate from catalogue metadata.</p></div>
      </div>
      <Callout tone="teal"><strong>Useful limitation</strong><p>When the key is not established, practice may still be available, but target-key transposition remains unavailable.</p></Callout>
    </section>

    <section className="docs-section" id="shapes">
      <h2>Shapes and lyrics</h2>
      <p>The shape legend distinguishes evidence from calculation. A displayed shape is either encoded by the witness, derived from an established key and exact pitch spelling, or unavailable because the source does not establish it.</p>
      <div className="evidence-grid">
        <div><span className="shape-dot source-dot" aria-hidden="true" /><strong>Source</strong><p>The notehead shape is encoded by the MusicXML witness.</p></div>
        <div><span className="shape-dot derived-dot" aria-hidden="true" /><strong>Derived</strong><p>A four-shape label is calculated from established pitch and key evidence.</p></div>
        <div><span className="shape-dot unavailable-dot" aria-hidden="true" /><strong>Unavailable</strong><p>The source does not establish the shape or key, so the Atlas leaves it blank.</p></div>
      </div>
      <p>The linked shape-source PDF remains the visual authority for printed glyphs. Missing lyrics, melismas, verses, repeats, endings, ties, slurs, and editorial markings stay visibly unavailable instead of being guessed.</p>
    </section>
  </>;
}

function EvidenceContent() {
  return <>
    <section className="docs-section intro-section" id="evidence-states">
      <h2>Evidence states</h2>
      <p>The reader keeps several concepts separate because they answer different questions:</p>
      <dl className="definition-list">
        <div><dt>Source identity</dt><dd>Does the URL, scan, PDF leaf, or catalogue row identify the intended record?</dd></div>
        <div><dt>Structured mapping</dt><dd>Is a parseable MusicXML asset associated with the selected edition?</dd></div>
        <div><dt>Review disposition</dt><dd>Has a draft been compared enough to be useful, rejected for mismatch, or blocked on unresolved evidence?</dd></div>
        <div><dt>Verified edition status</dt><dd>Has the exact selected edition’s required notation and source semantics passed the relevant review gates?</dd></div>
      </dl>
      <Callout><p className="quote">Source identity is not notation. Notation is not automatically edition certification. A passing build is not corpus completion.</p></Callout>
    </section>

    <section className="docs-section" id="source-policy">
      <h2>Source policy</h2>
      <p>The Atlas is not a replacement for the printed book or its authoritative scan. Alternate-edition scores, OMR output, source recordings, and comparison PDFs are valuable evidence and practice aids, but they do not silently become the selected edition’s engraving.</p>
      <p>Published review drafts are human-correctable: download the editable MusicXML, compare it with the untouched source, and use the linked correction path when needed. Every draft carries a version, evidence, hashes, and limitations. <code>safeToPromote</code> remains false until the required source-review gate is satisfied.</p>
    </section>

    <section className="docs-section" id="corrections">
      <h2>Correct a published draft</h2>
      <p>When a published review draft is available:</p>
      <ol className="docs-steps compact">
        <li>Download the editable MusicXML.</li>
        <li>Compare it with the untouched source page and evidence package.</li>
        <li>Preserve the original witness while editing in a notation editor.</li>
        <li>Use the pre-filled correction form if a correction should be proposed.</li>
      </ol>
    </section>
  </>;
}

function MaintainerContent() {
  return <>
    <section className="docs-section intro-section" id="data-model">
      <h2>Data model</h2>
      <p><code>public/corpus.json</code> is the application index. It contains books, songs, generated coverage, retained historical records, and provenance. Edition-scoped song values include metadata, structured scores, alternate reference witnesses, isolated drafts, and source coverage.</p>
      <div className="artifact-table" role="table" aria-label="Generated artifacts">
        <div className="artifact-row artifact-head" role="row"><span role="columnheader">Artifact</span><span role="columnheader">Purpose</span></div>
        {["source-coverage.json — Edition-scoped classification and next action.", "transcription-queue.json — Records without an exact structured score.", "human-review-queue.json — Drafts, dispositions, evidence, and correction metadata.", "source-comparison-ledger.json — Explicit source-versus-candidate comparisons.", "source-health.json — Network, evidence, and retention observations."].map((item) => { const [name, purpose] = item.split(" — "); return <div className="artifact-row" role="row" key={name}><code role="cell">public/{name}</code><span role="cell">{purpose}</span></div>; })}
      </div>
    </section>

    <section className="docs-section" id="data-workflow">
      <h2>Data workflow</h2>
      <p>The committed browser bundle can be served without the source checkout. Regeneration requires the established local source tree at <code>/Users/jacquelinehenriksen/sh-corpus-scripts</code> and refuses to create a partial bundle when required metadata is missing.</p>
      <CodeBlock>{`npm ci --ignore-scripts --no-audit --no-fund
python3 scripts/verify_dependencies.py
npm run prepare-data`}</CodeBlock>
      <p>Source-retention, image, recording, candidate, and review commands are separate because each has a different evidence boundary. Read the <a href={GUIDE_URL} target="_blank" rel="noreferrer noopener">full handoff and guide</a> before restoring retained evidence or resuming transcription work.</p>
    </section>

    <section className="docs-section" id="verification">
      <h2>Verification</h2>
      <p>Run focused checks after changing the corresponding layer, then use the fail-closed aggregate verifier:</p>
      <CodeBlock>{`python3 scripts/validate_data.py
python3 scripts/validate_playback.py
python3 scripts/validate_transposition.py
npm run verify-all`}</CodeBlock>
      <p>The aggregate check covers generated-artifact integrity, stale inputs, promotion safety, queue consistency, data, playback, transposition, source health, browser smoke when available, production build, and startup. Report local tests, browser proof, build status, push state, and deployment separately.</p>
    </section>
  </>;
}

const contentByPage = { overview: OverviewContent, gettingStarted: GettingStartedContent, reader: ReaderContent, evidence: EvidenceContent, maintainer: MaintainerContent };

function DocsPage() {
  const currentPage = pageKeyFromPath();
  const page = pages[currentPage];
  const PageContent = contentByPage[currentPage];
  const [query, setQuery] = useState("");
  const [theme, toggleTheme] = useStoredTheme();
  const searchRef = useRef(null);
  const matchingSections = useMemo(() => filteredNavigation(query).flatMap((group) => group.items.map(([label]) => label)), [query]);

  useEffect(() => {
    function focusSearch(event) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        searchRef.current?.focus();
      }
    }
    window.addEventListener("keydown", focusSearch);
    return () => window.removeEventListener("keydown", focusSearch);
  }, []);

  return <div className={`docs-app theme-${theme}`}>
    <header className="docs-header">
      <div className="docs-topline">
        <Brand />
        <label className="docs-search">
          <span className="search-icon" aria-hidden="true">⌕</span>
          <span className="sr-only">Search documentation</span>
          <input ref={searchRef} value={query} onChange={(event) => setQuery(event.target.value)} type="search" placeholder="Search documentation…" aria-label="Search documentation" />
          <kbd>⌘ K</kbd>
        </label>
        <div className="docs-header-actions">
          <a href={REPOSITORY_URL} target="_blank" rel="noreferrer noopener" aria-label="Open Shape-Note Atlas on GitHub">GitHub</a>
          <button className="theme-button" type="button" onClick={toggleTheme} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}>{theme === "dark" ? "☼" : "☾"}</button>
        </div>
      </div>
      <nav className="docs-category-nav" aria-label="Documentation categories">
        {["overview", "gettingStarted", "reader", "evidence", "maintainer"].map((key) => <a className={key === currentPage ? "active" : ""} href={routes[key]} key={key}>{pages[key].label}</a>)}
        <a className="category-reader-link" href={BASE_URL}>Open reader <Arrow /></a>
      </nav>
    </header>

    <div className="docs-layout">
      <Sidebar query={query} currentPage={currentPage} />

      <main className="docs-main" id="top">
        <div className="docs-breadcrumb">Docs <span>/</span> {page.label} <span>/</span> {page.title}</div>
        <div className="docs-article-actions"><a href={BASE_URL}>Open reader <Arrow /></a><a href={GUIDE_URL} target="_blank" rel="noreferrer noopener">View source <Arrow /></a></div>
        <div className="docs-kicker">{page.eyebrow}</div>
        <h1>{page.title}</h1>
        <p className="docs-lead">{page.lead}</p>

        <PageContent />

        <footer className="docs-footer"><span>Shape-Note Atlas documentation</span><span><a href={BASE_URL}>Open reader</a><span className="footer-divider">·</span><a href={REPOSITORY_URL} target="_blank" rel="noreferrer noopener">Source on GitHub</a></span></footer>
      </main>

      <aside className="docs-toc" aria-label="On this page">
        <div className="toc-label">On this page</div>
        <nav>{page.sections.map(([label, id]) => <a href={`#${id}`} key={id}>{label}</a>)}</nav>
        {query && <p className="toc-search-state">{matchingSections.length} matching navigation link{matchingSections.length === 1 ? "" : "s"}</p>}
      </aside>
    </div>
  </div>;
}

createRoot(document.getElementById("root")).render(<DocsPage />);
