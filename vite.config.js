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
        docsReader: resolve(process.cwd(), "docs/reader/index.html"),
        docsEvidence: resolve(process.cwd(), "docs/evidence/index.html"),
        docsMaintainer: resolve(process.cwd(), "docs/maintainer/index.html"),
      },
    },
  },
});
