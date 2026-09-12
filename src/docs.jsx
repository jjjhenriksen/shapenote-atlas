import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { getDocsConfig } from "./docs-content.jsx";
import "./docs.css";

const BASE_URL = import.meta.env.BASE_URL || "/";
const DOCS_ROOT = `${BASE_URL.replace(/\/?$/, "/")}docs/`;
const GUIDE_URL = "https://github.com/jjjhenriksen/shapenote-atlas/blob/main/docs/ATLAS_GUIDE.md";
const REPOSITORY_URL = "https://github.com/jjjhenriksen/shapenote-atlas";

const routes = {
  overview: DOCS_ROOT,
  gettingStarted: `${DOCS_ROOT}getting-started/`,
  concepts: `${DOCS_ROOT}concepts/`,
  browse: `${DOCS_ROOT}browse/`,
  tuneDetails: `${DOCS_ROOT}tune-details/`,
  reader: `${DOCS_ROOT}reader/`,
  practice: `${DOCS_ROOT}practice/`,
  transpose: `${DOCS_ROOT}transpose/`,
  notation: `${DOCS_ROOT}notation/`,
  sources: `${DOCS_ROOT}sources/`,
  evidence: `${DOCS_ROOT}evidence/`,
  coverage: `${DOCS_ROOT}coverage/`,
  reviewDrafts: `${DOCS_ROOT}review-drafts/`,
  maintainer: `${DOCS_ROOT}maintainer/`,
  dataModel: `${DOCS_ROOT}data-model/`,
  pipeline: `${DOCS_ROOT}pipeline/`,
  verification: `${DOCS_ROOT}verification/`,
  development: `${DOCS_ROOT}development/`,
  contributing: `${DOCS_ROOT}contributing/`,
  glossary: `${DOCS_ROOT}glossary/`,
};

const { pages, groups } = getDocsConfig(routes, { guideUrl: GUIDE_URL, repositoryUrl: REPOSITORY_URL, imageUrl: `${BASE_URL}docs/images/atlas-reader.png` });
const pageOrder = groups.flatMap((group) => group.keys);

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
  if (!normalized) return groups.map((group) => ({ ...group, items: group.keys.flatMap((pageKey) => pages[pageKey].sections.map(([label, id]) => ({ label, id, page: pageKey }))) }));

  return groups.map((group) => {
    const items = group.keys.flatMap((pageKey) => {
      const page = pages[pageKey];
      const pageMatches = `${group.label} ${page.label} ${page.title} ${page.lead}`.toLowerCase().includes(normalized);
      return pageMatches
        ? page.sections.map(([label, id]) => ({ label, id, page: pageKey }))
        : page.sections.filter(([label]) => `${group.label} ${page.label} ${label}`.toLowerCase().includes(normalized)).map(([label, id]) => ({ label, id, page: pageKey }));
    });
    return { ...group, items };
  }).filter((group) => group.items.length);
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
  const navGroups = filteredNavigation(query);
  const currentHash = window.location.hash.replace(/^#/, "");
  return <aside className="docs-sidebar" aria-label="Documentation navigation">
    {navGroups.length ? navGroups.map((group) => <div className={`docs-nav-group${group.keys.includes(currentPage) ? " current-group" : ""}`} key={group.label}>
      <div className="docs-nav-label">{group.label}</div>
      <nav>
        {group.items.map((item) => {
          const firstSection = pages[item.page].sections[0][1];
          const active = item.page === currentPage && (currentHash ? item.id === currentHash : item.id === firstSection);
          return <a className={active ? "current" : ""} href={`${routes[item.page]}#${item.id}`} key={`${item.page}-${item.id}`}>{item.label}</a>;
        })}
      </nav>
    </div>) : <p className="docs-nav-empty">No matching pages.</p>}
    <div className="docs-sidebar-spacer" />
    <a className="sidebar-guide-link" href={GUIDE_URL} target="_blank" rel="noreferrer noopener">Open the full maintainer guide <Arrow /></a>
  </aside>;
}

function PageNav({ currentPage }) {
  const index = pageOrder.indexOf(currentPage);
  const previous = index > 0 ? pageOrder[index - 1] : null;
  const next = index >= 0 && index < pageOrder.length - 1 ? pageOrder[index + 1] : null;
  return <nav className="docs-next-nav" aria-label="Documentation pagination">
    {previous ? <a className="docs-next-link previous" href={routes[previous]}><span>← Previous</span><strong>{pages[previous].label}</strong></a> : <span />}
    {next ? <a className="docs-next-link next" href={routes[next]}><span>Next</span><strong>{pages[next].label} →</strong></a> : <span />}
  </nav>;
}

function DocsPage() {
  const currentPage = pageKeyFromPath();
  const page = pages[currentPage];
  const [query, setQuery] = useState("");
  const [theme, toggleTheme] = useStoredTheme();
  const searchRef = useRef(null);
  const matchingItems = useMemo(() => filteredNavigation(query).flatMap((group) => group.items), [query]);
  const currentGroup = groups.find((group) => group.keys.includes(currentPage));

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
          <input ref={searchRef} value={query} onChange={(event) => setQuery(event.target.value)} type="search" placeholder="Search 19 documentation pages…" aria-label="Search documentation" />
          <kbd>⌘ K</kbd>
        </label>
        <div className="docs-header-actions">
          <a href={REPOSITORY_URL} target="_blank" rel="noreferrer noopener" aria-label="Open Shape-Note Atlas on GitHub">GitHub</a>
          <button className="theme-button" type="button" onClick={toggleTheme} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}>{theme === "dark" ? "☼" : "☾"}</button>
        </div>
      </div>
      <nav className="docs-category-nav" aria-label="Documentation categories">
        {groups.map((group) => <a className={group.keys.includes(currentPage) ? "active" : ""} href={routes[group.keys[0]]} key={group.label}>{group.label}</a>)}
        <a className="category-reader-link" href={BASE_URL}>Open reader <Arrow /></a>
      </nav>
    </header>

    <div className="docs-layout">
      <Sidebar query={query} currentPage={currentPage} />

      <main className="docs-main" id="top">
        <div className="docs-breadcrumb">Docs <span>/</span> {currentGroup?.label} <span>/</span> {page.label}</div>
        <div className="docs-article-actions"><a href={BASE_URL}>Open reader <Arrow /></a><a href={page.source || GUIDE_URL} target="_blank" rel="noreferrer noopener">View source <Arrow /></a></div>
        <div className="docs-kicker">{page.eyebrow}</div>
        <h1>{page.title}</h1>
        <p className="docs-lead">{page.lead}</p>
        <div className="docs-page-meta"><span>{page.sections.length} sections</span><span>·</span><span>{page.group}</span></div>

        {page.content}

        <PageNav currentPage={currentPage} />
        <footer className="docs-footer"><span>Shape-Note Atlas documentation</span><span><a href={BASE_URL}>Open reader</a><span className="footer-divider">·</span><a href={REPOSITORY_URL} target="_blank" rel="noreferrer noopener">Source on GitHub</a></span></footer>
      </main>

      <aside className="docs-toc" aria-label="On this page">
        <div className="toc-label">On this page</div>
        <nav>{page.sections.map(([label, id]) => <a href={`#${id}`} key={id}>{label}</a>)}</nav>
        {query && <p className="toc-search-state">{matchingItems.length} matching section{matchingItems.length === 1 ? "" : "s"}</p>}
      </aside>
    </div>
  </div>;
}

createRoot(document.getElementById("root")).render(<DocsPage />);
