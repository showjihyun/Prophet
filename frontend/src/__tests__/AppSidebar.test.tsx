/**
 * AppSidebar regression tests.
 *
 * @spec docs/spec/ui/UI_06_PROJECTS_LIST.md#app-sidebar
 */
import { render, screen, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

import AppSidebar from '@/components/shared/AppSidebar';

function mockMatchMedia(matches: boolean) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })) as unknown as typeof window.matchMedia;
}

describe('AppSidebar', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('respects defaultCollapsed=true on desktop (regression: mobile effect must not override)', () => {
    // Regression guard: a prior version had `useEffect(() => setCollapsed(isMobile))`
    // which fired on mount and stomped `defaultCollapsed` on desktop, silently
    // defeating SimulationPage's 60px rail.
    mockMatchMedia(false); // desktop
    render(
      <MemoryRouter>
        <AppSidebar defaultCollapsed />
      </MemoryRouter>,
    );
    const aside = screen.getByTestId('app-sidebar');
    expect(aside.style.width).toBe('60px');
  });

  it('renders expanded (256px) by default on desktop', () => {
    mockMatchMedia(false);
    render(
      <MemoryRouter>
        <AppSidebar />
      </MemoryRouter>,
    );
    const aside = screen.getByTestId('app-sidebar');
    expect(aside.style.width).toBe('256px');
  });

  it('auto-collapses on mobile even without defaultCollapsed', () => {
    mockMatchMedia(true); // mobile
    render(
      <MemoryRouter>
        <AppSidebar />
      </MemoryRouter>,
    );
    const aside = screen.getByTestId('app-sidebar');
    expect(aside.style.width).toBe('60px');
  });

  it('toggle button flips between 60px and 256px', () => {
    mockMatchMedia(false);
    render(
      <MemoryRouter>
        <AppSidebar defaultCollapsed />
      </MemoryRouter>,
    );
    const aside = screen.getByTestId('app-sidebar');
    expect(aside.style.width).toBe('60px');
    const toggle = screen.getByLabelText('Expand sidebar');
    act(() => {
      toggle.click();
    });
    expect(aside.style.width).toBe('256px');
  });
});
