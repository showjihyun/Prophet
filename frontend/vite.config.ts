/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    // Bump from default 500 KB → 600 KB so the simulation chunk warning
    // only fires when something is actually wrong.
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        // Explicit named chunks for heavy 3rd-party libs.
        // - Stable filenames → browser cache survives across route changes
        // - Heavy deps don't get duplicated into every consumer chunk
        // - Easier to spot regressions in the bundle table
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined

          // 3D rendering: three.js + react-force-graph-3d + their d3 deps.
          // ~1 MB raw, but only loaded when GraphPanel actually mounts.
          if (
            id.includes('/three/') ||
            id.includes('/react-force-graph-3d/') ||
            id.includes('/3d-force-graph/') ||
            id.includes('/three-render-objects/') ||
            id.includes('/three-forcegraph/')
          ) {
            return 'vendor-three'
          }

          // 2D graph: cytoscape (FactionMapView, EgoGraph)
          if (id.includes('/cytoscape')) {
            return 'vendor-cytoscape'
          }

          // Charts: recharts + its d3 dependencies
          if (id.includes('/recharts/') || id.includes('/victory-vendor/')) {
            return 'vendor-recharts'
          }

          // d3 utilities (used by recharts, force-graph, and directly)
          // Only the bits not already pulled into a vendor-* chunk above.
          if (id.includes('/d3-')) {
            return 'vendor-d3'
          }

          return undefined
        },
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: true,
    exclude: ['e2e/**', 'node_modules/**'],
  },
})
