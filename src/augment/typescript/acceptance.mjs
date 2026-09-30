export const DEFAULT_ACCEPTANCE_POLICY = "passing_subset";
export const ACCEPTANCE_POLICIES = [
  DEFAULT_ACCEPTANCE_POLICY,
  "candidate_atomic",
];

export function isCandidateAtomic(policy = DEFAULT_ACCEPTANCE_POLICY) {
  if (!ACCEPTANCE_POLICIES.includes(policy)) {
    throw new Error(`Unknown acceptance policy: ${policy}`);
  }
  return policy === "candidate_atomic";
}
