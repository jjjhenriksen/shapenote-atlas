import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./docs.css";

const BASE_URL = import.meta.env.BASE_URL || "/";
const GUIDE_URL = "https://github.com/jjjhenriksen/shapenote-atlas/blob/main/docs/ATLAS_GUIDE.md";
const REPOSITORY_URL = "https://github.com/jjjhenriksen/shapenote-atlas";

const navigation = [
  {
    label: "Overview",
    items: [
      ["Shape-Note Atlas", "top"],
      ["Start here", "start-here"],
      ["What the Atlas contains", "layers"],
      ["Evidence states", "evidence-states"],
      ["Source policy", "source-policy"],
    ],
  },
  {
    label: "Reader",
    items: [
      ["Reader workflow", "reader-workflow"],
      ["Practice and transpose", "practice"],
      ["Shapes and lyrics", "shapes"],
      ["Correct a published draft", "corrections"],
    ],
  },
  {
    label: "Maintainer reference",
    items: [
      ["Data model", "data-model"],
      ["Data workflow", "data-workflow"],
      ["Verification", "verification"],
    ],
  },
];

const pageSections = [
  ["Browse docs", "start-here"],
  ["What the Atlas contains", "layers"],
  ["Reader workflow", "reader-workflow"],
  ["Practice and transpose", "practice"],
  ["Evidence states", "evidence-states"],
  ["Data model", "data-model"],
  ["Verification", "verification"],
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
      items: group.items.filter(([label]) => label.toLowerCase().includes(normalized)),
    }))
    .filter((group) => group.items.length);
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

function Sidebar({ query }) {
  const groups = filteredNavigation(query);
  return <aside className="docs-sidebar" aria-label="Documentation navigation">
    {groups.length ? groups.map((group) => <div className="docs-nav-group" key={group.label}>
      <div className="docs-nav-label">{group.label}</div>
      <nav>
        {group.items.map(([label, id], index) => <a className={index === 0 && id === "top" ? "current" : ""} href={`#${id}`} key={id}>{label}</a>)}
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

function DocsPage() {
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
        {["Overview", "Reader", "Evidence", "Maintainer reference"].map((label, index) => <a className={index === 0 ? "active" : ""} href={`#${["top", "reader-workflow", "evidence-states", "data-model"][index]}`} key={label}>{label}</a>)}
        <a className="category-reader-link" href={BASE_URL}>Open reader <Arrow /></a>
      </nav>
    </header>

    <div className="docs-layout">
      <Sidebar query={query} />

      <main className="docs-main" id="top">
        <div className="docs-breadcrumb">Docs <span>/</span> Overview <span>/</span> Shape-Note Atlas</div>
        <div className="docs-article-actions"><a href={BASE_URL}>Open reader <Arrow /></a><a href={GUIDE_URL} target="_blank" rel="noreferrer noopener">View source <Arrow /></a></div>
        <div className="docs-kicker">Overview</div>
        <h1>Shape-Note Atlas</h1>
        <p className="docs-lead">A searchable, source-faithful reader and practice space for shape-note and Sacred Harp music.</p>

        <Callout>
          <strong>The governing rule</strong>
          <p>A matching title is not proof of an edition match, and a playable draft is not a verified printed score.</p>
        </Callout>

        <section className="docs-section intro-section" id="start-here">
          <h2>Browse docs</h2>
          <p>Use the Atlas to find tunes, inspect the evidence attached to a selected edition, and practice only the material whose source boundary is clear. The documentation follows the same distinction the reader shows in its status labels.</p>
          <div className="feature-grid">
            <FeatureCard eyebrow="01" title="Reader workflow" description="Search the corpus, choose an edition, and read the detail state before practicing." href="#reader-workflow" />
            <FeatureCard eyebrow="02" title="Evidence states" description="Understand the difference between a source record, notation, a draft, and certification." href="#evidence-states" />
            <FeatureCard eyebrow="03" title="Practice safely" description="Use structured scores, encoded repeats, and key evidence without borrowing across editions." href="#practice" />
            <FeatureCard eyebrow="04" title="Maintain the corpus" description="Refresh generated artifacts and run the fail-closed verification lanes." href="#data-workflow" />
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

        <section className="docs-section" id="reader-workflow">
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

        <section className="docs-section" id="evidence-states">
          <h2>Evidence states</h2>
          <p>The reader keeps several concepts separate because they answer different questions:</p>
          <div className="definition-list">
            <div><dt>Source identity</dt><dd>Does the URL, scan, PDF leaf, or catalogue row identify the intended record?</dd></div>
            <div><dt>Structured mapping</dt><dd>Is a parseable MusicXML asset associated with the selected edition?</dd></div>
            <div><dt>Review disposition</dt><dd>Has a draft been compared enough to be useful, rejected for mismatch, or blocked on unresolved evidence?</dd></div>
            <div><dt>Verified edition status</dt><dd>Has the exact selected edition’s required notation and source semantics passed the relevant review gates?</dd></div>
          </div>
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

        <section className="docs-section" id="data-model">
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

        <footer className="docs-footer"><span>Shape-Note Atlas documentation</span><span><a href={BASE_URL}>Open reader</a><span className="footer-divider">·</span><a href={REPOSITORY_URL} target="_blank" rel="noreferrer noopener">Source on GitHub</a></span></footer>
      </main>

      <aside className="docs-toc" aria-label="On this page">
        <div className="toc-label">On this page</div>
        <nav>{pageSections.map(([label, id]) => <a href={`#${id}`} key={id}>{label}</a>)}</nav>
        {query && <p className="toc-search-state">{matchingSections.length} matching navigation link{matchingSections.length === 1 ? "" : "s"}</p>}
      </aside>
    </div>
  </div>;
}

createRoot(document.getElementById("root")).render(<DocsPage />);
