/**
 * Community color resolver — single source of truth used by GraphPanel,
 * the legend, and CommunitiesDetailPage. If these regression checks
 * break, the same community will paint different colors across views.
 */
import { describe, it, expect } from 'vitest';

import { resolveCommunityColor, FALLBACK_COMMUNITY_PALETTE } from '@/lib/communityColor';
import { COMMUNITIES } from '@/config/constants';

describe('resolveCommunityColor', () => {
  it('returns the canonical color for built-in A–E ids', () => {
    for (const c of COMMUNITIES) {
      expect(resolveCommunityColor(c.id)).toBe(c.color);
    }
  });

  it('falls back to the shared palette for unknown ids', () => {
    const color = resolveCommunityColor('M');
    expect(FALLBACK_COMMUNITY_PALETTE).toContain(color);
  });

  it('is stable: same id always maps to the same color', () => {
    const ids = [
      '7ab2af25-f4e9-4cf5-a67e-82197fbc7090',
      'mainstream',
      'skeptics',
      'influencers',
    ];
    for (const id of ids) {
      const a = resolveCommunityColor(id);
      const b = resolveCommunityColor(id);
      expect(a).toBe(b);
    }
  });

  it('different ids generally pick different fallback slots (no obvious bucket collapse)', () => {
    // Not a perfect-uniqueness claim — hash collisions are allowed — but
    // the resolver should not collapse 10 distinct ids onto 1-2 colors.
    const ids = Array.from({ length: 10 }, (_, i) => `community-${i}`);
    const colors = new Set(ids.map(resolveCommunityColor));
    expect(colors.size).toBeGreaterThanOrEqual(5);
  });
});
