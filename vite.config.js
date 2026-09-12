import { defineConfig } from "vite";
import { resolve } from "node:path";

// Runtime/package checks can point at an isolated, bounded fixture without
// changing the canonical public tree. The normal build keeps Vite's default.
export default defineConfig({
  publicDir: process.env.ATLAS_PUBLIC_DIR || "public",
  build: {
    rollupOptions: {
      input: {
        atlas: resolve(process.cwd(), "index.html"),
        docs: resolve(process.cwd(), "docs/index.html"),
        docsGettingStarted: resolve(process.cwd(), "docs/getting-started/index.html"),
        docsConcepts: resolve(process.cwd(), "docs/concepts/index.html"),
        docsBrowse: resolve(process.cwd(), "docs/browse/index.html"),
        docsTuneDetails: resolve(process.cwd(), "docs/tune-details/index.html"),
        docsReader: resolve(process.cwd(), "docs/reader/index.html"),
        docsPractice: resolve(process.cwd(), "docs/practice/index.html"),
        docsTranspose: resolve(process.cwd(), "docs/transpose/index.html"),
        docsNotation: resolve(process.cwd(), "docs/notation/index.html"),
        docsSources: resolve(process.cwd(), "docs/sources/index.html"),
        docsEvidence: resolve(process.cwd(), "docs/evidence/index.html"),
        docsCoverage: resolve(process.cwd(), "docs/coverage/index.html"),
        docsReviewDrafts: resolve(process.cwd(), "docs/review-drafts/index.html"),
        docsMaintainer: resolve(process.cwd(), "docs/maintainer/index.html"),
        docsDataModel: resolve(process.cwd(), "docs/data-model/index.html"),
        docsPipeline: resolve(process.cwd(), "docs/pipeline/index.html"),
        docsVerification: resolve(process.cwd(), "docs/verification/index.html"),
        docsDevelopment: resolve(process.cwd(), "docs/development/index.html"),
        docsContributing: resolve(process.cwd(), "docs/contributing/index.html"),
        docsGlossary: resolve(process.cwd(), "docs/glossary/index.html"),
      },
    },
  },
});
