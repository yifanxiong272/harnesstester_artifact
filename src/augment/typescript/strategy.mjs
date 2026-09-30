export const DEFAULT_STRATEGY = "contract_directed";
export const STRATEGIES = [DEFAULT_STRATEGY, "contract_agnostic"];

export function isContractDirected(strategy = DEFAULT_STRATEGY) {
  if (!STRATEGIES.includes(strategy)) {
    throw new Error(`Unknown augmentation strategy: ${strategy}`);
  }
  return strategy === DEFAULT_STRATEGY;
}
