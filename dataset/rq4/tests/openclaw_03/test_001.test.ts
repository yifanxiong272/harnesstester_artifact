import { it, expect } from 'vitest';
import { evaluateRuntimeEligibility } from '../../shared/config-eval';

it('always=true must override OS filtering and return true even when os list does not match runtime', () => {
  const result = evaluateRuntimeEligibility({
    os: ['definitely-not-a-runtime-platform'],
    remotePlatforms: [],
    always: true,
    requires: {},
    hasBin: () => false,
    hasRemoteBin: () => false,
    hasAnyRemoteBin: () => false,
    hasEnv: () => false,
    isConfigPathTruthy: () => false,
  });

  expect(result).toBe(true);
});
