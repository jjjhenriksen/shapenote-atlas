import { defineConfig } from "vite";

// Runtime/package checks can point at an isolated, bounded fixture without
// changing the canonical public tree. The normal build keeps Vite's default.
export default defineConfig({
  publicDir: process.env.ATLAS_PUBLIC_DIR || "public",
});
