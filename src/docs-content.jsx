import React from "react";

function Section({ id, title, children, className = "" }) {
  return <section className={`docs-section ${className}`.trim()} id={id}>
    <h2>{title}</h2>
    {children}
  </section>;
}

function Callout({ children, tone = "brass" }) {
  return <aside className={`docs-callout ${tone}`}>
    <span className="callout-mark" aria-hidden="true">◇</span>
    <div>{children}</div>
  </aside>;
}

function CodeBlock({ children }) {
  return <pre className="docs-code"><code>{children}</code></pre>;
}

function Steps({ items, compact = false }) {
  return <ol className={`docs-steps${compact ? " compact" : ""}`}>
    {items.map((item, index) => <li key={index}>{item}</li>)}
  </ol>;
}

function FeatureCard({ eyebrow, title, description, href }) {
  return <a className="feature-card" href={href}>
    <span className="feature-icon" aria-hidden="true">{eyebrow}</span>
    <strong>{title}</strong>
    <span>{description}</span>
  </a>;
}

function LinkCard({ label, title, description, href, external = false }) {
  return <a className="link-card" href={href} {...(external ? { target: "_blank", rel: "noreferrer noopener" } : {})}>
    <span className="panel-label">{label}</span>
    <strong>{title} <span className="arrow" aria-hidden="true">↗</span></strong>
    <span>{description}</span>
  </a>;
}

function DefinitionList({ items }) {
  return <dl className="definition-list">
    {items.map(([term, definition], index) => <div key={index}><dt>{term}</dt><dd>{definition}</dd></div>)}
  </dl>;
}

function Table({ headers, rows, caption }) {
  return <div className="docs-table-wrap">
    {caption && <div className="table-caption">{caption}</div>}
    <table className="docs-table">
      <thead><tr>{headers.map((header) => <th key={header}>{header}</th>)}</tr></thead>
      <tbody>{rows.map((row, index) => <tr key={index}>{row.map((cell, cellIndex) => <td key={cellIndex}>{cell}</td>)}</tr>)}</tbody>
    </table>
  </div>;
}

function ArtifactTable() {
  return <Table
    caption="Committed public artifacts and what they are for"
    headers={["Artifact", "Role"]}
    rows={[
      [<code>public/corpus.json</code>, "Application index: books, songs, coverage summaries, edition metadata, and lazy score references."],
      [<code>public/scores/</code>, "Full structured score assets admitted to the selected edition."],
      [<code>public/draft-scores/</code>, "Isolated review and published-draft assets; never an automatic promotion signal."],
      [<code>public/source-coverage.json</code>, "Edition-scoped status and next safe action for each record."],
      [<code>public/transcription-queue.json</code>, "Records without an exact structured score, with source links and blockers."],
      [<code>public/human-review-queue.json</code>, "Draft dispositions, evidence, correction metadata, and publication state."],
      [<code>public/source-comparison-ledger.json</code>, "Explicit source-versus-candidate comparisons; not automatic certification."],
      [<code>public/source-health.json</code>, "Network, evidence, and retention observations with cached/offline state preserved."],
    ]}
  />;
}

function OverviewContent({ routes, guideUrl, repositoryUrl, imageUrl }) {
  return <>
    <Callout>
      <strong>The governing rule</strong>
      <p>A matching title is not proof of an edition match, and a playable draft is not a verified printed score.</p>
    </Callout>

    <Section id="start-here" title="A map, not a monolith" className="intro-section">
      <p>The Atlas documentation is organized the way the product is used: first orient yourself, then learn the reader, then inspect evidence, then maintain the corpus. Each page is deliberately narrow enough to bookmark and cross-reference.</p>
      <div className="feature-grid">
        <FeatureCard eyebrow="01" title="Start here" description="Get a tune on screen, choose the right edition, and learn the vocabulary." href={routes.gettingStarted} />
        <FeatureCard eyebrow="02" title="Use the reader" description="Search, inspect a tune, practice a structured score, and transpose with evidence." href={routes.browse} />
        <FeatureCard eyebrow="03" title="Follow evidence" description="Understand source identity, coverage states, drafts, and correction paths." href={routes.evidence} />
        <FeatureCard eyebrow="04" title="Maintain the corpus" description="Refresh generated artifacts, run checks, and contribute without flattening uncertainty." href={routes.maintainer} />
      </div>
    </Section>

    <Section id="the-atlas" title="What the Atlas is">
      <p>The Shape-Note Atlas is a searchable, source-faithful lookup and practice workspace for shape-note and Sacred Harp repertory. It keeps a catalogue record visible even when a tune does not yet have structured notation, and it exposes the boundary between source evidence, practice material, and verified edition data.</p>
      <div className="layer-list">
        <div><span className="layer-number">01</span><div><h3>Corpus metadata</h3><p>Tune numbers, titles, first lines, book membership, source links, edition relationships, and catalogue fields.</p></div></div>
        <div><span className="layer-number">02</span><div><h3>Structured notation</h3><p>MusicXML-derived parts and timing, loaded lazily when the selected edition has an admitted score asset.</p></div></div>
        <div><span className="layer-number">03</span><div><h3>Evidence and review work</h3><p>Source scans, recordings, OMR drafts, comparison candidates, correction packages, and validation ledgers.</p></div></div>
      </div>
    </Section>

    <Section id="documentation-map" title="Documentation map">
      <p>Choose a route by the question you are trying to answer. The same separation appears in the reader’s status labels and in the generated data model.</p>
      <div className="link-card-grid">
        <LinkCard label="Begin" title="Quickstart" description="The shortest path from a local checkout to a first tune." href={routes.gettingStarted} />
        <LinkCard label="Understand" title="Editions & records" description="Why book identity matters and how deep links stay specific." href={routes.concepts} />
        <LinkCard label="Practice" title="Playback" description="Parts, tempo, loops, repeat plans, and cancellation behavior." href={routes.practice} />
        <LinkCard label="Trust" title="Evidence model" description="What source identity, structured mapping, review, and certification each mean." href={routes.evidence} />
        <LinkCard label="Build" title="Data pipeline" description="How source-dependent inputs become a committed browser bundle." href={routes.pipeline} />
        <LinkCard label="Ship" title="Verification" description="Focused checks, aggregate verification, receipts, and honest reporting." href={routes.verification} />
      </div>
    </Section>

    <Section id="scope" title="Current scope">
      <p>The committed corpus represents eleven books and editions, including Sacred Harp 1991, Sacred Harp 2025, Cooper Book 2012, The Christian Harmony, The Shenandoah Harmony, The Southern Harmony, A Supplement to the Kentucky Harmony, The Social Harp, The Minnesota Harmony, Sacred Harp Tunes, and The Trumpet.</p>
      <p className="muted-note">Coverage counts are generated data. When an exact current count matters, inspect the <code>generatedAt</code> and <code>coverage</code> fields in <code>public/corpus.json</code> and <code>public/source-coverage.json</code>.</p>
    </Section>

    <figure className="docs-figure">
      <img src={imageUrl} alt="The Shape-Note Atlas reader showing a tune catalogue and score preview" />
      <figcaption>The reader keeps catalogue context, evidence labels, and practice controls in one workspace.</figcaption>
    </figure>

    <Section id="source-links" title="Primary project sources">
      <div className="link-card-grid compact-grid">
        <LinkCard label="Maintainer source" title="Atlas guide" description="The longer reader and maintainer reference in Markdown." href={guideUrl} external />
        <LinkCard label="Repository" title="Source on GitHub" description="Application code, generated public bundle, tests, and scripts." href={repositoryUrl} external />
      </div>
    </Section>
  </>;
}

function GettingStartedContent({ routes }) {
  return <>
    <Section id="install" title="Install and run" className="intro-section">
      <p>The browser bundle can be served from committed <code>public/</code> data. A normal reader session does not require the source checkout used to regenerate the corpus.</p>
      <CodeBlock>{`npm ci --ignore-scripts --no-audit --no-fund
npm run dev`}</CodeBlock>
      <p>Open the local URL printed by Vite. The development server binds to <code>127.0.0.1</code>. For a production-like static preview, run <code>npm run build</code> followed by <code>npm run preview</code>.</p>
    </Section>

    <Section id="first-session" title="Your first session">
      <Steps items={[
        <><strong>Choose a book.</strong> Use the <strong>Tune book</strong> picker. The selected edition is part of the tune’s identity.</>,
        <><strong>Find a tune.</strong> Search a page number, title, first line, or source metadata.</>,
        <><strong>Open the detail pane.</strong> Check the page, first line, links, source health, and notation status.</>,
        <><strong>Choose the appropriate action.</strong> Practice a structured score, inspect the source, or follow the next safe evidence step.</>,
      ]} />
    </Section>

    <Section id="what-to-check" title="What to check before practicing">
      <p>Do not start with the play button. Start with record identity. Confirm the book, page, first line, and source links; then read the status badge and key evidence. This takes seconds and prevents a plausible score from being mistaken for the selected printed edition.</p>
      <Callout tone="teal"><strong>A useful habit</strong><p>Ask “what record is this?” before asking “what can I do with it?”</p></Callout>
    </Section>

    <Section id="next-pages" title="Next pages">
      <div className="link-card-grid compact-grid">
        <LinkCard label="Context" title="Editions & records" description="Learn why a title match is not enough." href={routes.concepts} />
        <LinkCard label="Reader" title="Browse & search" description="Learn the search fields and filters." href={routes.browse} />
        <LinkCard label="Practice" title="Practice & playback" description="Understand controls, repeats, and stop conditions." href={routes.practice} />
      </div>
    </Section>
  </>;
}

function ConceptsContent({ routes }) {
  return <>
    <Section id="edition-identity" title="Edition identity" className="intro-section">
      <p>The Atlas is organized around editions, not title strings alone. The same title or first line can occur in multiple books with different notation, lyrics, page numbers, source history, or editorial treatment.</p>
      <Callout><p className="quote">A tune number, title, first line, and book relationship together identify the record the reader is showing.</p></Callout>
    </Section>

    <Section id="record-layers" title="One record, several layers">
      <DefinitionList items={[
        ["Catalogue metadata", "The record’s title, first line, book membership, page, source links, and edition-scoped fields."],
        ["Selected-edition score", "A structured score attached to the book currently selected in the reader."],
        ["Alternate witness", "A score from another edition or source, explicitly labeled and never silently substituted."],
        ["Review draft", "A versioned transcription or OMR result retained for comparison, correction, and—when its contract permits—practice."],
      ]} />
      <p>These layers can coexist. An alternate witness can be useful while the selected edition still has a mapping gap.</p>
    </Section>

    <Section id="deep-links" title="Share a specific tune">
      <p>The detail pane’s <strong>Link to this tune</strong> link preserves the selected book and tune query parameters. A shared link is therefore tied to the edition context instead of depending on someone else’s current search state.</p>
      <CodeBlock>{`?book=sh1991&tune=26-samaria`}</CodeBlock>
      <p>If a deep link names an unknown book or a tune that does not belong to that edition, the reader fails closed and asks the user to search or choose another book.</p>
    </Section>

    <Section id="edition-comparisons" title="Compare without collapsing">
      <Table
        headers={["Question", "Use", "Do not infer"]}
        rows={[
          ["Is this the intended record?", "Book, page, title, first line, and source identity", "That a score exists"],
          ["Can I render or practice it?", "An admitted structured asset and valid playback data", "That it matches every printed detail"],
          ["Can I transpose it?", "Established or explicitly entered source key", "A key borrowed from another edition"],
          ["Is the edition certified?", "The relevant direct source-review gates", "A green build or matching title"],
        ]}
      />
    </Section>
  </>;
}

function BrowseContent() {
  return <>
    <Section id="search-fields" title="Search fields" className="intro-section">
      <p>Library, Practice, and Sources share the same catalogue results. Search matches tune/page metadata, title, first line, and recorded source metadata. Use the field you know first; broad text search is useful when you only have a fragment.</p>
      <div className="evidence-grid">
        <div><span className="shape-dot source-dot" aria-hidden="true" /><strong>Page & number</strong><p>Find a printed tune number or page relationship within the selected edition.</p></div>
        <div><span className="shape-dot derived-dot" aria-hidden="true" /><strong>Title & first line</strong><p>Search the catalogue’s normalized and displayed text without assuming edition equivalence.</p></div>
        <div><span className="shape-dot unavailable-dot" aria-hidden="true" /><strong>Source metadata</strong><p>Find records by a source URL, recording, coverage label, or next-action text.</p></div>
      </div>
    </Section>

    <Section id="filters" title="Filters are facets, not claims">
      <p>Narrow results by notation availability, key, mode, vocal part, transposability, title order, page order, and—when Sacred Harp 2025 is selected—<strong>New in 2025</strong>.</p>
      <Table
        headers={["Filter", "What it selects"]}
        rows={[
          ["Notation", "Catalogued score, alternate reference, review draft, or no structured notation."],
          ["Key / mode", "The normalized key facet recorded for the selected edition’s available witness."],
          ["Part", "Records with the requested available vocal part."],
          ["Transposable", "A witness whose validated transposition capability is available and not quarantined."],
          ["New in 2025", "Publisher-listed additions when the Sacred Harp 2025 edition is selected."],
        ]}
      />
      <p className="muted-note">A missing facet value means the attribute is not recorded or not available for filtering. It is not evidence that the printed source lacks that attribute.</p>
    </Section>

    <Section id="result-row" title="Read a result row">
      <p>Each result row keeps the tune number, title, first line, and a compact status visible. Select a row to open the detail pane; do not infer a score from the title row alone.</p>
      <Callout tone="teal"><strong>Search state is not record identity</strong><p>The selected book and tune are the identity. Search terms are only how you got there.</p></Callout>
    </Section>

    <Section id="empty-results" title="When search returns nothing">
      <Steps compact items={[
        <><strong>Clear one filter.</strong> A restrictive notation, mode, part, or transposable facet may be excluding the record.</>,
        <><strong>Try the displayed text.</strong> Search the title or first line as it appears in the selected book.</>,
        <><strong>Choose another edition deliberately.</strong> If the title belongs to another book, switch editions and read the new record state.</>,
      ]} />
    </Section>
  </>;
}

function TuneDetailsContent({ routes }) {
  return <>
    <Section id="detail-pane" title="The detail pane is the evidence hinge" className="intro-section">
      <p>The detail pane answers “what do I have?” before the practice controls answer “what can I do with it?” It identifies the selected book and page, first line, source links, source health, score state, key evidence, and any edition relationship that needs attention.</p>
      <Callout><strong>Read the status before opening controls</strong><p>A catalogue record remains useful when structured notation is unavailable. The absence of a play button is itself meaningful.</p></Callout>
    </Section>

    <Section id="status-labels" title="Status labels">
      <Table
        headers={["Label", "Meaning", "What it permits"]}
        rows={[
          [<strong>Catalogued score</strong>, "Structured notation is attached to the selected edition.", "Render and practice when timing/key checks permit."],
          [<strong>Alternate reference</strong>, "A structured witness exists for another edition or source.", "Compare or practice with the alternate identity visible."],
          [<strong>Review draft only</strong>, "A versioned transcription or OMR result is available.", "Use only within its review contract; never call it authoritative."],
          [<strong>Source scan / source reference</strong>, "The page, scan, PDF, or recording is linked without an admitted score.", "Inspect the source; do not invent transposition."],
          [<strong>Transcription blocked</strong>, "A source blocker prevents safe advancement.", "Resolve or acquire source evidence before transcribing."],
          [<strong>Metadata only / mapping gap</strong>, "The catalogue record exists without a usable source path.", "Keep the record visible; infer no notation."],
        ]}
      />
    </Section>

    <Section id="source-health" title="Source health and links">
      <p>Source health describes what the application knows about a link or retained source at the time it was observed. It can include online, cached, offline, or blocked observations. Read the timestamp and retention state; do not turn a health observation into a fidelity claim.</p>
      <div className="link-card-grid compact-grid">
        <LinkCard label="Source page" title="Printed witness" description="The page, scan, or publisher source remains the visual authority." href={routes.sources} />
        <LinkCard label="Score state" title="Structured asset" description="A machine-readable witness may support rendering without proving every printed semantic." href={routes.reader} />
        <LinkCard label="Review state" title="Human correction" description="Draft evidence and correction paths stay separate from certification." href={routes.reviewDrafts} />
      </div>
    </Section>

    <Section id="missing-score" title="When there is no score">
      <p>The Atlas preserves the exact source link or scan instead of synthesizing notation where structured score data is absent. The coverage state supplies the next safe action: acquire a source, repair a mapping, transcribe from a recorded source, or verify an existing structured witness.</p>
    </Section>
  </>;
}

function ReaderContent({ routes }) {
  return <>
    <Section id="three-views" title="Three views, one catalogue" className="intro-section">
      <Table
        headers={["View", "Use it for", "What stays shared"]}
        rows={[
          [<strong>Library</strong>, "Browsing and selecting records", "Book, search, filters, and detail state"],
          [<strong>Practice</strong>, "Playback and score controls", "The same selected record and evidence labels"],
          [<strong>Sources</strong>, "Source-first inspection", "Edition identity, links, health, and coverage"],
        ]}
      />
      <p>Changing views does not change the edition identity. It changes the job the center panel emphasizes.</p>
    </Section>

    <Section id="score-preview" title="Score preview behavior">
      <p>Full score data is loaded lazily. The visual score is wrapped into vertical four-measure systems for reading; that layout is a reading presentation, not a four-bar playback excerpt. Playback schedules the complete selected score.</p>
      <div className="split-panel">
        <div><span className="panel-label">Rendered</span><h3>What you can see</h3><p>Parts, clefs, measures, noteheads, timing, lyrics, and semantics that the admitted asset actually contains.</p></div>
        <div><span className="panel-label">Linked</span><h3>What you can verify</h3><p>The source page, scan, PDF, recording, or MusicXML witness that remains authoritative for its own claims.</p></div>
      </div>
    </Section>

    <Section id="legend" title="The shape legend">
      <p>The reader distinguishes source-encoded noteheads, derived four-shape labels, and unavailable evidence. The legend is not a guarantee that every glyph came from the printed page.</p>
      <div className="evidence-grid">
        <div><span className="shape-dot source-dot" aria-hidden="true" /><strong>Source</strong><p>The notehead shape is encoded by the MusicXML witness.</p></div>
        <div><span className="shape-dot derived-dot" aria-hidden="true" /><strong>Derived</strong><p>The label is calculated from established key and exact pitch spelling.</p></div>
        <div><span className="shape-dot unavailable-dot" aria-hidden="true" /><strong>Unavailable</strong><p>The source does not establish the shape or key, so the Atlas leaves it blank.</p></div>
      </div>
    </Section>

    <Section id="responsive-reading" title="Small screens and long labels">
      <p>On narrow screens, the documentation and score surfaces retain their semantic order. Long voice labels and notation may require horizontal scrolling inside the score surface; the surrounding reader controls remain usable. This is intentional containment, not a claim that the engraving fits every viewport.</p>
    </Section>
  </>;
}

function PracticeContent({ routes }) {
  return <>
    <Section id="practice-loop" title="A safe practice loop" className="intro-section">
      <Steps items={[
        <><strong>Choose parts.</strong> Select the vocal parts you want to hear. Changing parts stops active playback so an old schedule cannot continue with stale selections.</>,
        <><strong>Choose order.</strong> Use <strong>Written order</strong> by default. Choose <strong>Follow encoded repeats</strong> only when repeat semantics are explicitly supported.</>,
        <><strong>Set tempo and loops.</strong> Tempo is bounded from 40 to 220 BPM; practice loops are bounded from one to eight.</>,
        <><strong>Play and listen.</strong> Use Play, Pause, Resume, and Stop. The schedule covers the selected score, not merely the visible system.</>,
      ]} />
    </Section>

    <Section id="repeat-plans" title="Written order and repeats">
      <p>Encoded repeats are followed only when their semantics are safe to apply. Unsupported D.C., segno, coda, or other navigation falls back to written order and is announced in the detail pane.</p>
      <Table
        headers={["Playback choice", "Use when", "Boundary"]}
        rows={[
          [<strong>Written order</strong>, "You need the conservative linear reading of the score.", "Does not claim the printed source has no repeat."],
          [<strong>Follow encoded repeats</strong>, "Repeat semantics are explicitly encoded and accepted by the playback plan.", "Unsupported navigation remains out of the schedule."],
          [<strong>Practice loops</strong>, "You intentionally want to repeat a scheduled passage or score.", "A loop setting is not source evidence."],
        ]}
      />
    </Section>

    <Section id="stop-conditions" title="When playback stops">
      <p>Playback is stopped or invalidated when selected parts, score version, source key, or target key changes. It also stops at the actual end of a short score. This prevents audio from continuing after the record or its interpretation has changed.</p>
      <Callout tone="teal"><strong>Why this matters</strong><p>Audio is stateful. A schedule built for one score/key/part selection must not outlive that selection.</p></Callout>
    </Section>

    <Section id="failed-playback" title="When playback is unavailable">
      <p>A record can be searchable and source-linked while lacking a playable structured asset. Read the detail state and coverage next action. Do not treat a missing control as a bug until you have checked whether the selected edition has an admitted score and validated timing.</p>
      <div className="link-card-grid compact-grid">
        <LinkCard label="Before retrying" title="Read tune details" description="Check score state, source health, and coverage." href={routes.tuneDetails} />
        <LinkCard label="If key is missing" title="Read transposition" description="Practice may remain possible while pitch changes stay unavailable." href={routes.transpose} />
      </div>
    </Section>
  </>;
}

function TransposeContent() {
  return <>
    <Section id="key-gate" title="Key evidence is the gate" className="intro-section">
      <p>Transposition is enabled only when a source key is available or explicitly entered. The key evidence label distinguishes source-verified, source-observed, OMR-detected, and user-entered keys. A missing mode never silently becomes major.</p>
      <Callout><strong>Useful limitation</strong><p>Practice may still be available when the key is unknown, but target-key transposition remains unavailable until the source key is established.</p></Callout>
    </Section>

    <Section id="key-sources" title="Where a source key comes from">
      <Table
        headers={["Evidence label", "Meaning", "Authority"]}
        rows={[
          [<strong>Source-verified key</strong>, "The structured/source metadata records a key for the witness.", "The named source/asset, subject to the edition boundary."],
          [<strong>Source-observed key</strong>, "A key was directly observed in a source page or retained evidence package.", "The observed source page; review still has its own scope."],
          [<strong>OMR-detected key</strong>, "A notation import detected a key signature.", "A review lead, not automatic edition certification."],
          [<strong>Entered source key</strong>, "A user supplied the key printed in the linked source.", "The current record’s local user entry; separate from catalogue metadata."],
        ]}
      />
    </Section>

    <Section id="manual-entry" title="Enter an unknown source key">
      <Steps compact items={[
        <><strong>Open the linked source.</strong> Read the printed key rather than borrowing one from another edition.</>,
        <><strong>Choose Source key.</strong> Select the printed tonic and mode in the detail pane.</>,
        <><strong>Check the label.</strong> The reader marks the value as entered source key, not as catalogue metadata.</>,
        <><strong>Choose a target.</strong> The target-key control moves by semitone while retaining the source mode.</>,
      ]} />
    </Section>

    <Section id="transposition-boundaries" title="What transposition does not prove">
      <p>A successful pitch transformation proves that the selected structured witness can be transformed under the current key context. It does not prove that the witness matches every printed pitch, shape, lyric, repeat, ending, or editorial marking in the selected edition.</p>
    </Section>
  </>;
}

function NotationContent({ routes }) {
  return <>
    <Section id="four-shapes" title="Four-shape solfège" className="intro-section">
      <p>Shape-note practice uses four shape names—fa, sol, la, and mi—to represent the scale relationships established by the source key and pitch spelling. The Atlas keeps direct notehead evidence separate from labels calculated by the reader.</p>
      <p>The linked shape-source PDF remains the visual authority for printed glyphs. A clean-looking rendered notehead is not by itself proof of the printed shape.</p>
    </Section>

    <Section id="source-derived-unavailable" title="Three shape states">
      <DefinitionList items={[
        ["Source", "The notehead/shape was encoded in the MusicXML witness."],
        ["Derived", "A four-shape label was calculated from an established key and exact pitch spelling."],
        ["Unavailable", "The source does not establish the shape or key, so the Atlas leaves it blank rather than guessing."],
      ]} />
    </Section>

    <Section id="lyrics-and-semantics" title="Lyrics and score semantics">
      <p>Lyrics, melismas, verses, repeats, endings, ties, slurs, and editorial markings follow the same rule: values that are encoded or directly evidenced are preserved; unknown values stay unknown.</p>
      <Table
        headers={["Semantic", "Reader behavior"]}
        rows={[
          ["Lyrics", "Render what the witness contains; do not fill missing underlay from a plausible text source."],
          ["Repeats / endings", "Use only encoded navigation that the playback plan can safely interpret."],
          ["Shapes", "Label source evidence and derivation separately."],
          ["Mode", "Keep it unavailable when the source does not establish it."],
        ]}
      />
    </Section>

    <Section id="compare-notation" title="Compare the rendering with the source">
      <p>Use the linked source page or shape PDF for direct visual comparison. If you find a mismatch, preserve the original witness and route the correction through the versioned review process.</p>
      <LinkCard label="Correction path" title="Review drafts" description="Download an editable candidate, compare it, and propose a versioned correction." href={routes.reviewDrafts} />
    </Section>
  </>;
}

function SourcesContent({ routes }) {
  return <>
    <Section id="source-types" title="Source types" className="intro-section">
      <p>The reader may link to several kinds of source. Each one answers a different question and none should be treated as a universal authority.</p>
      <Table
        headers={["Source", "Useful for", "Still separate from"]}
        rows={[
          ["Printed page / scan", "Edition identity, printed glyphs, lyrics, and visual comparison.", "A parseable MusicXML score."],
          ["Publisher PDF / source list", "Locating or identifying the intended source page.", "Exact notation certification."],
          ["Recording", "Listening context and source metadata.", "The printed score’s exact underlay or engraving."],
          ["MusicXML witness", "Rendering, timing, parts, and possible practice/transposition.", "Automatic proof of printed fidelity."],
          ["Review package", "Correction, comparison, hashes, limitations, and human follow-up.", "Verified edition status."],
        ]}
      />
    </Section>

    <Section id="source-first-workflow" title="A source-first workflow">
      <Steps items={[
        <><strong>Open the source link.</strong> Identify the book, page, and tune on the witness itself.</>,
        <><strong>Compare the record.</strong> Check title, first line, page, key, mode, and visible notation where present.</>,
        <><strong>Use the structured asset cautiously.</strong> Treat it as a named witness with its own evidence state.</>,
        <><strong>Record a mismatch.</strong> Keep the source, candidate, hashes, and limitations available for review.</>,
      ]} />
    </Section>

    <Section id="shape-source" title="Shape-source PDFs">
      <p>When the structured score comes from the Shape Note Music Files path, the Atlas can derive a corresponding shape-source PDF link. That PDF is for visual authority over printed glyphs; it does not turn a MusicXML import into a certified edition.</p>
    </Section>

    <Section id="health-retention" title="Health, caching, and retention">
      <p>Source-health reports preserve observations and their timing. Cached or offline evidence is labeled as such. Retained bytes and their checksums belong to the evidence package; a successful current HTTP request is not permission to replace an earlier source.</p>
      <Callout tone="teal"><strong>When a source is blocked</strong><p>Keep the record visible, name the blocker, and wait for an authorized identifiable source. Do not substitute a convenient derivative.</p></Callout>
    </Section>
  </>;
}

function EvidenceContent({ routes }) {
  return <>
    <Section id="four-questions" title="Four evidence questions" className="intro-section">
      <p>The Atlas keeps separate concepts that are easy to conflate:</p>
      <DefinitionList items={[
        ["Source identity", "Does a URL, scan, PDF leaf, or catalogue row identify the intended record?"],
        ["Structured mapping", "Is a parseable MusicXML asset associated with the selected edition?"],
        ["Review disposition", "Has a draft been compared enough to be useful, rejected for mismatch, or blocked on unresolved evidence?"],
        ["Verified edition status", "Has the exact selected edition’s required notation and source semantics passed the relevant review gates?"],
      ]} />
      <Callout><p className="quote">Source identity is not notation. Notation is not automatically edition certification. A passing build is not corpus completion.</p></Callout>
    </Section>

    <Section id="evidence-ladder" title="The evidence ladder">
      <div className="layer-list">
        <div><span className="layer-number">01</span><div><h3>Identify</h3><p>Establish which page, book, tune, and source record you mean.</p></div></div>
        <div><span className="layer-number">02</span><div><h3>Map</h3><p>Associate a structured witness with the selected edition without overclaiming its semantics.</p></div></div>
        <div><span className="layer-number">03</span><div><h3>Review</h3><p>Compare the candidate with retained source evidence and record its disposition, limits, and version.</p></div></div>
        <div><span className="layer-number">04</span><div><h3>Certify</h3><p>Pass the exact edition-specific review gates required for verified coverage.</p></div></div>
      </div>
    </Section>

    <Section id="not-claims" title="What the labels do not claim">
      <Table
        headers={["Observed", "Not automatically claimed"]}
        rows={[
          ["A matching title", "The same edition or notation"],
          ["A parser import", "Complete printed semantics"],
          ["A playable draft", "A verified printed score"],
          ["A source URL that responds", "Fidelity, completeness, or authorization"],
          ["A green application build", "Corpus completion"],
        ]}
      />
    </Section>

    <Section id="evidence-next" title="Where to go next">
      <div className="link-card-grid compact-grid">
        <LinkCard label="Coverage" title="Queues and next actions" description="Read how unresolved records are classified and routed." href={routes.coverage} />
        <LinkCard label="Correction" title="Review drafts" description="Work with human-correctable, versioned candidates." href={routes.reviewDrafts} />
        <LinkCard label="Source" title="Sources and retention" description="Inspect source types, health observations, and retained bytes." href={routes.sources} />
      </div>
    </Section>
  </>;
}

function CoverageContent({ routes }) {
  return <>
    <Section id="coverage-status" title="Coverage is edition-scoped" className="intro-section">
      <p>Coverage is recorded per book and tune. A record can have an exact structured score, an alternate reference, a review draft, a source reference, a transcription blocker, or a mapping gap. These are not interchangeable completion counts.</p>
      <Table
        headers={["Status", "Next safe action"]}
        rows={[
          [<strong>Structured score</strong>, "Verify source fidelity and playback."],
          [<strong>Source reference</strong>, "Transcribe and verify from the recorded source."],
          [<strong>Transcription blocked</strong>, "Acquire a clean authorized source."],
          [<strong>Metadata only</strong>, "Acquire an authorized source before transcribing."],
          [<strong>Mapping gap</strong>, "Repair the edition-to-source mapping before transcribing."],
        ]}
      />
    </Section>

    <Section id="generated-queues" title="Generated queues">
      <p>Queues are generated views over the corpus and retained evidence. They help select bounded work; they do not replace the source package or direct review.</p>
      <div className="artifact-table" role="table" aria-label="Coverage queues">
        <div className="artifact-row artifact-head" role="row"><span role="columnheader">Queue</span><span role="columnheader">Use</span></div>
        <div className="artifact-row" role="row"><code role="cell">source-coverage.json</code><span role="cell">One edition-scoped classification and next action per record.</span></div>
        <div className="artifact-row" role="row"><code role="cell">transcription-queue.json</code><span role="cell">Records without an exact structured score, with source links and blockers.</span></div>
        <div className="artifact-row" role="row"><code role="cell">human-review-queue.json</code><span role="cell">Drafts, dispositions, review evidence, and correction/publication metadata.</span></div>
        <div className="artifact-row" role="row"><code role="cell">image-review-queue.json</code><span role="cell">Immutable source images and non-authoritative working layers for image review.</span></div>
      </div>
    </Section>

    <Section id="counts" title="Read counts from generated data">
      <p>Coverage numbers change when the generated bundle changes. Use the <code>generatedAt</code>, <code>books</code>, <code>songs</code>, and <code>coverage</code> fields in <code>public/corpus.json</code> and the edition-scoped entries in <code>public/source-coverage.json</code>. Do not copy a historical count into a permanent claim without dating it.</p>
    </Section>

    <Section id="bounded-work" title="Bounded work is a feature">
      <p>Choose a small source-backed batch, preserve its predecessor hashes, verify the exact changed records, and publish a new version. A queue should make the next safe action clear without creating pressure to “complete” a tune by guessing.</p>
      <LinkCard label="Process" title="Contributing rules" description="Read the guardrails for source review, versioning, and staging." href={routes.contributing} />
    </Section>
  </>;
}

function ReviewDraftsContent({ routes }) {
  return <>
    <Section id="draft-contract" title="What a review draft is" className="intro-section">
      <p>A published review draft is a usable, human-correctable work product. It can contain a versioned candidate MusicXML, source links, evidence JSON, hashes, limitations, and a correction path. It is not the selected edition’s verified engraving.</p>
      <Callout><strong><code>safeToPromote: false</code></strong><p>This remains false until the required edition-specific source-review gate is satisfied. Downloading or playing a draft does not promote it.</p></Callout>
    </Section>

    <Section id="use-draft" title="Use a published draft">
      <Steps items={[
        <><strong>Open the evidence.</strong> Read the disposition, source identity, version, and limitations.</>,
        <><strong>Download the editable MusicXML.</strong> The downloadable artifact is the thing a reviewer will actually inspect.</>,
        <><strong>Compare with the untouched source.</strong> Check parts, pitch, timing, clefs, lyrics, shapes, repeats, endings, and editorial details where the source establishes them.</>,
        <><strong>Preserve the original.</strong> Make corrections as a new candidate version; retain superseded artifacts and hashes.</>,
        <><strong>Open the correction path.</strong> Use the pre-filled GitHub form when a correction should be proposed.</>,
      ]} />
    </Section>

    <Section id="draft-boundaries" title="Draft boundaries">
      <Table
        headers={["Draft can provide", "Draft cannot provide by itself"]}
        rows={[
          ["A playable candidate", "Exact-edition certification"],
          ["A correction surface", "Permission to overwrite the source"],
          ["A versioned evidence package", "Proof that unknown lyrics/shapes/repeats are known"],
          ["A useful comparison witness", "A reason to relabel an alternate edition"],
        ]}
      />
    </Section>

    <Section id="rejected-and-blocked" title="Rejected and blocked states">
      <p>A source mismatch, ambiguous comparison, or unresolved blocker remains visible in the review disposition. The isolated material stays fail-closed; it is not quietly promoted because it renders or plays.</p>
      <LinkCard label="Related" title="Evidence model" description="Review the four questions the Atlas keeps separate." href={routes.evidence} />
    </Section>
  </>;
}

function MaintainerContent({ routes, guideUrl }) {
  return <>
    <Section id="maintainer-map" title="Maintainer map" className="intro-section">
      <p>The maintainer surface is split by responsibility: data model, source-dependent pipeline, development workflow, verification, and contribution rules. The current continuation state and retained-evidence requirements live in the <a href={guideUrl} target="_blank" rel="noreferrer noopener">OpenClaw handoff and guide</a>.</p>
      <div className="feature-grid">
        <FeatureCard eyebrow="A" title="Data model" description="Know which artifact answers which question." href={routes.dataModel} />
        <FeatureCard eyebrow="B" title="Data pipeline" description="Refresh source-backed inputs without making a partial bundle." href={routes.pipeline} />
        <FeatureCard eyebrow="C" title="Verification" description="Run focused checks and aggregate receipts." href={routes.verification} />
        <FeatureCard eyebrow="D" title="Contributing" description="Preserve source fidelity and version every correction." href={routes.contributing} />
      </div>
    </Section>

    <Section id="safe-start" title="Safe start">
      <Steps compact items={[
        <><strong>Run git status.</strong> Preserve unrelated work and cloud-backed duplicates.</>,
        <><strong>Read the current handoff.</strong> It is the authority for active source lanes and retained evidence.</>,
        <><strong>Confirm the intended edition.</strong> Do not start from a title string or a convenient alternate witness.</>,
        <><strong>Choose one bounded lane.</strong> Make the smallest reviewed batch that can be independently verified.</>,
      ]} />
    </Section>

    <Section id="maintainer-navigation" title="Maintainer navigation">
      <div className="link-card-grid">
        <LinkCard label="Structure" title="Data model" description="Canonical index, score assets, queues, and provenance." href={routes.dataModel} />
        <LinkCard label="Refresh" title="Data pipeline" description="Prerequisites, generators, source retention, and review commands." href={routes.pipeline} />
        <LinkCard label="Code" title="Development workflow" description="Browser, tests, build, macOS wrapper, and browser audio harness." href={routes.development} />
        <LinkCard label="Proof" title="Verification & receipts" description="Fail-closed checks and claim boundaries." href={routes.verification} />
      </div>
    </Section>
  </>;
}

function DataModelContent() {
  return <>
    <Section id="canonical-bundle" title="The canonical public bundle" className="intro-section">
      <p><code>public/corpus.json</code> is the application index. Its top-level fields include books, merged songs, generated coverage, retained historical records, and <code>generatedAt</code>/<code>source</code> provenance.</p>
      <DefinitionList items={[
        [<code>books</code>, "Edition IDs and display labels."],
        [<code>songs</code>, "Merged corpus records with edition membership and source-backed fields."],
        [<code>coverage</code>, "Generated counts by book; mutable and not hand-maintained prose."],
        [<code>legacyEditionRecords</code>, "Retained historical records when an edition index changes."],
        [<code>generatedAt / source</code>, "The provenance and time context for the generated bundle."],
      ]} />
    </Section>

    <Section id="edition-scoped-fields" title="Edition-scoped fields">
      <Table
        headers={["Field", "Why it is separate"]}
        rows={[
          [<code>metadataByBook</code>, "A key, meter, source URL, composer/lyricist, and edition evidence belong to a specific book."],
          [<code>scoreByBook</code>, "The selected edition’s admitted structured score."],
          [<code>referenceScoreByBook</code>, "An alternate witness that must remain visibly alternate."],
          [<code>draftScoreByBook</code>, "An isolated or published review candidate with its own contract."],
          [<code>sourceCoverageByBook</code>, "The edition-specific status and next action."],
        ]}
      />
    </Section>

    <Section id="artifact-map" title="Artifact map">
      <ArtifactTable />
      <p className="muted-note">Full score data is lazy-loaded from <code>public/scores/</code> or <code>public/draft-scores/</code>; compact previews keep the initial catalogue smaller.</p>
    </Section>

    <Section id="local-work" title="Local-only work tree">
      <p>The <code>work/</code> tree contains retained scans, downloaded inputs, OMR outputs, comparison packages, and verification receipts. Much of it is ignored or local-only. A Git clone alone is not a complete source-dependent validation environment.</p>
    </Section>
  </>;
}

function PipelineContent({ routes, guideUrl }) {
  return <>
    <Section id="prerequisites" title="Prerequisites" className="intro-section">
      <p>Regeneration requires the established local source checkout at <code>/Users/jacquelinehenriksen/sh-corpus-scripts</code>. The builder expects the dashboard corpus, metadata export, edition-change register, and local MusicXML cache. It refuses to create a partial bundle when required metadata sources are absent.</p>
    </Section>

    <Section id="refresh" title="Refresh the generated bundle">
      <CodeBlock>{`npm ci --ignore-scripts --no-audit --no-fund
python3 scripts/verify_dependencies.py
python3 scripts/fetch_shapenote_scores.py   # only when score mappings need refresh
npm run prepare-data`}</CodeBlock>
      <p><code>prepare-data</code> runs the corpus builder and candidate reconciliation. Source retention, image, recording, candidate, and review commands remain separate because each has a different evidence boundary.</p>
    </Section>

    <Section id="source-commands" title="Source and review commands">
      <Table
        headers={["Command family", "Result"]}
        rows={[
          [<code>index-source-images / retain-source-images</code>, "Index and retain confirmed source images with URL/checksum provenance."],
          [<code>prepare-transcription-images / build-image-review-queue</code>, "Create versioned review layers and publish the image-review queue."],
          [<code>run-cleaned-omr / audit-omr</code>, "Run bounded OMR and audit warnings against deterministic review inputs."],
          [<code>build-review-queue</code>, "Rebuild human-review state after draft changes."],
          [<code>build-source-comparison-ledger</code>, "Record explicit source-versus-candidate comparisons."],
          [<code>build-shared-edition-reconciliation</code>, "Rebuild edition-pair relationships without merging their identity."],
        ]}
      />
      <p>Read the <a href={guideUrl} target="_blank" rel="noreferrer noopener">current handoff</a> before restoring retained evidence or resuming a source lane.</p>
    </Section>

    <Section id="pipeline-rules" title="Pipeline rules">
      <Steps compact items={[
        <><strong>Preserve originals.</strong> Never replace an immutable scan or source MusicXML with a cleaned derivative.</>,
        <><strong>Version corrections.</strong> Publish a new candidate version and retain predecessors, evidence JSON, and hashes.</>,
        <><strong>Keep boundaries explicit.</strong> A candidate ledger records comparison; it does not promote the candidate.</>,
        <><strong>Stage only the reviewed batch.</strong> Generated data changes need the same scope discipline as code changes.</>,
      ]} />
      <LinkCard label="Next" title="Verification & receipts" description="Prove the resulting bundle and report its boundaries." href={routes.verification} />
    </Section>
  </>;
}

function VerificationContent({ routes }) {
  return <>
    <Section id="focused-checks" title="Focused checks first" className="intro-section">
      <p>Run the narrow validator that covers the layer you changed, then run the aggregate verifier when the checkout has the required source-dependent inputs.</p>
      <CodeBlock>{`python3 scripts/validate_data.py
python3 scripts/validate_playback.py
python3 scripts/validate_transposition.py
node --test tests/*.mjs`}</CodeBlock>
      <p>The JavaScript tests use Node’s built-in test runner. Browser behavior follows <code>scripts/browser-smoke-test-plan.md</code> and requires a fresh receipt for the tested commit.</p>
    </Section>

    <Section id="aggregate" title="Aggregate verification">
      <CodeBlock>{`npm run verify-all

# bounded options
npm run verify-all -- --no-build
npm run verify-all -- --no-write
npm run verify-all -- --skip-source-health-collection
npm run verify-all -- --allow-missing-optional`}</CodeBlock>
      <p>The fail-closed aggregate check covers generated-artifact integrity, stale inputs, promotion safety, queue consistency, data, playback, transposition, shape and image review, source candidates, source health, browser smoke when available, production build, and startup.</p>
    </Section>

    <Section id="receipts" title="Receipts are dated proof">
      <p>The verifier writes <code>work/verification/verification-receipt.json</code> and <code>work/verification/verification-receipt.md</code> unless <code>--no-write</code> is used. Browser audio proof records page identity, expected event counts, frequencies, console/harness errors, and post-action state.</p>
      <Callout tone="teal"><strong>Do not relabel old proof</strong><p>A receipt for an earlier commit is historical evidence. Capture a fresh receipt after changing application code or generated assets.</p></Callout>
    </Section>

    <Section id="reporting-boundaries" title="Report claims separately">
      <Table
        headers={["Claim", "Evidence needed"]}
        rows={[
          ["Local behavior", "Focused tests and local runtime checks"],
          ["Browser behavior", "Fresh browser smoke/audio receipt"],
          ["Build", "Production build output"],
          ["Git state", "Commit, working tree, and push proof"],
          ["Deployment", "Hosted route/asset checks and deployment result"],
          ["Corpus completion", "Edition-specific source review, not merely the above"],
        ]}
      />
      <LinkCard label="Code" title="Development workflow" description="Run the browser app, tests, static preview, and macOS wrapper." href={routes.development} />
    </Section>
  </>;
}

function DevelopmentContent() {
  return <>
    <Section id="browser-app" title="Run the browser app" className="intro-section">
      <CodeBlock>{`npm ci --ignore-scripts --no-audit --no-fund
npm run dev`}</CodeBlock>
      <p>The separate <code>public/audio-harness.html</code> page instruments browser audio for verification. It is not part of the reader UI.</p>
    </Section>

    <Section id="static-preview" title="Build and preview">
      <CodeBlock>{`npm run build
npm run preview`}</CodeBlock>
      <p>The multi-page build emits the reader and the documentation routes under the configured base path. When testing a hosted subpath locally, mount the built output at the same path used by deployment.</p>
    </Section>

    <Section id="macos-wrapper" title="Build the macOS wrapper">
      <p>The SwiftUI wrapper bundles the browser build and serves score assets from a private local service.</p>
      <CodeBlock>{`bash script/build_and_run.sh
bash script/build_and_run.sh --verify`}</CodeBlock>
      <p>The output app is <code>outputs/The Shape-Note Atlas.app</code>. The <code>--verify</code> check covers the static package/startup contract; it does not prove native-window interaction or public deployment.</p>
    </Section>

    <Section id="browser-audio" title="Browser audio harness">
      <p>For audio proof, open <code>/audio-harness.html</code> from a running dev server and follow <code>scripts/browser-smoke-test-plan.md</code>. Test source-verified keys, unknown-key entry, reference witnesses, review drafts, partial parts, target-key cancellation, automatic ending, and target reset.</p>
    </Section>
  </>;
}

function ContributingContent({ routes, guideUrl }) {
  return <>
    <Section id="before-editing" title="Before editing" className="intro-section">
      <Steps compact items={[
        <><strong>Run <code>git status</code>.</strong> Preserve unrelated work and cloud-backed duplicates.</>,
        <><strong>Read the current handoff.</strong> Check retained evidence and the active source lane.</>,
        <><strong>Confirm the intended edition.</strong> Verify source identity and recorded hashes before transcribing.</>,
        <><strong>Define the batch.</strong> Keep the change independently reviewable and stage only that batch.</>,
      ]} />
    </Section>

    <Section id="notation-rules" title="When adding notation">
      <ul className="docs-bullets">
        <li>Compare the actual exported MusicXML, not only an evidence JSON file.</li>
        <li>Preserve parts, event order, pitch, duration, clef, voice, staff, ties, repeats, endings, lyrics, and notehead geometry when the source establishes them.</li>
        <li>Keep source notehead evidence separate from pitch-derived shape labels.</li>
        <li>Leave missing lyrics, shapes, mode, repeats, and verse numbers unavailable.</li>
        <li>Keep <code>safeToPromote: false</code> until the exact source-review gate is satisfied.</li>
        <li>Publish a new candidate version instead of overwriting an earlier one.</li>
      </ul>
    </Section>

    <Section id="application-rules" title="When changing application behavior">
      <ul className="docs-bullets">
        <li>Keep alternate editions visibly labeled.</li>
        <li>Stop and clean up playback when its source state changes.</li>
        <li>Do not borrow a key from another edition to unlock transposition.</li>
        <li>Add or update focused tests.</li>
        <li>Run a fresh browser check for user-visible behavior.</li>
        <li>Report tests, browser proof, build, Git state, and deployment separately.</li>
      </ul>
    </Section>

    <Section id="review-and-ship" title="Review and ship">
      <p>Use the smallest useful commit, verify it in a clean enough environment, and preserve the distinction between local proof and hosted proof. The project is intentionally suspicious of convenient certainty; that is how a tune catalogue stays useful instead of becoming a polished set of guesses.</p>
      <div className="link-card-grid compact-grid">
        <LinkCard label="Process" title="Verification" description="Run the focused and aggregate checks." href={routes.verification} />
        <LinkCard label="Authority" title="Current handoff" description="Read retained evidence and continuation boundaries." href={guideUrl} external />
      </div>
    </Section>
  </>;
}

function GlossaryContent({ routes }) {
  return <>
    <Section id="terms" title="Atlas vocabulary" className="intro-section">
      <DefinitionList items={[
        ["Edition", "A particular book or published witness, such as Sacred Harp 1991 or Sacred Harp 2025."],
        ["Exact / catalogued score", "A structured score attached to the selected edition’s score field."],
        ["Alternate reference", "A structured witness from another edition or source, labeled as alternate."],
        ["Review draft", "A versioned, human-correctable candidate that is not automatically authoritative."],
        ["Source identity", "Evidence that a page, scan, PDF leaf, or catalogue row is the intended record."],
        ["Structured mapping", "An association between a parseable MusicXML asset and an edition-scoped record."],
        ["Source coverage", "An edition-scoped status and next safe action for a record."],
        ["Promotion", "Moving a review candidate into a verified edition score; gated by direct source review."],
        ["Source shape", "A notehead shape encoded by the witness, distinct from a pitch-derived label."],
        ["Entered key", "A user-supplied key read from the linked source, kept separate from catalogue metadata."],
        ["Fail closed", "Keep a value unavailable or a candidate isolated when evidence does not support a stronger claim."],
      ]} />
    </Section>

    <Section id="shortcuts" title="Shortcuts for common questions">
      <Table
        headers={["If you are asking…", "Start here"]}
        rows={[
          ["Can I practice this tune?", <a href={routes.tuneDetails}>Tune details</a>],
          ["Why is transpose disabled?", <a href={routes.transpose}>Keys & transposition</a>],
          ["Is this score really from this book?", <a href={routes.evidence}>Evidence model</a>],
          ["Where did this count come from?", <a href={routes.dataModel}>Data model</a>],
          ["How do I publish a correction?", <a href={routes.reviewDrafts}>Review drafts</a>],
          ["What should I run after a change?", <a href={routes.verification}>Verification</a>],
        ]}
      />
    </Section>

    <Section id="honest-language" title="Honest language">
      <p>Prefer “source-linked,” “structured witness,” “review draft,” “source-observed,” and “not yet verified” when those are the facts. Avoid “complete,” “official,” “exact,” or “certified” unless the corresponding source-review gate actually passed.</p>
    </Section>
  </>;
}

export function getDocsConfig(routes, { guideUrl, repositoryUrl, imageUrl }) {
  const pages = {
    overview: { label: "Overview", eyebrow: "Start here", group: "Start here", title: "Shape-Note Atlas", lead: "A searchable, source-faithful reader and practice space for shape-note and Sacred Harp music.", source: guideUrl, sections: [["A map, not a monolith", "start-here"], ["What the Atlas is", "the-atlas"], ["Documentation map", "documentation-map"], ["Current scope", "scope"], ["Primary project sources", "source-links"]], content: <OverviewContent routes={routes} guideUrl={guideUrl} repositoryUrl={repositoryUrl} imageUrl={imageUrl} /> },
    gettingStarted: { label: "Quickstart", eyebrow: "Start here", group: "Start here", title: "Get to a first tune", lead: "Install the browser app, choose an edition, and learn what to inspect before you practice.", source: guideUrl, sections: [["Install and run", "install"], ["Your first session", "first-session"], ["What to check before practicing", "what-to-check"], ["Next pages", "next-pages"]], content: <GettingStartedContent routes={routes} /> },
    concepts: { label: "Editions & records", eyebrow: "Start here", group: "Start here", title: "A tune is more than a title", lead: "Understand edition identity, record layers, deep links, and deliberate comparison.", source: guideUrl, sections: [["Edition identity", "edition-identity"], ["One record, several layers", "record-layers"], ["Share a specific tune", "deep-links"], ["Compare without collapsing", "edition-comparisons"]], content: <ConceptsContent routes={routes} /> },
    browse: { label: "Browse & search", eyebrow: "Use the reader", group: "Use the reader", title: "Find the record you mean", lead: "Search by the evidence you have, then use facets to narrow without turning absence into a claim.", source: guideUrl, sections: [["Search fields", "search-fields"], ["Filters are facets, not claims", "filters"], ["Read a result row", "result-row"], ["When search returns nothing", "empty-results"]], content: <BrowseContent /> },
    tuneDetails: { label: "Tune details", eyebrow: "Use the reader", group: "Use the reader", title: "Read the detail state", lead: "The detail pane keeps record identity, source health, score state, and next action in view.", source: guideUrl, sections: [["The detail pane is the evidence hinge", "detail-pane"], ["Status labels", "status-labels"], ["Source health and links", "source-health"], ["When there is no score", "missing-score"]], content: <TuneDetailsContent routes={routes} /> },
    reader: { label: "Reader layout", eyebrow: "Use the reader", group: "Use the reader", title: "One catalogue, three working views", lead: "Move between Library, Practice, and Sources while keeping the selected edition explicit.", source: guideUrl, sections: [["Three views, one catalogue", "three-views"], ["Score preview behavior", "score-preview"], ["The shape legend", "legend"], ["Small screens and long labels", "responsive-reading"]], content: <ReaderContent routes={routes} /> },
    practice: { label: "Practice & playback", eyebrow: "Use the reader", group: "Use the reader", title: "Practice the score you actually selected", lead: "Control parts, tempo, loops, and repeat plans while keeping playback tied to the current score state.", source: guideUrl, sections: [["A safe practice loop", "practice-loop"], ["Written order and repeats", "repeat-plans"], ["When playback stops", "stop-conditions"], ["When playback is unavailable", "failed-playback"]], content: <PracticeContent routes={routes} /> },
    transpose: { label: "Keys & transposition", eyebrow: "Use the reader", group: "Use the reader", title: "Transpose only with key evidence", lead: "Source keys, entered keys, modes, and target keys stay explicit instead of being guessed.", source: guideUrl, sections: [["Key evidence is the gate", "key-gate"], ["Where a source key comes from", "key-sources"], ["Enter an unknown source key", "manual-entry"], ["What transposition does not prove", "transposition-boundaries"]], content: <TransposeContent /> },
    notation: { label: "Shapes & semantics", eyebrow: "Use the reader", group: "Use the reader", title: "Render what the source establishes", lead: "Four-shape labels, lyrics, repeats, and editorial semantics remain honest about their evidence.", source: guideUrl, sections: [["Four-shape solfège", "four-shapes"], ["Three shape states", "source-derived-unavailable"], ["Lyrics and score semantics", "lyrics-and-semantics"], ["Compare the rendering with the source", "compare-notation"]], content: <NotationContent routes={routes} /> },
    sources: { label: "Sources & links", eyebrow: "Use the reader", group: "Use the reader", title: "Keep the witness in view", lead: "Source pages, scans, recordings, MusicXML, and review packages answer different questions.", source: guideUrl, sections: [["Source types", "source-types"], ["A source-first workflow", "source-first-workflow"], ["Shape-source PDFs", "shape-source"], ["Health, caching, and retention", "health-retention"]], content: <SourcesContent routes={routes} /> },
    evidence: { label: "Evidence model", eyebrow: "Evidence", group: "Evidence", title: "Follow the evidence boundary", lead: "Understand what the Atlas knows, what it derives, and what remains open for human correction.", source: guideUrl, sections: [["Four evidence questions", "four-questions"], ["The evidence ladder", "evidence-ladder"], ["What the labels do not claim", "not-claims"], ["Where to go next", "evidence-next"]], content: <EvidenceContent routes={routes} /> },
    coverage: { label: "Coverage & queues", eyebrow: "Evidence", group: "Evidence", title: "See what is covered—and what is not", lead: "Edition-scoped coverage states route the next safe action without pretending the corpus is complete.", source: guideUrl, sections: [["Coverage is edition-scoped", "coverage-status"], ["Generated queues", "generated-queues"], ["Read counts from generated data", "counts"], ["Bounded work is a feature", "bounded-work"]], content: <CoverageContent routes={routes} /> },
    reviewDrafts: { label: "Review drafts", eyebrow: "Evidence", group: "Evidence", title: "Correct without promoting", lead: "Use versioned, human-correctable drafts while preserving the source and the verified-edition boundary.", source: guideUrl, sections: [["What a review draft is", "draft-contract"], ["Use a published draft", "use-draft"], ["Draft boundaries", "draft-boundaries"], ["Rejected and blocked states", "rejected-and-blocked"]], content: <ReviewDraftsContent routes={routes} /> },
    maintainer: { label: "Maintainer map", eyebrow: "Maintain", group: "Maintain", title: "Maintain the corpus", lead: "Refresh generated artifacts and verify the browser bundle without collapsing source, review, and release claims.", source: guideUrl, sections: [["Maintainer map", "maintainer-map"], ["Safe start", "safe-start"], ["Maintainer navigation", "maintainer-navigation"]], content: <MaintainerContent routes={routes} guideUrl={guideUrl} /> },
    dataModel: { label: "Data model", eyebrow: "Maintain", group: "Maintain", title: "Know which artifact answers which question", lead: "Trace the canonical bundle, edition-scoped fields, queues, lazy assets, and local evidence tree.", source: guideUrl, sections: [["The canonical public bundle", "canonical-bundle"], ["Edition-scoped fields", "edition-scoped-fields"], ["Artifact map", "artifact-map"], ["Local-only work tree", "local-work"]], content: <DataModelContent /> },
    pipeline: { label: "Data pipeline", eyebrow: "Maintain", group: "Maintain", title: "Refresh source-backed data", lead: "Regenerate deliberately from the established source checkout and keep every evidence lane separate.", source: guideUrl, sections: [["Prerequisites", "prerequisites"], ["Refresh the generated bundle", "refresh"], ["Source and review commands", "source-commands"], ["Pipeline rules", "pipeline-rules"]], content: <PipelineContent routes={routes} guideUrl={guideUrl} /> },
    verification: { label: "Verification & receipts", eyebrow: "Maintain", group: "Maintain", title: "Prove the change you made", lead: "Focused checks, aggregate verification, browser receipts, and claim boundaries for maintainers.", source: guideUrl, sections: [["Focused checks first", "focused-checks"], ["Aggregate verification", "aggregate"], ["Receipts are dated proof", "receipts"], ["Report claims separately", "reporting-boundaries"]], content: <VerificationContent routes={routes} /> },
    development: { label: "Development workflow", eyebrow: "Maintain", group: "Maintain", title: "Run the app and its checks", lead: "Browser development, static preview, the macOS wrapper, and the audio harness in one place.", source: guideUrl, sections: [["Run the browser app", "browser-app"], ["Build and preview", "static-preview"], ["Build the macOS wrapper", "macos-wrapper"], ["Browser audio harness", "browser-audio"]], content: <DevelopmentContent /> },
    contributing: { label: "Contributing", eyebrow: "Maintain", group: "Maintain", title: "Contribute without flattening uncertainty", lead: "Source fidelity, versioned corrections, focused tests, and clean delivery boundaries.", source: guideUrl, sections: [["Before editing", "before-editing"], ["When adding notation", "notation-rules"], ["When changing application behavior", "application-rules"], ["Review and ship", "review-and-ship"]], content: <ContributingContent routes={routes} guideUrl={guideUrl} /> },
    glossary: { label: "Glossary", eyebrow: "Reference", group: "Reference", title: "Atlas vocabulary", lead: "A compact reference for the words that carry the project’s evidence boundaries.", source: guideUrl, sections: [["Atlas vocabulary", "terms"], ["Shortcuts for common questions", "shortcuts"], ["Honest language", "honest-language"]], content: <GlossaryContent routes={routes} /> },
  };

  const groups = [
    { label: "Start here", keys: ["overview", "gettingStarted", "concepts"] },
    { label: "Use the reader", keys: ["browse", "tuneDetails", "reader", "practice", "transpose", "notation", "sources"] },
    { label: "Evidence", keys: ["evidence", "coverage", "reviewDrafts"] },
    { label: "Maintain", keys: ["maintainer", "dataModel", "pipeline", "verification", "development", "contributing"] },
    { label: "Reference", keys: ["glossary"] },
  ];
  return { pages, groups };
}
