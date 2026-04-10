/**
 * Vitest setup — global test configuration.
 * @spec docs/spec/09_HARNESS_SPEC.md
 */
import '@testing-library/jest-dom';
import { vi, beforeEach } from 'vitest';
import * as React from 'react';
import * as rtl from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// jsdom does not implement ResizeObserver. Components that query layout on
// mount (GraphPanel, lazy-loaded chart containers) crash without it. Provide
// a no-op stub globally so tests render instead of throwing.
class ResizeObserverStub {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}
if (!globalThis.ResizeObserver) {
  globalThis.ResizeObserver = ResizeObserverStub as unknown as typeof ResizeObserver;
}

// react-force-graph-3d pulls in three.js which tries to use WebGL at module
// load time. jsdom has no WebGL, so importing it crashes any test that
// indirectly renders GraphPanel. Stub it globally with a no-op component
// — tests that need to assert on graph DOM should use the GraphPanel3D
// targeted suite which mocks more deliberately.
vi.mock('react-force-graph-3d', () => ({
  __esModule: true,
  default: () => null,
}));

// ───────── Global TanStack Query test wrapper ─────────
//
// Most pages now use `useQuery` hooks from `src/api/queries.ts`. Those
// hooks throw "No QueryClient set" without a provider.
//
// Strategy: vi.mock the tanstack-react-query module so that hooks
// returning a query client always find one. The mock provides a real
// client created lazily on first access — no per-test setup required.
const _testQueryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false, gcTime: 0, staleTime: 0 },
    mutations: { retry: false },
  },
});

vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual<typeof import('@tanstack/react-query')>(
    '@tanstack/react-query',
  );
  return {
    ...actual,
    // Override useQueryClient so tests don't need a provider
    useQueryClient: () => _testQueryClient,
    // Wrap useQuery so it injects the test client when no provider exists
    useQuery: (options: Parameters<typeof actual.useQuery>[0]) =>
      actual.useQuery(options, _testQueryClient),
    useMutation: (options: Parameters<typeof actual.useMutation>[0]) =>
      actual.useMutation(options, _testQueryClient),
  };
});

// Reference React/rtl so they're not flagged as unused (used to be by the
// monkey-patch render wrapper, kept for future test util needs).
void React;
void rtl;
void QueryClientProvider;

// Clear the test query cache between tests so cached data from a previous
// test doesn't bleed into the next one (e.g. Loading State tests need
// queries to actually be in pending state, not cached as success).
beforeEach(() => {
  _testQueryClient.clear();
});
