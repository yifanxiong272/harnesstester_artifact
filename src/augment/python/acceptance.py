DEFAULT_ACCEPTANCE_POLICY = "passing_subset"
ACCEPTANCE_POLICIES = (DEFAULT_ACCEPTANCE_POLICY, "candidate_atomic")


def is_candidate_atomic(policy: str = DEFAULT_ACCEPTANCE_POLICY) -> bool:
    if policy not in ACCEPTANCE_POLICIES:
        raise ValueError(f"unknown acceptance policy: {policy!r}")
    return policy == "candidate_atomic"
