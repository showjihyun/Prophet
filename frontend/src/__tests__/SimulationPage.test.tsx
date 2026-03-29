/**
 * Auto-generated from SPEC: docs/spec/07_FRONTEND_SPEC.md
 * SPEC Version: 0.1.0
 * Tests the main simulation page renders all 4 zones.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// Mock WebSocket hook
vi.mock('../hooks/useSimulationSocket', () => ({
  useSimulationSocket: () => ({ lastMessage: null }),
}));

// Mock Cytoscape (not available in jsdom)
vi.mock('cytoscape', () => ({
  default: vi.fn(() => ({
    on: vi.fn(),
    nodes: () => ({ length: 0, forEach: vi.fn() }),
    edges: () => ({ length: 0, forEach: vi.fn() }),
    zoom: vi.fn(() => 1),
    width: vi.fn(() => 800),
    height: vi.fn(() => 600),
    fit: vi.fn(),
    destroy: vi.fn(),
  })),
}));

import SimulationPage from '../pages/SimulationPage';

describe('SimulationPage', () => {
  /** @spec 07_FRONTEND_SPEC.md#simulation-dashboard */
  it('renders the simulation page with control panel', () => {
    render(
      <MemoryRouter>
        <SimulationPage />
      </MemoryRouter>,
    );
    expect(screen.getByTestId('simulation-page')).toBeInTheDocument();
    expect(screen.getByTestId('control-panel')).toBeInTheDocument();
  });

  it('renders graph panel', () => {
    render(
      <MemoryRouter>
        <SimulationPage />
      </MemoryRouter>,
    );
    expect(screen.getByTestId('graph-panel')).toBeInTheDocument();
  });

  it('renders timeline panel', () => {
    render(
      <MemoryRouter>
        <SimulationPage />
      </MemoryRouter>,
    );
    expect(screen.getByTestId('timeline-panel')).toBeInTheDocument();
  });

  it('renders metrics panel', () => {
    render(
      <MemoryRouter>
        <SimulationPage />
      </MemoryRouter>,
    );
    expect(screen.getByTestId('metrics-panel')).toBeInTheDocument();
  });
});
