def probe_constraints() -> list[str]:
    """Return prompt-visible constraints shared by all probing strategies."""

    # These constraints are part of the public prompt contract. They document
    # which benchmark fields are intentionally unavailable to generation.
    return [
        "Use only the buggy-side target units, existing test context, and constraints provided in the packet.",
        "Do not use issue text, PR text, commit messages, fixed source, source diffs, "
        "changed hunks, benchmark labels, or official triggering tests.",
        "Write append-only pytest code under the packet's dedicated generated_test_roots.",
        "Use deterministic mocks or direct object construction.",
        "Do not use live model, credential, or network calls.",
        "Do not depend on unbounded wall-clock timing or inspect or mutate operating-system process state.",
        "Bounded deterministic timing and prompt-visible public project observation helpers are allowed when required by the target behavior.",
    ]
