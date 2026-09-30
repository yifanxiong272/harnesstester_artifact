DEFAULT_STRATEGY = "contract_directed"
STRATEGIES = (DEFAULT_STRATEGY, "contract_agnostic")


def is_contract_directed(strategy: str = DEFAULT_STRATEGY) -> bool:
    if strategy not in STRATEGIES:
        raise ValueError(f"unknown augmentation strategy: {strategy!r}")
    return strategy == DEFAULT_STRATEGY
