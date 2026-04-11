/**
 * Auto-generated from SPEC: docs/spec/06_API_SPEC.md
 * SPEC Version: 0.1.0
 * Tests API client method signatures and types.
 */
import { describe, it, expect } from 'vitest';
import { apiClient } from '../api/client';

describe('apiClient', () => {
  /** @spec 06_API_SPEC.md#simulation-endpoints */
  it('has all simulation methods', () => {
    expect(apiClient.simulations.create).toBeDefined();
    expect(apiClient.simulations.get).toBeDefined();
    expect(apiClient.simulations.list).toBeDefined();
    expect(apiClient.simulations.start).toBeDefined();
    expect(apiClient.simulations.step).toBeDefined();
    expect(apiClient.simulations.pause).toBeDefined();
    expect(apiClient.simulations.resume).toBeDefined();
    expect(apiClient.simulations.stop).toBeDefined();
    expect(apiClient.simulations.getSteps).toBeDefined();
  });

  /** @spec 06_API_SPEC.md#phase-b-endpoints */
  it('has Phase B methods', () => {
    expect(apiClient.simulations.injectEvent).toBeDefined();
    expect(apiClient.simulations.replay).toBeDefined();
    expect(apiClient.simulations.compare).toBeDefined();
    expect(apiClient.simulations.engineControl).toBeDefined();
    expect(apiClient.simulations.recommendEngine).toBeDefined();
  });

  /** @spec 06_API_SPEC.md#agent-endpoints */
  it('has agent methods', () => {
    expect(apiClient.agents.list).toBeDefined();
    expect(apiClient.agents.get).toBeDefined();
    expect(apiClient.agents.modify).toBeDefined();
    expect(apiClient.agents.getMemory).toBeDefined();
  });

  /** @spec 06_API_SPEC.md#community-endpoints */
  it('has community methods', () => {
    expect(apiClient.communities.list).toBeDefined();
  });

  /** @spec 06_API_SPEC.md#network-endpoints */
  it('has network methods', () => {
    expect(apiClient.network.get).toBeDefined();
    expect(apiClient.network.getMetrics).toBeDefined();
  });

  /** @spec 06_API_SPEC.md#settings-endpoints */
  it('has settings methods', () => {
    expect(apiClient.settings.get).toBeDefined();
    expect(apiClient.settings.update).toBeDefined();
    expect(apiClient.settings.listOllamaModels).toBeDefined();
    expect(apiClient.settings.testOllama).toBeDefined();
    expect(apiClient.settings.listPlatforms).toBeDefined();
    expect(apiClient.settings.listRecsys).toBeDefined();
  });

  /** @spec 06_API_SPEC.md#project-endpoints */
  it('has projects methods', () => {
    expect(apiClient.projects.list).toBeDefined();
    expect(apiClient.projects.get).toBeDefined();
    expect(apiClient.projects.create).toBeDefined();
    expect(apiClient.projects.createScenario).toBeDefined();
    expect(apiClient.projects.runScenario).toBeDefined();
    expect(apiClient.projects.deleteScenario).toBeDefined();
  });
});
